#ifndef H616_WORKLOAD_H
#define H616_WORKLOAD_H

#define WORKLOAD_INSTRUCTIONS 256
#define WORKLOAD_WORDS (WORKLOAD_INSTRUCTIONS + 1)

#ifndef __ASSEMBLER__
#include <stdint.h>

struct workload {
    const char *name;
    const uint32_t *code;
    uint64_t nzcv;
};

const struct workload *workload_find(const char *name);
void workload_prepare(const struct workload *workload);
_Noreturn void workload_start(const struct workload *workload);
_Noreturn void workload_run(const uint32_t *code, uint64_t nzcv);
#endif

#endif
