#include "runtime.h"

#include <stdint.h>

_Noreturn void runtime_main(void) {
    volatile uint32_t *const uart_tx = (volatile uint32_t *)0x05000000;
    volatile const uint32_t *const uart_status = (volatile const uint32_t *)0x05000014;
    const char *message = "runtime started\r\n";

    // Inherit UART0's clock, pinmux, and 115200-baud configuration from firmware.
    while (*message) {
        while (!(*uart_status & (1u << 5))) {
        }
        *uart_tx = (uint32_t)*message++;
    }
    // Drain the transmitter before entering the workload.
    while (!(*uart_status & (1u << 6))) {
    }
    workload_idle();
}
