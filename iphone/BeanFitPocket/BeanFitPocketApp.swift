import SwiftUI
import UniformTypeIdentifiers

@MainActor final class PocketModel: ObservableObject {
    @Published var selected = LocalModel.catalog[0]
    @Published var loadedID: String?
    @Published var status = "Import a model to begin. Everything runs on this device."
    @Published var busy = false
    @Published var answer = ""
    @Published var request = "A blue watch under $150"
    @Published var chat = "Reply with one short sentence introducing yourself."
    @Published var budget = ""
    @Published var strap = "any"
    @Published var hasDraft = false
    @Published var offers: [SampleOffer]?
    @Published var metrics: [Measurement] = []
    @Published var exportURL: URL?
    @Published var memoryWarnings = 0
    let runtime = EmbeddedInference()
    var ready: Bool { loadedID == selected.id && !busy }
    func perform(_ title: String, operation: @escaping () async throws -> Void) {
        guard !busy else { return }; busy = true; status = title; exportURL = nil
        Task {
            defer { busy = false }
            do { try await operation(); status = "Ready" }
            catch { if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }; status = error.localizedDescription }
        }
    }
    func importModel(_ url: URL) {
        let model = selected
        perform("Copying and verifying model…") {
            await self.runtime.unload(); self.loadedID = nil
            try await Task.detached { try ModelFiles.importFile(url, model: model) }.value
        }
    }
    func load() {
        let model = selected
        perform("Verifying and loading model…") {
            self.loadedID = nil
            self.metrics.append(try await self.runtime.load(model)); self.loadedID = model.id
        }
    }
    func unload() {
        perform("Releasing model memory…") { await self.runtime.unload(); self.loadedID = nil }
    }
    func generate() {
        perform("Running on this device…") {
            let result = try await self.runtime.generate(system: "You are a concise local assistant. You have no tools or network access. Do not claim to save, send, purchase or execute actions.", user: self.chat, maxTokens: 128)
            self.answer = result.text; self.metrics.append(result.measurement)
        }
    }
    func suggest() {
        hasDraft = false; offers = nil
        perform("Suggesting filters locally…") {
            let (draft, result) = try await ShoppingAdapter(runtime: self.runtime).suggest(self.request)
            self.metrics.append(result.measurement)
            self.budget = draft.maxPrice.map { String(format: "%g", $0) } ?? ""
            self.strap = draft.strap ?? "any"; self.hasDraft = true
        }
    }
    func apply() {
        let amount = budget.isEmpty ? nil : Double(budget)
        guard budget.isEmpty || (amount != nil && amount!.isFinite && amount! >= 0 && amount! <= 100000) else { status = "Enter a valid nonnegative budget"; return }
        offers = SampleOffer.matching(ShoppingDraft(maxPrice: amount, strap: strap == "any" ? nil : strap))
        status = "Reviewed filters applied to the sample catalog"
    }
    func export() {
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]; encoder.dateEncodingStrategy = .iso8601
            let url = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("beanfit-measurements.json")
            let report = Report(schema: "beanfit.iphone.prototype.v1", runtimeRevision: "2145525a4081d66ff1a87cf43ef809f95a85ac0c", qualified: false, memoryWarnings: memoryWarnings, measurements: metrics)
            try encoder.encode(report).write(to: url, options: .atomic); exportURL = url
        } catch { if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }; status = error.localizedDescription }
    }
    struct Report: Codable {
        let schema: String, runtimeRevision: String
        let qualified: Bool
        let memoryWarnings: Int
        let measurements: [Measurement]
    }
    func smoke() async {
        guard ProcessInfo.processInfo.arguments.contains("--smoke") else { return }
        busy = true; defer { busy = false }
        if let argument = ProcessInfo.processInfo.arguments.first(where: { $0.hasPrefix("--model=") }),
           let model = LocalModel.catalog.first(where: { $0.id == String(argument.dropFirst(8)) }) { selected = model }
        var checks: [String: Bool] = [:]
        do {
            let valid = try ShoppingDraft.parse(#"{"maxPrice":150,"strap":"blue"}"#)
            checks["typed_preferences"] = valid.maxPrice == 150 && valid.strap == "blue"
            let invalid = [#"{"maxPrice":-1,"strap":null}"#, #"{"maxPrice":true,"strap":null}"#,
                           #"{"maxPrice":150,"strap":"red"}"#, #"{"maxPrice":150,"strap":null,"buy":true}"#,
                           #"{"strap":"blue"}"#]
            checks["invalid_preferences_rejected"] = invalid.allSatisfy { (try? ShoppingDraft.parse($0)) == nil }
            checks["inclusive_budget"] = SampleOffer.matching(ShoppingDraft(maxPrice: 120, strap: "blue")).map(\.id) == ["W1"]
            checks["no_matches"] = SampleOffer.matching(ShoppingDraft(maxPrice: 119, strap: "blue")).isEmpty
            status = "Device smoke test: loading"
            metrics.append(try await runtime.load(selected)); loadedID = selected.id; checks["load"] = true
            let text = try await runtime.generate(system: "Use only the supplied fact and reply with the requested word.", user: "The badge is amber. Reply with only its color.", maxTokens: 32)
            metrics.append(text.measurement); answer = text.text
            checks["local_inference"] = text.text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased().trimmingCharacters(in: CharacterSet(charactersIn: ".")) == "amber"
            let (draft, result) = try await ShoppingAdapter(runtime: runtime).suggest("I want a blue watch with a maximum price of 150 dollars.")
            metrics.append(result.measurement)
            checks["product_preferences"] = draft.maxPrice == 150 && draft.strap == "blue"
            checks["catalog_rule"] = SampleOffer.matching(draft).map(\.id) == ["W1"]
            checks["review_required"] = offers == nil
            budget = draft.maxPrice.map { String(format: "%g", $0) } ?? ""; strap = draft.strap ?? "any"; hasDraft = true
            await runtime.unload(); loadedID = nil; checks["unload"] = true
            status = checks.values.allSatisfy { $0 } ? "Local checks passed" : "Local checks need review"
        } catch {
            if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }
            status = error.localizedDescription; checks["completed"] = false
            await runtime.unload(); loadedID = nil
        }
        export()
        let record: [String: Any] = ["checks": checks, "status": status, "model": selected.id, "phoneQualified": false]
        let destination = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("smoke.json")
        try? JSONSerialization.data(withJSONObject: record, options: .prettyPrinted).write(to: destination, options: .atomic)
    }
}

