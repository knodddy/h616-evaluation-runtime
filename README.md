# H616 evaluation runtime

Bare-metal C and assembly runtime for H616 workload experiments

```sh
nix develop
make         # Build ELF and binary in build/
make format  # Format C, headers, and Nix
make -j4 build/u-boot-sd.img  # Fetch and build SPL, TF-A, and U-Boot
```

For board access, run `make diagnostics` to list USB, serial, and FEL devices.
Use `make console SERIAL=/dev/ttyUSB0` for a 115200-baud UART console; output is
logged to `build/uart.log`. Exit with Ctrl-A, Ctrl-X.

The U-Boot image stops at the UART prompt. Connect H4 pin 1 to adapter GND,
pin 2 to RX, and pin 3 to TX using 3.3 V logic; leave adapter VCC disconnected.

To launch the runtime, build with `make` and open `make console` using the updated
U-Boot image. At its prompt, run `loadx 0x4a000000`, then press Ctrl-A, Ctrl-S and
enter `build/h616-runtime.bin`. After the transfer completes, run:

```text
dcache off
icache off
go 0x4a000000
```

The runtime prints `runtime started` and idles. Power-cycle to return to U-Boot.

SD boot and the UART console are verified; DDR stability under workload is untested.
It contains no partition table or filesystem. Writing it to a card replaces that
card's existing boot and partition data.
