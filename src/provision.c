#include "provision.h"

#include "uart.h"
#include "workload.h"

#include <stdbool.h>
#include <stddef.h>

static bool read_command(char *command, size_t capacity) {
    size_t length = 0;
    bool invalid = false;
    for (;;) {
        int value = uart_getc();
        if (value == 0x18) {
            length = 0;
            invalid = false;
            uart_puts("SYNC\r\n");
            continue;
        }
        if (value == '\r' || value == '\n') {
            command[length] = '\0';
            return !invalid;
        }
        if (value < ' ' || value > '~' || length + 1 >= capacity) {
            invalid = true;
        } else {
            command[length++] = (char)value;
        }
    }
}

const struct workload *provision_wait(void) {
    for (;;) {
        char command[32];
        if (read_command(command, sizeof(command))) {
            if (!command[0]) {
                continue;
            }
            if (command[0] == 'R' && command[1] == 'U' && command[2] == 'N' && command[3] == ' ') {
                const struct workload *workload = workload_find(command + 4);
                if (workload) {
                    return workload;
                }
            }
        }
        uart_puts("ERR COMMAND\r\n");
    }
}
