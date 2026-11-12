#include "uart.h"

#include <stdint.h>

static volatile uint32_t *const uart_data = (volatile uint32_t *)0x05000000;
static volatile uint32_t *const uart_ier = (volatile uint32_t *)0x05000004;
static volatile uint32_t *const uart_fcr = (volatile uint32_t *)0x05000008;
static volatile uint32_t *const uart_lcr = (volatile uint32_t *)0x0500000c;
static volatile const uint32_t *const uart_status = (volatile const uint32_t *)0x05000014;
static volatile uint32_t *const uart_bgr = (volatile uint32_t *)0x0300190c;
static volatile uint32_t *const ph_cfg0 = (volatile uint32_t *)0x0300b0fc;
static volatile uint32_t *const ph_pull0 = (volatile uint32_t *)0x0300b118;

void uart_init(void) {
    uart_drain();
    *uart_lcr = 3;
    *uart_ier = 0;
    *uart_fcr = 7;
}

int uart_getc(void) {
    uint32_t status;
    do {
        status = *uart_status;
    } while (!(status & 1u));
    uint32_t value = *uart_data;
    return (status & 0x1eu) ? -1 : (int)(value & 0xffu);
}

static void uart_putc(char value) {
    while (!(*uart_status & (1u << 5))) {
    }
    *uart_data = (unsigned char)value;
}

void uart_puts(const char *text) {
    while (*text) {
        uart_putc(*text++);
    }
}

void uart_drain(void) {
    while (!(*uart_status & (1u << 6))) {
    }
}

void uart_disable(void) {
    *uart_ier = 0;
    *uart_bgr &= ~((1u << 16) | 1u);
    *ph_pull0 = (*ph_pull0 & ~0xfu) | 0xau;
    *ph_cfg0 = (*ph_cfg0 & ~0xffu) | 0x77u;
    __asm__ volatile("dsb sy" ::: "memory");
}
