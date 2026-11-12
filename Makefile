SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.DEFAULT_GOAL := build/h616-sd.img
.DELETE_ON_ERROR:

CROSS_COMPILE ?= aarch64-none-elf-
CC := $(CROSS_COMPILE)gcc
OBJCOPY := $(CROSS_COMPILE)objcopy
SERIAL ?= /dev/ttyUSB0
WORKLOAD ?=
export SERIAL WORKLOAD DEVICE

CPPFLAGS := -Iinclude
CFLAGS := -std=c11 -mcpu=cortex-a53 -O2 -g -ffreestanding -mgeneral-regs-only \
	-fno-stack-protector -fno-pie -fno-unwind-tables -fno-asynchronous-unwind-tables \
	-Wall -Wextra -Werror -Wstrict-prototypes -Wmissing-prototypes
ASFLAGS := -mcpu=cortex-a53 -g -Wa,--fatal-warnings
LDFLAGS := -nostdlib -static -Wl,--build-id=none,--fatal-warnings -Tboot/h616.ld

OBJECTS := build/startup.o build/main.o build/platform.o build/provision.o \
	build/uart.o build/workload.o build/workloads.o

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

.PHONY: format console provision clean flash
flash: build/h616-sd.img
	@[[ -n "$${DEVICE:-}" ]] || { printf 'Usage: make flash DEVICE=/dev/sdX\n' >&2; exit 2; }; \
	device=$$(readlink -e -- "$$DEVICE") || \
		{ printf 'Device does not exist: %s\n' "$$DEVICE" >&2; exit 2; }; \
	[[ -b "$$device" && $$(lsblk -dnro TYPE "$$device") == disk ]] || \
		{ printf 'DEVICE must be a whole disk, not a partition or file.\n' >&2; exit 2; }; \
	mounts=$$(lsblk -nrpo MOUNTPOINTS "$$device"); \
	[[ -z "$${mounts//[[:space:]]/}" ]] || \
		{ printf 'Unmount all partitions and deactivate swap on %s first.\n' "$$device" >&2; exit 2; }; \
	[[ $$(lsblk -dnro RO "$$device") == 0 ]] || \
		{ printf 'Device is read-only.\n' >&2; exit 2; }; \
	[[ $$(lsblk -bdnro SIZE "$$device") -ge $$(stat -c %s "$<") ]] || \
		{ printf 'Device is smaller than the image.\n' >&2; exit 2; }; \
	lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS "$$device"; \
	printf 'This overwrites boot and partition data. Type %s to flash: ' "$$device"; \
	read -r confirmation; \
	[[ "$$confirmation" == "$$device" ]] || { printf 'Cancelled.\n'; exit 1; }; \
	sudo "$$(command -v dd)" if="$$(realpath -- "$<")" of="$$device" \
		bs=4M conv=fsync,nocreat,notrunc oflag=nofollow status=progress

clean:
	rm -rf -- build

provision:
	python3 host/provision.py "$$WORKLOAD" --port "$$SERIAL"

console:
	mkdir -p build
	picocom --baud 115200 --flow n --parity n --databits 8 --send-cmd "sz --xmodem" --logfile build/uart.log "$(SERIAL)"

format:
	git ls-files -z --cached --others --exclude-standard -- '*.c' '*.h' | xargs -0 -r clang-format --style=file -i
	git ls-files -z --cached --others --exclude-standard -- '*.nix' | xargs -0 -r nixfmt
