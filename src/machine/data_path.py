import logging
from typing import Any

from src.machine.cache import Cache
from src.machine.microcode import Signal

logger = logging.getLogger(__name__)


class DataPath:
    def __init__(self, data_mem_size: int, data_init: list[int], input_buffer: list) -> None:
        self.memory = [0] * data_mem_size
        for i, val in enumerate(data_init):
            if i < data_mem_size:
                self.memory[i] = val

        self.cache = Cache()
        self.registers = [0] * 8
        self.registers[7] = data_mem_size - 1

        self.ar = 0
        self.tmp1 = 0
        self.tmp2 = 0
        self.alu_res = 0

        self.flag_z = False
        self.flag_n = False
        self.flag_v = False
        self.flag_c = 0

        self.input_value = 0
        self.input_buffer = input_buffer
        self.output_buffer: list[Any] = []

    def signal_set_ar(self, idx: int) -> None:
        self.ar = self.registers[idx]

    def signal_set_ar_off(self, idx: int, off: int) -> None:
        self.ar = (self.registers[idx] + off) & 0xFFFFFFFF

    def signal_latch_tmp1_reg(self, idx: int) -> None:
        self.tmp1 = self.sign_extend(self.registers[idx])

    def signal_latch_tmp2_reg(self, idx: int) -> None:
        self.tmp2 = self.sign_extend(self.registers[idx])

    def signal_latch_tmp1_imm(self, val: int) -> None:
        self.tmp1 = self.sign_extend(val)

    def signal_latch_tmp2_imm(self, val: int) -> None:
        self.tmp2 = self.sign_extend(val)

    def signal_latch_tmp2_io(self) -> None:
        self.tmp2 = self.input_value

    def signal_latch_tmp1_mem(self):
        val, ticks = self.cache.read(self.ar, self.memory)
        self.tmp1 = self.sign_extend(val)
        return ticks

    def signal_latch_tmp2_mem(self):
        val, ticks = self.cache.read(self.ar, self.memory)
        self.tmp2 = self.sign_extend(val)
        return ticks

    def signal_mem_store(self):
        return self.cache.write(self.ar, self.memory, self.alu_res)

    def alu_compute(self, op: Signal) -> None:
        a, b = self.tmp1, self.tmp2
        res = 0
        flags_ops = {Signal.OP_ADD, Signal.OP_ADC, Signal.OP_SUB}
        a_u = self.tmp1 & 0xFFFFFFFF
        b_u = self.tmp2 & 0xFFFFFFFF

        if op == Signal.OP_ADD:
            res_u = b_u + a_u
            res = b + a
            self.flag_c = 1 if res_u > 0xFFFFFFFF else 0
        elif op == Signal.OP_ADC:
            res_u = b_u + a_u + self.flag_c
            res = b + a + self.flag_c
            self.flag_c = 1 if res_u > 0xFFFFFFFF else 0
        elif op == Signal.OP_SUB:
            res = b - a
            self.flag_c = 1 if b_u >= a_u else 0
        elif op == Signal.OP_MUL:
            res = b * a
        elif op == Signal.OP_DIV:
            res = b // a if a != 0 else 0
        elif op == Signal.OP_REM:
            res = b % a if a != 0 else 0
        elif op == Signal.OP_NEG:
            res = -a
        elif op == Signal.OP_AND:
            res = b & a
        elif op == Signal.OP_OR:
            res = b | a
        elif op == Signal.OP_NOT:
            res = ~a
        elif op == Signal.OP_PASS_TMP1:
            res = a
        elif op == Signal.OP_PASS_TMP2:
            res = b

        if op in flags_ops:
            self.flag_z = (res & 0xFFFFFFFF) == 0
            self.flag_n = (res & 0x80000000) != 0
            if op in (Signal.OP_ADD, Signal.OP_ADC):
                self.flag_v = bool(((self.tmp2 ^ res) & (self.tmp1 ^ res)) & 0x80000000)
            elif op == Signal.OP_SUB:
                self.flag_v = bool(((self.tmp2 ^ self.tmp1) & (self.tmp2 ^ res)) & 0x80000000)
        self.alu_res = res & 0xFFFFFFFF

    def signal_io_read(self, port: int):
        if not self.input_buffer:
            raise StopIteration(f"Input port {port} is empty")
        val = self.input_buffer.pop(0)
        self.input_value = ord(val) if isinstance(val, str) else int(val)

    def signal_io_write(self, port: int) -> None:
        val = self.alu_res
        if port == 3:
            self.output_buffer.append(chr(val & 0xFF))
        else:
            self.output_buffer.append(str(val))

    def signal_wb_from_alu(self, idx: int) -> None:
        self.registers[idx] = self.alu_res

    def sign_extend(self, val):
        val &= 0xFFFFFFFF
        return val if val < 0x80000000 else val - 0x100000000
