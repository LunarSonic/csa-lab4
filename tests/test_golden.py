import contextlib
import io
import logging
import os
import tempfile

import pytest

import src.machine.machine as machine
import src.translator.translator as translator
from src.isa.isa import from_bytes, to_hex


@pytest.mark.golden_test("golden/*.yaml")
def test_translator_and_machine(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = os.path.join(tmpdir, "source.alg")
        input_file = os.path.join(tmpdir, "input.txt")
        target_code = os.path.join(tmpdir, "target.bin")
        target_data = os.path.join(tmpdir, "target_data.bin")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write(golden["in_source"])
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source_file, target_code, target_data)
            print("============================================================")
            machine.run_simulation(target_code, target_data, input_file)

        with open(target_code, "rb") as f:
            instructions_bin = f.read()

        with open(target_data, "rb") as f:
            data_bin = f.read()

        instructions_hex = to_hex(from_bytes(bytearray(instructions_bin)))
        data_list = [int.from_bytes(data_bin[i : i + 4], "big", signed=True) for i in range(0, len(data_bin), 4)]
        data_hex = "\n".join([f"{i * 4:3} : {val}" for i, val in enumerate(data_list)])

        assert instructions_hex == golden.out["out_instructions_hex"]
        assert data_hex == golden.out["out_data_hex"]
        assert stdout.getvalue() == golden.out["out_stdout"]

        log_output = caplog.text
        assert log_output[:40000].strip() + "\nEOF" == golden.out["out_log"]
