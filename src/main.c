#include "runtime.h"

#include "platform.h"
#include "provision.h"
#include "uart.h"
#include "workload.h"

_Noreturn void runtime_main(void) {
    bool ready = platform_init();
    uart_init();
    if (!ready) {
        uart_puts("ERR PLATFORM\r\n");
        uart_drain();
        platform_halt();
    }

    uart_puts("READY\r\n");
    const struct workload *workload = provision_wait();
    workload_prepare(workload);
    uart_puts("ACK ");
    uart_puts(workload->name);
    uart_puts("\r\n");
    uart_drain();
    platform_disconnect_grace();
    uart_disable();
    platform_quiet();
    workload_start(workload);
}
