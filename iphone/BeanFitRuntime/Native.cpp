#include <algorithm>
#include "Native.h"
#include "llama.h"
#include <atomic>
#include <chrono>
#include <string>
#include <vector>
#include <mach/mach.h>
struct Engine {
    llama_model *model = nullptr;
    std::atomic<bool> cancel{false};
    std::string result, error;
    int tokens = 0;
    double first = -1;
};
static bool aborted(void *p) { return static_cast<Engine *>(p)->cancel.load(); }
static bool progress(float, void *p) { return !aborted(p); }
extern "C" {
void *bf_create() { return new Engine(); }
void bf_unload(void *p) {
    auto e = static_cast<Engine *>(p);
    if (e->model) { llama_model_free(e->model); e->model = nullptr; }
}
void bf_destroy(void *p) { bf_unload(p); delete static_cast<Engine *>(p); }
void bf_cancel(void *p) { static_cast<Engine *>(p)->cancel = true; }
int bf_load(void *p, const char *path) {
    auto e = static_cast<Engine *>(p); bf_unload(p); e->cancel = false; e->error.clear();
    auto params = llama_model_default_params(); params.n_gpu_layers = 0;
    params.progress_callback = progress; params.progress_callback_user_data = p;
    e->model = llama_model_load_from_file(path, params);
    if (!e->model) { e->error = e->cancel ? "Loading cancelled" : "Could not load this model"; return 0; }
    return 1;
}
const char *bf_error(void *p) { return static_cast<Engine *>(p)->error.c_str(); }
int bf_tokens(void *p) { return static_cast<Engine *>(p)->tokens; }
double bf_first_token_ms(void *p) { return static_cast<Engine *>(p)->first; }
uint64_t bf_footprint() {
    task_vm_info_data_t info{}; mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &count) != KERN_SUCCESS) return 0;
    return info.phys_footprint;
}
const char *bf_generate(void *p, const char *prompt, const char *grammar, int max_tokens) {
    auto e = static_cast<Engine *>(p); e->cancel = false; e->error.clear(); e->result.clear(); e->tokens = 0; e->first = -1;
    if (!e->model) { e->error = "Load a model first"; return nullptr; }
    auto vocab = llama_model_get_vocab(e->model);
    std::string input(prompt);
    int count = -llama_tokenize(vocab, input.data(), (int)input.size(), nullptr, 0, true, true);
    if (count <= 0 || count + max_tokens > 2048 || max_tokens < 1 || max_tokens > 256) {
        e->error = "Prompt exceeds the 2048-token context limit"; return nullptr;
    }
    std::vector<llama_token> tokens(count);
    llama_tokenize(vocab, input.data(), (int)input.size(), tokens.data(), count, true, true);
    auto cp = llama_context_default_params(); cp.n_ctx = 2048; cp.n_batch = 256;
    cp.n_threads = 4; cp.n_threads_batch = 4; cp.abort_callback = aborted; cp.abort_callback_data = p;
    auto ctx = llama_init_from_model(e->model, cp);
    if (!ctx) { e->error = "Could not allocate model context"; return nullptr; }
    auto sampler = llama_sampler_chain_init(llama_sampler_chain_default_params());
    if (grammar && *grammar) {
        auto gs = llama_sampler_init_grammar(vocab, grammar, "root");
        if (!gs) { e->error = "Invalid output grammar"; llama_sampler_free(sampler); llama_free(ctx); return nullptr; }
        llama_sampler_chain_add(sampler, gs);
    }
    llama_sampler_chain_add(sampler, llama_sampler_init_greedy());
    auto start = std::chrono::steady_clock::now();
    bool ok = true, finished = false;
    for (int i = 0; i < count && ok; i += 256) {
        int n = std::min(256, count-i);
        if (aborted(p) || llama_decode(ctx, llama_batch_get_one(tokens.data()+i, n)) != 0) ok = false;
    }
    for (int i = 0; i < max_tokens && ok; ++i) {
        if (aborted(p)) { ok = false; break; }
        auto token = llama_sampler_sample(sampler, ctx, -1);
        if (llama_vocab_is_eog(vocab, token)) { finished = true; break; }
        std::vector<char> piece(256);
        int n = llama_token_to_piece(vocab, token, piece.data(), (int)piece.size(), 0, false);
        if (n < 0) { piece.resize(-n); n = llama_token_to_piece(vocab, token, piece.data(), (int)piece.size(), 0, false); }
        if (n < 0) { ok = false; break; }
        e->result.append(piece.data(), n); ++e->tokens;
        if (e->first < 0) e->first = std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        if (llama_decode(ctx, llama_batch_get_one(&token, 1)) != 0) ok = false;
    }
    llama_sampler_free(sampler); llama_free(ctx);
    if (!ok) { e->error = aborted(p) ? "Generation cancelled" : "Generation failed"; return nullptr; }
    if (!finished) { e->error = "Output reached the token limit; shorten the request"; return nullptr; }
    return e->result.c_str();
}
}
