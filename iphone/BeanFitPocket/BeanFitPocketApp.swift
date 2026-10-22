import SwiftUI
import UniformTypeIdentifiers

@MainActor final class PocketModel: ObservableObject {
    @Published var selected = LocalModel.catalog.first { $0.id == "liquid12" }!
    @Published var selectedExperience = "text_assistant"
    @Published var smallestDownload = false
    @Published var testMemoryMiB = ""
    var hardwareIdentifier: String {
        #if targetEnvironment(simulator)
        return ProcessInfo.processInfo.environment["SIMULATOR_MODEL_IDENTIFIER"] ?? "simulator"
        #else
        var value = utsname(); uname(&value)
        let size = MemoryLayout.size(ofValue: value.machine)
        return withUnsafePointer(to: &value.machine) { pointer in
            pointer.withMemoryRebound(to: CChar.self, capacity: size) { String(cString: $0) }
        }
        #endif
    }
    var modelSuggestions: [ModelSuggestion] {
        let text = testMemoryMiB.trimmingCharacters(in: .whitespacesAndNewlines)
        let amount = Int64(text)
        let budget: Int64? = text.isEmpty ? nil : (amount != nil && amount! > 0 && amount! <= 1_073_741_824 ? amount! * 1_048_576 : 0)
        return ModelSuggestions.suggestions(experience: selectedExperience, device: hardwareIdentifier,
            osMajor: ProcessInfo.processInfo.operatingSystemVersion.majorVersion,
            memoryBudgetBytes: budget, smallestDownload: smallestDownload)
    }
    var selectedSuggestion: ModelSuggestion? { modelSuggestions.first { $0.id == selected.id } }
    var modelOptions: [LocalModel] {
        modelSuggestions.compactMap { suggestion in LocalModel.catalog.first { $0.id == suggestion.id } }
    }
    @Published var loadedID: String?
    @Published var status = "Filter suggestions run on this device. Catalog searches use the internet."
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
    @Published var catalogQuery = "coffee"
    @Published var catalogRequest = "coffee under $30"
    @Published var catalogBudget = ""
    @Published var catalogInclusive = false
    @Published var catalogReviewed = false
    @Published var catalogResult: CatalogResponse?
    @Published var catalogHandoff: MerchantOffer?
    @Published var catalogStatus = "Review filters, then search the public merchant catalog."
    let runtime = EmbeddedInference()
    private var activeTask: Task<Void, Never>?
    private var generation = 0
    func retireCatalog() { catalogResult = nil; catalogHandoff = nil; catalogReviewed = false }
    func cancelWork() {
        generation += 1; let token = generation
        activeTask?.cancel(); runtime.cancel(); busy = true
        retireCatalog(); hasDraft = false; offers = nil; answer = ""
        Task {
            await runtime.unload()
            guard generation == token else { return }
            loadedID = nil; busy = false; status = "Stopped; model released"
        }
    }
    func catalogSuggest(useModel: Bool) {
        retireCatalog()
        let input = catalogRequest
        perform(useModel ? "Suggesting catalog filters on this device…" : "Parsing filters without a model…") {
            let draft: CatalogDraft
            if useModel {
                let (suggestion, result) = try await CatalogShoppingAdapter(runtime: self.runtime).suggest(input)
                draft = suggestion; self.metrics.append(result.measurement)
            } else { draft = try CatalogDraft.baseline(input) }
            try Task.checkCancellation()
            guard self.catalogRequest == input else { return }
            self.catalogQuery = draft.query
            self.catalogBudget = draft.maxPrice.map { String(format: "%.2f", $0) } ?? ""
            self.catalogInclusive = draft.inclusive
            self.catalogStatus = "Review and edit these filters before searching."
        }
    }
    func searchCatalog(reviewing offer: MerchantOffer? = nil) {
        catalogResult = nil; catalogHandoff = nil
        guard catalogReviewed else { status = "Review the current filters first"; return }
        let budget = catalogBudget.trimmingCharacters(in: .whitespacesAndNewlines)
        guard budget.isEmpty || Double(budget) != nil else { status = "Enter a valid USD budget"; return }
        let draft = CatalogDraft(query: catalogQuery, maxPrice: budget.isEmpty ? nil : Double(budget), inclusive: catalogInclusive, supported: true)
        perform("Searching the public catalog…") {
            let result = try await PublicCatalogClient().search(draft, reviewing: offer)
            try Task.checkCancellation()
            guard self.catalogReviewed, self.catalogQuery == draft.query, self.catalogBudget == budget,
                  self.catalogInclusive == draft.inclusive else { return }
            self.catalogResult = result
            if offer != nil, result.status == "ok" { self.catalogHandoff = result.offers.first }
            self.catalogStatus = result.status == "ok" ? "Current merchant discovery. Review the exact variant before opening its link." : "Catalog status: \(result.status). No automatic retry."
        }
    }
    var ready: Bool { loadedID == selected.id && !busy && selectedSuggestion?.eligibleForTrial == true }
    var experimentalCatalogSuggestions: Bool { ProcessInfo.processInfo.arguments.contains("--experimental-catalog") }
    func perform(_ title: String, operation: @escaping () async throws -> Void) {
        guard !busy else { return }; busy = true; status = title; exportURL = nil
        generation += 1; let token = generation
        activeTask = Task {
            defer { if generation == token { busy = false; activeTask = nil } }
            do { try Task.checkCancellation(); try await operation(); try Task.checkCancellation(); if generation == token { status = "Ready" } }
            catch { if generation == token { if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }; if let rejected = error as? CatalogSuggestionError { metrics.append(rejected.result.measurement) }; status = error.localizedDescription } }
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
        guard selectedSuggestion?.eligibleForTrial == true else {
            status = selectedSuggestion?.explanation ?? "Choose a supported candidate"; return
        }
        let thermal = ProcessInfo.processInfo.thermalState
        guard thermal != .serious && thermal != .critical else {
            status = "Let the phone cool before loading a model"; return
        }
        let model = selected
        perform("Verifying and loading model…") {
            self.loadedID = nil
            let metric = try await self.runtime.load(model); try Task.checkCancellation(); self.metrics.append(metric); self.loadedID = model.id
        }
    }
    func unload() {
        perform("Releasing model memory…") { await self.runtime.unload(); self.loadedID = nil }
    }
    func generate() {
        perform("Running on this device…") {
            let result = try await self.runtime.generate(system: "You are a concise local assistant. You have no tools or network access. Do not claim to save, send, purchase or execute actions.", user: self.chat, maxTokens: 128)
            try Task.checkCancellation(); self.answer = result.text; self.metrics.append(result.measurement)
        }
    }
    func suggest() {
        hasDraft = false; offers = nil
        perform("Suggesting filters locally…") {
            let (draft, result) = try await ShoppingAdapter(runtime: self.runtime).suggest(self.request)
            try Task.checkCancellation(); self.metrics.append(result.measurement)
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
        } catch { if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }; if let rejected = error as? CatalogSuggestionError { metrics.append(rejected.result.measurement) }; status = error.localizedDescription }
    }
    struct Report: Codable {
        let schema: String, runtimeRevision: String
        let qualified: Bool
        let memoryWarnings: Int
        let measurements: [Measurement]
    }
    func qualifyCatalog() async {
        generation += 1; let token = generation
        busy = true; defer { if generation == token { busy = false; activeTask = nil } }
        var records: [[String: Any]] = []
        var live: [String: Any] = ["run": false]
        var cancellation: [String: Any] = ["run": false]
        UIDevice.current.isBatteryMonitoringEnabled = true
        let batteryStart = UIDevice.current.batteryLevel
        let arguments = ProcessInfo.processInfo.arguments
        if let argument = arguments.first(where: { $0.hasPrefix("--model=") }),
           let model = LocalModel.catalog.first(where: { $0.id == String(argument.dropFirst(8)) }) { selected = model }
        let qualificationModel = selected
        var completed = false
        func checkpoint() {
            #if targetEnvironment(simulator)
            let kind = "simulator"
            #else
            let kind = "physical-device"
            #endif
            let report: [String: Any] = ["schema":"beanfit.pocket.catalog.preliminary.v1", "model":qualificationModel.id, "modelSHA256":qualificationModel.sha256,
                "evidenceKind":kind, "phoneQualified":false, "completed":completed, "interrupted":generation != token || Task.isCancelled, "completedProbeCount":records.count, "records":records, "cancellation":cancellation, "liveCatalog":live,
                "batteryStart":batteryStart, "batteryEnd":UIDevice.current.batteryLevel,
                "missingGates":["20 repeated complete real product flows", "background/foreground observed UI", "complete resident/dirty/mapped whole-stack memory", "30-minute thermal/battery matched baseline", "durable distribution", "Steve release acceptance"]]
            let destination = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("catalog-qualification.json")
            do { try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted,.sortedKeys]).write(to: destination, options: .atomic); print("BeanFit qualification checkpoint: \(records.count) probes, completed=\(completed)") }
            catch { print("BeanFit qualification checkpoint failed: \(error.localizedDescription)") }
        }
        checkpoint()
        defer { checkpoint() }
        do {
            let loaded = try await runtime.load(selected)
            guard generation == token else { return }
            try Task.checkCancellation()
            metrics.append(loaded); loadedID = selected.id
            for probe in CatalogQualificationCase.cases {
                guard generation == token else { return }
                try Task.checkCancellation()
                let baseline = try? CatalogDraft.baseline(probe.request)
                var record: [String: Any] = ["request": probe.request, "baselinePassed": baseline == probe.expected, "expectedAbstention": probe.expected == nil]
                if let expected = probe.expected { record["expected"] = try JSONSerialization.jsonObject(with: JSONEncoder().encode(expected)) }
                do {
                    let output = try await runtime.generate(system: CatalogShoppingAdapter.systemPrompt, user: probe.request, grammar: CatalogShoppingAdapter.grammar, maxTokens: 128)
                    guard generation == token else { return }
                    metrics.append(output.measurement); record["rawOutput"] = output.text
                    let draft = try? CatalogDraft.parse(output.text)
                    let data = Data(output.text.utf8)
                    let decoded = try? JSONDecoder().decode(CatalogDraft.self, from: data)
                    record["modelPassed"] = probe.expected.map { draft == $0 } ?? (decoded?.supported == false)
                    record["durationMs"] = output.measurement.durationMs
                } catch {
                    guard generation == token else { return }
                    if error is CancellationError { throw error }
                    if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }
                    record["modelPassed"] = false; record["error"] = error.localizedDescription
                }
                records.append(record)
                checkpoint()
            }
            do {
            let task = Task { try await runtime.generate(system: "Reply concisely.", user: "Write a long description of coffee.", maxTokens: 256) }
            defer { task.cancel() }
            try await Task.sleep(nanoseconds: 50_000_000)
            let stopped = Date(); task.cancel()
            var didCancel = false
            do { _ = try await task.value } catch { didCancel = true; if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) } }
            let stopMs = Date().timeIntervalSince(stopped) * 1000
            cancellation = ["run":true, "cancelled":didCancel, "durationMs":stopMs, "passed":didCancel && stopMs <= 2000]
            }
            checkpoint()
            // Exactly one search and one review, only on explicitly requested live proof.
            // Retain status/count evidence only. Never export or cache live offers/images/URLs.
            if arguments.contains("--live-catalog") {
                guard generation == token else { return }
                try Task.checkCancellation()
                let draft = CatalogDraft(query:"whole bean coffee", maxPrice:25, inclusive:true, supported:true)
                let found = try await PublicCatalogClient().search(draft)
                guard generation == token else { return }
                try Task.checkCancellation()
                live = ["run":true, "searchStatus":found.status, "offerCount":found.offers.count, "nativeTransport":true, "provenance":found.provenance]
                if found.status == "ok", let offer = found.offers.first {
                    guard generation == token else { return }
                    let reviewed = try await PublicCatalogClient().search(draft, reviewing:offer)
                    live["reviewStatus"] = reviewed.status
                    live["exactVariantHandoff"] = reviewed.status == "ok" && reviewed.offers.count == 1 && reviewed.offers[0].resolved
                }
            }
        } catch {
            live["error"] = error.localizedDescription
            if let failure = error as? MeasuredFailure { metrics.append(failure.measurement) }
        }
        await runtime.unload(); loadedID = nil
        guard generation == token else { return }
        export()
        completed = records.count == CatalogQualificationCase.cases.count
        checkpoint()
        status = "Preliminary qualification recorded; see failures and missing gates"
    }
    func smoke() async {
        if ProcessInfo.processInfo.arguments.contains("--qualify-catalog") {
            let task = Task { await self.qualifyCatalog() }
            activeTask = task
            await task.value
            return
        }
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
            Group {
                if (ProcessInfo.processInfo.arguments.contains("--text-smoke") || ProcessInfo.processInfo.arguments.contains("--text-qualify")) { LocalTextDraftView() }
                else { ContentView(model: model).task { await model.smoke() } }
            }
                .onReceive(NotificationCenter.default.publisher(for: UIApplication.didReceiveMemoryWarningNotification)) { _ in
                    model.memoryWarnings += 1; model.cancelWork()
                }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .background {
                        model.cancelWork()
                    }
                }
        }
    }
}