@main struct BeanFitPocketApp: App {
    @StateObject private var model = PocketModel()
    @Environment(\.scenePhase) private var scenePhase
    var body: some Scene {
        WindowGroup {
            ContentView(model: model)
                .task { await model.smoke() }
                .onReceive(NotificationCenter.default.publisher(for: UIApplication.didReceiveMemoryWarningNotification)) { _ in
                    model.memoryWarnings += 1; model.runtime.cancel()
                    Task { await model.runtime.unload(); model.loadedID = nil; model.status = "Memory warning: model released" }
                }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .background {
                        model.runtime.cancel()
                        Task { await model.runtime.unload(); model.loadedID = nil }
                    }
                }
        }
    }
}

struct ContentView: View {
    @ObservedObject var model: PocketModel
    @State private var importer = false
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Label("Local intelligence for your products", systemImage: "iphone")
                    Text("Prototype · no remote inference").font(.caption).foregroundStyle(.secondary)
                    Text(model.status).accessibilityIdentifier("runtimeStatus")
                    if model.busy { ProgressView(); Button("Stop") { model.runtime.cancel() } }
                }
                Section("1. Choose a local model") {
                    Picker("Model", selection: $model.selected) {
                        ForEach(LocalModel.catalog) { Text($0.title).tag($0) }
                    }.disabled(model.busy || model.loadedID != nil)
                    Button("Import model from Files") { importer = true }.disabled(model.busy)
                    HStack {
                        Button("Load") { model.load() }.disabled(model.busy || model.loadedID != nil)
                        Spacer()
                        Button("Unload") { model.unload() }.disabled(model.busy || model.loadedID == nil)
                    }.buttonStyle(.borderless)
                    Text("Files are verified before loading. Download sizes are not memory requirements. Start with 0.8B to check your device.").font(.caption).foregroundStyle(.secondary)
                }
                Section("2. Try local inference") {
                    TextField("Ask something", text: $model.chat, axis: .vertical).lineLimit(2...4)
                    Button("Run locally") { model.generate() }.disabled(!model.ready)
                    if !model.answer.isEmpty { Text(model.answer).textSelection(.enabled).accessibilityIdentifier("localAnswer") }
                }
                Section("3. Jumping Beans demo") {
                    Text("Sample watch catalog · no live offers, saving or purchases").font(.caption).foregroundStyle(.secondary)
                    TextField("What are you looking for?", text: $model.request, axis: .vertical)
                    Button("Suggest filters") { model.suggest() }.disabled(!model.ready)
                    if model.hasDraft {
                        Text("Review and edit before applying").font(.headline)
                        TextField("Maximum price in USD (optional)", text: $model.budget).keyboardType(.decimalPad)
                        Picker("Strap", selection: $model.strap) {
                            Text("Any").tag("any"); Text("Blue").tag("blue"); Text("Black").tag("black"); Text("Steel").tag("steel")
                        }
                        Button("Apply reviewed filters") { model.apply() }.disabled(model.busy)
                    }
                    if let offers = model.offers {
                        if offers.isEmpty { Text("No matching sample offers") }
                        ForEach(offers) { offer in Text("\(offer.name) · $\(Int(offer.price)) · \(offer.strap)") }
                    }
                }
                Section("Measurements") {
                    Text("Observed app-process memory only. Samples may miss brief peaks. These measurements do not yet qualify a product or measure the entire voice stack.").font(.caption)
                    ForEach(model.metrics.suffix(6)) { metric in
                        VStack(alignment: .leading) {
                            Text("\(metric.stage) · \(metric.durationMs / 1000, specifier: "%.2f") s")
                            Text("Observed peak: \(Double(metric.observedPeakProcessBytes)/1048576, specifier: "%.1f") MiB").font(.caption)
                            Text(metric.evidenceKind).font(.caption2).foregroundStyle(.secondary)
                        }
                    }
                    Button("Prepare measurement export") { model.export() }.disabled(model.busy || model.metrics.isEmpty)
                    if let url = model.exportURL { ShareLink("Share measurements", item: url) }
                }
            }.navigationTitle("BeanFit Pocket")
            .fileImporter(isPresented: $importer, allowedContentTypes: [.data]) { result in
                switch result { case .success(let url): model.importModel(url); case .failure(let error): model.status = error.localizedDescription }
            }
        }
    }
}
