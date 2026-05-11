import logging
import sys

from src.machine.control_unit import ControlUnit
from src.machine.data_path import DataPath
from src.machine.microcode import MICROCODE_BYTES


def run_simulation(code_bin: str, data_bin: str, input_file: str) -> None:
    with open(code_bin, "rb") as f:
        instructions = bytearray(f.read())

    with open(data_bin, "rb") as f:
        raw_data = f.read()
        data_init = [int.from_bytes(raw_data[i : i + 4], "big", signed=True) for i in range(0, len(raw_data), 4)]

    input_tokens = []
    try:
        with open(input_file) as f:
            content = f.read()
            input_tokens = [ord(c) for c in content]
    except FileNotFoundError:
        pass

    dp = DataPath(data_mem_size=2048, data_init=data_init, input_buffer=input_tokens)
    cu = ControlUnit(instructions, dp, MICROCODE_BYTES)

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(name)s:%(message)s")
    logging.info("Simulation started")

    try:
        while not cu.halted and cu.ticks < 1000000:
            cu.step()
    except EOFError:
        logging.warning("Input buffer is empty")
    except StopIteration:
        pass

    print(f"Final Output:\n{''.join(dp.output_buffer)}")
    print(f"Total Ticks:  {cu.ticks}")
    print(dp.cache.stats())


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: machine.py <code.bin> <data.bin> <input.txt>")
    else:
        run_simulation(sys.argv[1], sys.argv[2], sys.argv[3])
