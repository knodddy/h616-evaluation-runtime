#include "platform.h"

#include <stddef.h>
#include <stdint.h>

static volatile uint32_t *const ccu = (volatile uint32_t *)0x03001000;
static volatile uint32_t *const timer = (volatile uint32_t *)0x03009000;

static uint64_t counter(void) {
    uint64_t value;
    __asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(value));
    return value;
}

bool platform_init(void) {
    uint64_t frequency;
    __asm__ volatile("msr daifset, #0xf\n"
                     "msr cnthp_ctl_el2, xzr\n"
                     "msr cntp_ctl_el0, xzr\n"
                     "msr cntv_ctl_el0, xzr\n"
                     "mrs %0, cntfrq_el0"
                     : "=r"(frequency)
                     :
                     : "memory");
    uint32_t pll = ccu[0x000 / 4];
    uint32_t cpu = ccu[0x500 / 4];
    if (frequency != 24000000 || (pll & 0xb8000000u) != 0xb8000000u ||
        (pll & 0x0003ff03u) != (24u << 8) || (cpu & 0x07000303u) != 0x03000301u ||
        (timer[0xb8 / 4] & 1u)) {
        return false;
    }
    uint64_t start = counter();
    for (unsigned int i = 0; i < 100000; ++i) {
        if (counter() != start) {
            return true;
        }
    }
    return false;
}

void platform_disconnect_grace(void) {
    uint64_t start = counter();
    while (counter() - start < UINT64_C(240000000)) {
    }
}

void platform_quiet(void) {
    static const uint16_t clock_offsets[] = {0x810, 0x814, 0x830, 0x834, 0x838, 0x940, 0x944};
    for (size_t i = 0; i < sizeof(clock_offsets) / sizeof(clock_offsets[0]); ++i) {
        ccu[clock_offsets[i] / 4] &= ~(1u << 31);
    }
    static const uint16_t reset_offsets[] = {0x70c, 0x73c, 0x82c, 0x84c, 0x90c,
                                             0x91c, 0x96c, 0x97c, 0xa8c};
    for (size_t i = 0; i < sizeof(reset_offsets) / sizeof(reset_offsets[0]); ++i) {
        ccu[reset_offsets[i] / 4] = 0;
    }
    for (unsigned int offset = 0xa70; offset <= 0xa7c; offset += 4) {
        ccu[offset / 4] &= ~(7u << 29);
    }
    volatile uint32_t *const r_i2c_bgr = (volatile uint32_t *)0x0701019c;
    *r_i2c_bgr &= ~((1u << 16) | 1u);
    timer[0x00 / 4] = 0;
    timer[0x10 / 4] = 0;
    timer[0x20 / 4] = 0;
    timer[0xc0 / 4] = 0;
    __asm__ volatile("dsb sy; isb" ::: "memory");
}

_Noreturn void platform_halt(void) {
    for (;;) {
        __asm__ volatile("wfe");
    }
}