struct ContentView: View {
    @ObservedObject var model: PocketModel
    @State private var importer = false
    @State private var textAssistant = false
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Label("Local intelligence for your products", systemImage: "iphone")
                    Text("Prototype · no remote inference").font(.caption).foregroundStyle(.secondary)
                    Text(model.status).accessibilityIdentifier("runtimeStatus")
                    if model.busy { ProgressView(); Button("Stop") { model.cancelWork() } }
                }
                Section("Write on this iPhone") {
                    Button("Write with local AI") {
                        model.perform("Releasing current model…") {
                            await model.runtime.unload(); model.loadedID = nil
                            try Task.checkCancellation(); textAssistant = true
                        }
                    }.disabled(model.busy)
                    Text("Short summaries, rewrites and reply drafts. Review before using.").font(.caption)
                }
                Section("Shop the merchant catalog") {
                    Text("Suggestions stay on this iPhone. Searching sends only your reviewed keywords and USD budget to Jumping Beans.").font(.caption).foregroundStyle(.secondary)
                    TextField("Shopping request", text: $model.catalogRequest, axis: .vertical)
                        .disabled(model.busy).onChange(of: model.catalogRequest) { _, _ in model.retireCatalog() }
                    Text("Local model suggestions have not passed qualification. Use the parser or edit filters directly.").font(.caption)
                    Button("Experimental local suggestions") { model.catalogSuggest(useModel: true) }.disabled(!model.ready || !model.experimentalCatalogSuggestions)
                    Button("Parse without a model") { model.catalogSuggest(useModel: false) }.disabled(model.busy)
                    TextField("Product keywords", text: $model.catalogQuery).disabled(model.busy)
                        .onChange(of: model.catalogQuery) { _, _ in model.retireCatalog() }
                    TextField("Maximum price in USD (optional)", text: $model.catalogBudget).keyboardType(.decimalPad).disabled(model.busy)
                        .onChange(of: model.catalogBudget) { _, _ in model.retireCatalog() }
                    Toggle("Include the maximum price", isOn: $model.catalogInclusive).disabled(model.busy)
                        .onChange(of: model.catalogInclusive) { _, _ in model.retireCatalog() }
                    Toggle("I reviewed these filters", isOn: $model.catalogReviewed).disabled(model.busy)
                        .onChange(of: model.catalogReviewed) { _, reviewed in if !reviewed { model.catalogResult = nil; model.catalogHandoff = nil } }
                    Button("Search reviewed filters") { model.searchCatalog() }.disabled(model.busy || !model.catalogReviewed)
                    Text(model.catalogStatus).font(.caption)
                    if let result = model.catalogResult {
                        ForEach(result.limits, id: \.self) { Text($0).font(.caption2) }
                        ForEach(result.offers) { offer in
                            VStack(alignment: .leading) {
                                Text(offer.title)
                                Text(offer.variantTitle).font(.caption)
                                Text("\(offer.sellerName) · \(Double(offer.price.amount) / 100, specifier: "%.2f") USD").font(.caption)
                                Text("\(offer.verification) · \(offer.billing)").font(.caption2)
                                Text("Shipping, tax, merchant trust and stock at checkout need merchant confirmation.").font(.caption2)
                                if model.catalogHandoff?.id == offer.id, let url = model.catalogHandoff?.url {
                                    Link("Open reviewed merchant variant", destination: url)
                                } else {
                                    Button("Review this exact variant") { model.searchCatalog(reviewing: offer) }.disabled(model.busy)
                                }
                            }
                        }
                    }
                }
                Section("Local model") {
                    Picker("Experience", selection: $model.selectedExperience) {
                        ForEach(ModelSuggestions.catalog.experiences.filter {
                            ["text_assistant", "structured_extraction", "shopping_filters"].contains($0.id)
                        }) { Text($0.name).tag($0.id) }
                    }.disabled(model.busy || model.loadedID != nil)
                    Toggle("Smallest download first", isOn: $model.smallestDownload).disabled(model.busy || model.loadedID != nil)
                    Picker("Model", selection: $model.selected) {
                        ForEach(model.modelOptions) { Text($0.title).tag($0) }
                    }.disabled(model.busy || model.loadedID != nil)
                    if let suggestion = model.selectedSuggestion {
                        Text(suggestion.explanation).font(.caption)
                        Text(suggestion.model.summary).font(.caption).foregroundStyle(.secondary)
                        if let artifact = suggestion.model.artifacts.first {
                            Link("View the exact model file", destination: URL(string: "https://huggingface.co/\(artifact.repository)/blob/\(artifact.revision)/\(artifact.filename)")!)
                        }
                    }
                    DisclosureGroup("Test memory allowance") {
                        TextField("Optional allowance in MiB", text: $model.testMemoryMiB).keyboardType(.numberPad).disabled(model.busy || model.loadedID != nil)
                        Text("Use an app allowance, not total phone RAM. Files reaching it are conservatively excluded. File size is not resident memory; complete working memory remains unverified.").font(.caption)
                    }
                    Button("Import model from Files") { importer = true }.disabled(model.busy)
                    HStack {
                        Button("Load") { model.load() }.disabled(model.busy || model.loadedID != nil || model.selectedSuggestion?.eligibleForTrial != true)
                        Spacer()
                        Button("Unload") { model.unload() }.disabled(model.busy || model.loadedID == nil)
                    }.buttonStyle(.borderless)
                    Text("Catalog checked \(ModelSuggestions.catalog.as_of). Task-specific ordering suggests what to test; no model is qualified yet. Files are verified before loading. Download sizes are not memory requirements.").font(.caption).foregroundStyle(.secondary)
                }
                Section("Runtime check") {
                    TextField("Ask something", text: $model.chat, axis: .vertical).lineLimit(2...4)
                    Button("Run locally") { model.generate() }.disabled(!model.ready)
                    if !model.answer.isEmpty { Text(model.answer).textSelection(.enabled).accessibilityIdentifier("localAnswer") }
                }
                Section("Historical sample demo") {
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
            .sheet(isPresented: $textAssistant) { LocalTextDraftView() }
            .fileImporter(isPresented: $importer, allowedContentTypes: [.data]) { result in
                switch result { case .success(let url): model.importModel(url); case .failure(let error): model.status = error.localizedDescription }
            }
        }
    }
}
