# H616 evaluation runtime

Bare-metal C and assembly runtime for H616 workload experiments. Boots from microSD
through U-Boot SPL and TF-A directly into the runtime.

```sh
nix develop
make
make flash DEVICE=/dev/sdX
```

`make` builds `build/h616-sd.img`. Flash the whole microSD device, not a partition;
this overwrites its boot and partition data.

With the flashed microSD inserted and the board powered off, use a 3.3 V UART
adapter and leave its VCC disconnected:

1. Connect adapter RX to H4 pin 2 and GND to H4 pin 1, then plug the adapter into
   the host's USB port. Leave TX disconnected.
2. Connect power to the board.
3. Wait a few seconds, then connect adapter TX to H4 pin 3.
4. Provision the selected workload:

   ```sh
   make provision WORKLOAD=ADD SERIAL=/dev/ttyUSB0
   ```

5. After `ACK ADD`, disconnect all UART leads from the board within 10 seconds.

The selected workload starts after the disconnect delay and runs until reset.
Use `WORKLOAD=IDLE` for the wait-for-event loop. Power-cycle the board to select
another workload, following the same connection sequence.

`make console SERIAL=/dev/ttyUSB0` optionally captures boot output at 115200 baud
in `build/uart.log`. Exit with Ctrl-A, Ctrl-X before provisioning.

`make format` formats C, headers and Nix; `make clean` removes build outputs and
downloaded firmware sources.

See the [execution diagram](analysis/program-flow/execution-flow.svg) and
[VNA findings](analysis/findings.md).
