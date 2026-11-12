#include "workload.h"

#include <stddef.h>

extern const uint32_t workload_idle[WORKLOAD_WORDS];
extern const uint32_t workload_nop[WORKLOAD_WORDS];
extern const uint32_t workload_mov[WORKLOAD_WORDS];
extern const uint32_t workload_movz[WORKLOAD_WORDS];
extern const uint32_t workload_add[WORKLOAD_WORDS];
extern const uint32_t workload_adds[WORKLOAD_WORDS];
extern const uint32_t workload_sub[WORKLOAD_WORDS];
extern const uint32_t workload_and[WORKLOAD_WORDS];
extern const uint32_t workload_orr[WORKLOAD_WORDS];
extern const uint32_t workload_eor[WORKLOAD_WORDS];
extern const uint32_t workload_lsl[WORKLOAD_WORDS];
extern const uint32_t workload_lsr[WORKLOAD_WORDS];
extern const uint32_t workload_b[WORKLOAD_WORDS];
extern const uint32_t workload_beq[WORKLOAD_WORDS];
extern const uint32_t workload_bne[WORKLOAD_WORDS];

static const struct workload workloads[] = {
    {"IDLE", workload_idle, 0},
    {"NOP", workload_nop, 0},
    {"MOV", workload_mov, 0},
    {"MOVZ", workload_movz, 0},
    {"ADD", workload_add, 0},
    {"ADDS", workload_adds, 0},
    {"SUB", workload_sub, 0},
    {"AND", workload_and, 0},
    {"ORR", workload_orr, 0},
    {"EOR", workload_eor, 0},
    {"LSL", workload_lsl, 0},
    {"LSR", workload_lsr, 0},
    {"B", workload_b, 0},
    {"BEQ-TAKEN", workload_beq, 1ul << 30},
    {"BEQ-NOT-TAKEN", workload_beq, 0},
    {"BNE-TAKEN", workload_bne, 0},
    {"BNE-NOT-TAKEN", workload_bne, 1ul << 30},
};

_Alignas(64) static uint32_t measurement_loop[WORKLOAD_WORDS];

const struct workload *workload_find(const char *name) {
    for (size_t i = 0; i < sizeof(workloads) / sizeof(workloads[0]); ++i) {
        const char *left = name;
        const char *right = workloads[i].name;
        while (*left && *left == *right) {
            ++left;
            ++right;
        }
        if (*left == *right) {
            return &workloads[i];
        }
    }
    return NULL;
}

void workload_prepare(const struct workload *workload) {
    for (size_t word = 0; word < WORKLOAD_WORDS; ++word) {
        measurement_loop[word] = workload->code[word];
    }
}

_Noreturn void workload_start(const struct workload *workload) {
    workload_run(measurement_loop, workload->nzcv);
}
