import logging
from collections.abc import Set
from typing import Any

from src.isa.isa import Instruction, decode_instruction
from src.machine.microcode import DISPATCH_OPCODE_SRC_DST, MicroInstruction, Signal, decode_microinstruction

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
            logger.debug(self)
            return

        micro_cmd = decode_microinstruction(self.microcode, self.mpc)
        self.execute_signals(micro_cmd.signals)
        self.next_mpc(micro_cmd)
        self.ticks += 1
        logger.debug(self)

    def execute_signals(self, signals: Set[Signal]) -> None:
        if Signal.HALT in signals:
            self.halted = True
            return

        if Signal.INSTRUCTION_MEMORY_LOAD in signals:
            self.ir, _ = decode_instruction(self.instr_mem, self.pc)

        if self.ir is None:
            return

        ir = self.ir

        if Signal.LATCH_IR in signals:
            logger.debug(f"signal_latch_ir @{ir.opcode.name}")
            size = 2 + (4 if ir.src_mode.value in (1, 3) else 0) + (4 if ir.dst_mode.value in (1, 3) else 0)
            self.pc += size

        if Signal.SET_AR_SRC in signals:
            self.dp.signal_set_ar(self.ir.src_index.value)
        if Signal.SET_AR_DST in signals:
            self.dp.signal_set_ar(self.ir.dst_index.value)
        if Signal.SET_AR_SRC_OFF in signals:
            self.dp.signal_set_ar_off(self.ir.src_index.value, self.ir.src_imm)
        if Signal.SET_AR_DST_OFF in signals:
            self.dp.signal_set_ar_off(self.ir.dst_index.value, self.ir.dst_imm)

        if Signal.IO_READ in signals:
            self.dp.signal_io_read(self.ir.src_imm)
        if Signal.LATCH_TMP1_IMM in signals:
            self.dp.signal_latch_tmp1_imm(self.ir.src_imm)
        if Signal.LATCH_TMP1_REG in signals:
            self.dp.signal_latch_tmp1_reg(self.ir.src_index.value)
        if Signal.LATCH_TMP2_REG in signals:
            self.dp.signal_latch_tmp2_reg(self.ir.dst_index.value)
        if Signal.LATCH_TMP2_IMM in signals:
            self.dp.signal_latch_tmp2_imm(self.ir.dst_imm)
        if Signal.LATCH_TMP2_IO in signals:
            self.dp.signal_latch_tmp2_io()

        if Signal.LATCH_TMP1_MEM in signals:
            self.stall_cycles = self.dp.signal_latch_tmp1_mem() - 1
        if Signal.LATCH_TMP2_MEM in signals:
            self.stall_cycles = self.dp.signal_latch_tmp2_mem() - 1

        alu_op = next((s for s in signals if Signal.OP_ADD <= s <= Signal.OP_PASS_TMP2), None)
        if alu_op:
            self.dp.alu_compute(alu_op)

        if Signal.WB_FROM_ALU in signals:
            self.dp.signal_wb_from_alu(self.ir.dst_index.value)
        if Signal.DATA_MEMORY_STORE in signals:
            self.stall_cycles = self.dp.signal_mem_store() - 1
        if Signal.IO_WRITE in signals:
            self.dp.signal_io_write(self.ir.dst_imm)

        if any(Signal.COND_TRUE <= s <= Signal.COND_LESS_EQUAL for s in signals):
            self.branch_done = False
            if Signal.COND_TRUE in signals:
                self.branch_done = True
            elif Signal.COND_EQUAL in signals:
                self.branch_done = self.dp.flag_z
            elif Signal.COND_NOT_EQUAL in signals:
                self.branch_done = not self.dp.flag_z
            elif Signal.COND_GREATER in signals:
                self.branch_done = (not self.dp.flag_z) and (self.dp.flag_n == self.dp.flag_v)
            elif Signal.COND_GREATER_EQUAL in signals:
                self.branch_done = self.dp.flag_n == self.dp.flag_v
            elif Signal.COND_LESS in signals:
                self.branch_done = self.dp.flag_n != self.dp.flag_v
            elif Signal.COND_LESS_EQUAL in signals:
                self.branch_done = self.dp.flag_z or (self.dp.flag_n != self.dp.flag_v)

            if Signal.PC_BRANCH in signals and self.branch_done:
                self.pc = self.ir.dst_imm

    def next_mpc(self, micro_cmd: MicroInstruction) -> None:
        if Signal.MPC_DECODE in micro_cmd.signals:
            assert self.ir is not None
            key = (self.ir.opcode.value, self.ir.src_mode.value, self.ir.dst_mode.value)
            self.mpc = DISPATCH_OPCODE_SRC_DST[key]
        else:
            self.mpc = micro_cmd.next_addr

    def __repr__(self) -> str:
        regs = self.dp.registers
        flags = f"Z:{int(self.dp.flag_z)} N:{int(self.dp.flag_n)} V:{int(self.dp.flag_v)} C:{int(self.dp.flag_c)}"
        return (
            f"TICK: {self.ticks:5} | PC: {self.pc:3} | mPC: {self.mpc:2} | "
            f"AR: {self.dp.ar:3} | TMP1: {self.dp.tmp1:4} | TMP2: {self.dp.tmp2:4} | "
            f"{flags} | R0: {regs[0]:3} R1: {regs[1]:3} R2: {regs[2]:3} "
            f"R3: {regs[3]:3} R4: {regs[4]:3} R5: {regs[5]:3} R6: {regs[6]:3} R7: {regs[7]:3}"
        )
