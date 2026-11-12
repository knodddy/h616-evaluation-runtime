SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.DEFAULT_GOAL := build/h616-runtime.bin
.DELETE_ON_ERROR:

CROSS_COMPILE ?= aarch64-none-elf-
CC := $(CROSS_COMPILE)gcc
OBJCOPY := $(CROSS_COMPILE)objcopy
SERIAL ?= /dev/ttyUSB0

CPPFLAGS := -Iinclude
CFLAGS := -std=c11 -mcpu=cortex-a53 -O2 -g -ffreestanding -mgeneral-regs-only \
	-fno-stack-protector -fno-pie -fno-unwind-tables -fno-asynchronous-unwind-tables \
	-Wall -Wextra -Werror -Wstrict-prototypes -Wmissing-prototypes
ASFLAGS := -mcpu=cortex-a53 -g -Wa,--fatal-warnings
LDFLAGS := -nostdlib -static -Wl,--build-id=none,--fatal-warnings -Tboot/h616.ld

OBJECTS := build/startup.o build/main.o build/workloads.o

build/h616-runtime.bin: build/h616-runtime.elf
	$(OBJCOPY) -O binary $< $@

build/h616-runtime.elf: $(OBJECTS) boot/h616.ld Makefile
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@

build/%.o: src/%.c Makefile
	mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

build/%.o: src/%.S Makefile
	mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(ASFLAGS) -MMD -MP -c $< -o $@

-include $(OBJECTS:.o=.d)
include boot/firmware.mk

.PHONY: format diagnostics console
diagnostics:
	id
	lsusb
	lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS
	@printf '\nSerial devices:\n'
	@for device in /dev/serial/by-id/* /dev/ttyUSB* /dev/ttyACM*; do \
		[[ ! -e "$$device" ]] || ls -l "$$device"; \
	done
	@sunxi-fel --list || { printf 'No accessible FEL device (absent or USB permissions denied).\n'; }

console:
	mkdir -p build
	picocom --baud 115200 --flow n --parity n --databits 8 --logfile build/uart.log "$(SERIAL)"

format:
	git ls-files -z --cached --others --exclude-standard -- '*.c' '*.h' | xargs -0 -r clang-format --style=file -i
	git ls-files -z --cached --others --exclude-standard -- '*.nix' | xargs -0 -r nixfmt
