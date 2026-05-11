import logging
from collections.abc import Set
from typing import Any

from src.isa.isa import Instruction, decode_instruction
from src.machine.microcode import (
    DISPATCH_DST_MODE,
    DISPATCH_OPCODE,
    DISPATCH_SRC_MODE,
    DISPATCH_WB_MODE,
    MICROCODE_BYTES,
    Signal,
    decode_microinstruction,
)

logger = logging.getLogger(__name__)


class ControlUnit:
    def __init__(self, instr_mem: bytearray, data_path: Any, microcode_bin: bytes) -> None:
        self.instr_mem = instr_mem
        self.dp = data_path
        self.microcode = microcode_bin

        self.pc: int = 0
        self.mpc: int = 0
        self.ir: Instruction | None = None
        self.ticks: int = 0
        self.stall_cycles: int = 0
        self.halted: bool = False
        self.branch_done: bool = False

    def step(self) -> None:
        if self.halted:
            return

        if self.stall_cycles > 0:
            self.stall_cycles -= 1
            self.ticks += 1
            return

        signals = decode_microinstruction(MICROCODE_BYTES, self.mpc)

        logger.debug(self)

        self.execute_signals(signals)
        self.next_mpc(signals)
        self.ticks += 1

    def execute_signals(self, signals: Set[Signal]) -> None:
        if Signal.HALT in signals:
            self.halted = True

        if Signal.INSTRUCTION_MEMORY_LOAD in signals:
            self.ir, _ = decode_instruction(self.instr_mem, self.pc)

        if any(
            s in signals
            for s in (
                Signal.LATCH_IR,
                Signal.IO_READ,
                Signal.IO_WRITE,
                Signal.LATCH_TMP1_REG,
                Signal.LATCH_TMP1_IMM,
                Signal.LATCH_TMP2_REG,
                Signal.LATCH_TMP2_IMM,
                Signal.SET_AR_SRC,
                Signal.SET_AR_DST,
                Signal.PC_BRANCH,
            )
        ):
            assert self.ir is not None, "IR must be loaded before use"

        if Signal.LATCH_IR in signals:
            assert self.ir is not None
            size = 2
            if self.ir.src_mode.value in (1, 3):
                size += 4
            if self.ir.dst_mode.value in (1, 3):
                size += 4
            self.pc += size

        if Signal.LATCH_TMP1_MEM in signals:
            self.stall_cycles = self.dp.signal_latch_tmp1_mem() - 1

        if Signal.LATCH_TMP2_MEM in signals:
            self.stall_cycles = self.dp.signal_latch_tmp2_mem() - 1

        if Signal.DATA_MEMORY_STORE in signals:
            delay = self.dp.signal_mem_store()
            self.stall_cycles = delay - 1

        if Signal.IO_READ in signals:
            assert self.ir is not None
            self.dp.signal_io_read(self.ir.src_imm)
        if Signal.LATCH_TMP2_IO in signals:
            self.dp.signal_latch_tmp2_io()
        if Signal.IO_WRITE in signals:
            assert self.ir is not None
            self.dp.signal_io_write(self.ir.dst_imm)

        if Signal.LATCH_TMP1_REG in signals:
            assert self.ir is not None
            self.dp.signal_latch_tmp1_reg(self.ir.src_index.value)
        if Signal.LATCH_TMP1_IMM in signals:
            assert self.ir is not None
            self.dp.signal_latch_tmp1_imm(self.ir.src_imm)
        if Signal.LATCH_TMP2_REG in signals:
            assert self.ir is not None
            self.dp.signal_latch_tmp2_reg(self.ir.dst_index.value)
        if Signal.LATCH_TMP2_IMM in signals:
            assert self.ir is not None
            self.dp.signal_latch_tmp2_imm(self.ir.dst_imm)

        for s in signals:
            if Signal.OP_ADD <= s <= Signal.OP_PASS_TMP2:
                self.dp.alu_compute(s)
            if Signal.WB_FROM_ALU in signals:
                assert self.ir is not None
                self.dp.signal_wb_from_alu(self.ir.dst_index.value)

        if Signal.SET_AR_SRC in signals or Signal.SET_AR_DST in signals:
            assert self.ir is not None
            idx = self.ir.src_index.value if Signal.SET_AR_SRC in signals else self.ir.dst_index.value
            self.dp.signal_set_ar(idx)

        if Signal.SET_AR_SRC_OFF in signals or Signal.SET_AR_DST_OFF in signals:
            assert self.ir is not None
            idx = self.ir.src_index.value if Signal.SET_AR_SRC_OFF in signals else self.ir.dst_index.value
            off = self.ir.src_imm if Signal.SET_AR_SRC_OFF in signals else self.ir.dst_imm
            self.dp.signal_set_ar_off(idx, off)

        if Signal.COND_EQUAL in signals:
            self.branch_done = self.dp.flag_z
        if Signal.COND_NOT_EQUAL in signals:
            self.branch_done = not self.dp.flag_z
        if Signal.COND_TRUE in signals:
            self.branch_done = True
        if Signal.COND_GREATER in signals:
            self.branch_done = (not self.dp.flag_z) and (self.dp.flag_n == self.dp.flag_v)
        if Signal.COND_GREATER_EQUAL in signals:
            self.branch_done = self.dp.flag_n == self.dp.flag_v
        if Signal.COND_LESS in signals:
            self.branch_done = self.dp.flag_n != self.dp.flag_v
        if Signal.COND_LESS_EQUAL in signals:
            self.branch_done = self.dp.flag_z or (self.dp.flag_n != self.dp.flag_v)

        if Signal.PC_BRANCH in signals and self.branch_done:
            assert self.ir is not None
            self.pc = self.ir.dst_imm

    def next_mpc(self, signals: Set[Signal]) -> None:
        if Signal.MPC_ZERO in signals:
            self.mpc = 0
            return

        assert self.ir is not None, "IR must be loaded for dispatch signals"

        if Signal.MPC_DISPATCH_OP in signals:
            self.mpc = DISPATCH_OPCODE[self.ir.opcode.value]
        elif Signal.MPC_DISPATCH_SRC in signals:
            self.mpc = DISPATCH_SRC_MODE[self.ir.src_mode.value]
        elif Signal.MPC_DISPATCH_DST in signals:
            self.mpc = DISPATCH_DST_MODE[self.ir.dst_mode.value]
        elif Signal.MPC_DISPATCH_WB in signals:
            self.mpc = DISPATCH_WB_MODE[self.ir.dst_mode.value]
        elif Signal.MPC_NEXT in signals:
            self.mpc += 1

    def __repr__(self) -> str:
        regs = self.dp.registers
        flags = f"Z:{int(self.dp.flag_z)} N:{int(self.dp.flag_n)} V:{int(self.dp.flag_v)} C:{int(self.dp.flag_c)}"
        return (
            f"TICK: {self.ticks:5} | PC: {self.pc:3} | mPC: {self.mpc:2} | "
            f"AR: {self.dp.ar:3} | TMP1: {self.dp.tmp1:4} | TMP2: {self.dp.tmp2:4} | "
            f"{flags} | R0: {regs[0]:3} R1: {regs[1]:3} R2: {regs[2]:3} "
            f"R3: {regs[3]:3} R4: {regs[4]:3} R5: {regs[5]:3} R6: {regs[6]:3} R7: {regs[7]:3}"
        )
