#ifndef BEANFIT_NATIVE_H
#define BEANFIT_NATIVE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void * bf_create(void);
void bf_destroy(void * engine);
void bf_prepare(void * engine);
void bf_cancel(void * engine);
void bf_set_threads(void * engine, int threads);
void bf_set_text_sampling(void * engine, int profile);
int bf_load(void * engine, const char * path);
void bf_unload(void * engine);
const char * bf_generate(void * engine, const char * prompt, const char * grammar, int max_tokens);
const char * bf_error(void * engine);
int bf_tokens(void * engine);
double bf_first_token_ms(void * engine);
uint64_t bf_footprint(void);
uint64_t bf_peak_resident(void);
typedef struct {
    uint64_t footprint, resident, virtual_bytes, internal_bytes, external_bytes, compressed, available;
} bf_resource_snapshot;
bf_resource_snapshot bf_resources(void);
#ifdef __cplusplus
}
#endif
#endif
