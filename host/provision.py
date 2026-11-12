import argparse
from contextlib import contextmanager
import math
import re
import sys
import time

import serial


@contextmanager
def open_uart(port, timeout):
    uart = serial.Serial(
        baudrate=115200,
        timeout=timeout,
        write_timeout=timeout,
        exclusive=True,
    )
    uart.port = port
    uart.dtr = False
    uart.rts = False
    try:
        uart.open()
        uart.reset_input_buffer()
        yield uart
    finally:
        uart.close()


def read_line(uart, deadline):
    line = bytearray()
    while len(line) < 128:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("UART response timed out; check UART and reset the board before retrying")
        uart.timeout = remaining
        value = uart.read(1)
        if value == b"\n":
            return bytes(line).removesuffix(b"\r")
        line.extend(value)
    raise ValueError("UART response exceeds 127 bytes")


def provision(port, workload, timeout):
    workload = workload.upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{0,23}", workload):
        raise ValueError("specify a workload, for example WORKLOAD=ADD")
    expected = f"ACK {workload}".encode("ascii")
    command = f"RUN {workload}\n".encode("ascii")
    with open_uart(port, timeout) as uart:
        for request, reply in ((b"\x18", b"SYNC"), (command, expected)):
            if uart.write(request) != len(request):
                raise OSError("incomplete command write; reset the board before retrying")
            deadline = time.monotonic() + timeout
            while True:
                read_deadline = min(deadline, time.monotonic() + 0.25) if reply == b"SYNC" else deadline
                try:
                    response = read_line(uart, read_deadline)
                except TimeoutError as error:
                    if reply != b"SYNC" or time.monotonic() >= deadline:
                        raise TimeoutError(
                            f"timed out waiting for {reply.decode()}; check UART and reset the board before retrying"
                        ) from error
                    if uart.write(request) != len(request):
                        raise OSError("incomplete command write; reset the board before retrying")
                    continue
                if response == reply:
                    break
                if reply == b"SYNC" and response == b"ERR COMMAND":
                    continue
                if response.startswith(b"ACK ") or response.startswith(b"ERR "):
                    raise ValueError(f"unexpected response: {response!r}")
    return workload


def positive_timeout(value):
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return timeout


def main():
    parser = argparse.ArgumentParser(description="Provision one H616 workload over UART.")
    parser.add_argument("workload")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--timeout", type=positive_timeout, default=5.0)
    args = parser.parse_args()
    try:
        workload = provision(args.port, args.workload, args.timeout)
    except (OSError, ValueError) as error:
        print(f"Provisioning failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    print(f"ACK {workload}")
    print("Disconnect UART now. The workload starts 10 seconds after ACK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
