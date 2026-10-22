import Foundation

private struct Packet: Decodable { let cases: [Case] }
private struct Case: Decodable {
    let id: String, task: TextDraftTask, text: String, expectation: String
    let required: [String], forbidden: [String]
    func screens(_ text: String) -> Bool {
        required.allSatisfy { text.range(of:$0,options:[.regularExpression,.caseInsensitive]) != nil }
        && forbidden.allSatisfy { text.range(of:$0,options:[.regularExpression,.caseInsensitive]) == nil }
    }
}
private final class NativePreflightRuntime: LocalInferenceClient {
    let handle = bf_create()!
    let model: LocalModel
    init(_ model: LocalModel, sampling: Int32) { self.model = model; bf_set_text_sampling(handle,sampling) }
    deinit { bf_destroy(handle) }
    func load(_ model: LocalModel) async throws -> Measurement { fatalError("Use explicit verified path") }
    func unload() async { bf_unload(handle) }
    func cancel() { bf_cancel(handle) }
    func generate(system: String, user: String, grammar: String?, maxTokens: Int) async throws -> InferenceResult {
        bf_prepare(handle)
        let started = Date(), deadline = DispatchWorkItem { self.cancel() }
        DispatchQueue.global().asyncAfter(deadline:.now()+90,execute:deadline)
        defer { deadline.cancel() }
        guard let output = bf_generate(handle,model.prompt(system:system,user:user),grammar ?? "",Int32(maxTokens)) else {
            throw RuntimeFailure.message(String(cString:bf_error(handle)))
        }
        let metric = Measurement(id:UUID(),stage:"generate",model:model.id,modelSHA256:model.sha256,
            evidenceKind:"mac-native-preflight-not-phone",device:"Mac preflight",os:ProcessInfo.processInfo.operatingSystemVersionString,
            contextTokens:2048,startedAt:started,durationMs:Date().timeIntervalSince(started)*1000,
            firstTokenMs:bf_first_token_ms(handle),outputTokens:Int(bf_tokens(handle)),baselineProcessBytes:0,
            observedPeakProcessBytes:0,endProcessBytes:0,memorySamples:0,outcome:"completed",thermalBefore:0,thermalAfter:0)
        return InferenceResult(text:String(cString:output),measurement:metric)
    }
}
@main struct NativeTextPreflight {
    static func main() async throws {
        let args = CommandLine.arguments
        guard (5...6).contains(args.count), let model = LocalModel.catalog.first(where:{$0.id == args[1]}) else { fatalError("MODEL_ID MODEL_PATH PACKET OUTPUT [SAMPLING_PROFILE]") }
        let url = URL(fileURLWithPath:args[2]); try ModelFiles.verify(url,model:model)
        let packet = try JSONDecoder().decode(Packet.self,from:Data(contentsOf:URL(fileURLWithPath:args[3])))
        let sampling = args.count == 6 ? Int32(args[5])! : 0
        let runtime = NativePreflightRuntime(model,sampling:sampling)
        guard bf_load(runtime.handle,url.path) == 1 else { throw RuntimeFailure.message(String(cString:bf_error(runtime.handle))) }
        var records: [[String:Any]] = []
        func save(_ completed: Bool) throws {
            let doc: [String:Any] = ["evidence_kind":"mac-native-preflight-not-phone","qualified":false,
                "model":model.id,"model_sha256":model.sha256,"completed":completed,"records":records,
                "memory_and_thermal_measurements":false,"sampling_profile":sampling]
            try JSONSerialization.data(withJSONObject:doc,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:args[4]),options:.atomic)
        }
        try save(false)
        for item in packet.cases {
            do {
                let marker = item.task == .reply ? item.text.range(of:"Reply facts:") : nil
                let text = marker.map { String(item.text[..<$0.lowerBound]) } ?? item.text
                let facts = marker.map { String(item.text[$0.upperBound...]) }
                let result = try await TextDraftAdapter(runtime:runtime).draft(TextDraftRequest(task:item.task,text:text,replyFacts:facts))
                records.append(["id":item.id,"input":item.text,"expectation":item.expectation,"output":result.text,
                    "passed":item.screens(result.text),"duration_ms":result.durationMs,"used_model":result.usedModel])
            } catch { records.append(["id":item.id,"input":item.text,"expectation":item.expectation,"error":error.localizedDescription,"passed":false]) }
            try save(false)
        }
        await runtime.unload(); try save(true)
        print("Mac preflight \(model.id): \(records.filter{$0["passed"] as? Bool == true}.count)/\(records.count) phrase screens. Not phone proof.")
    }
}
