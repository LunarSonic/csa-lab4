from dataclasses import dataclass
from enum import IntEnum


class Signal(IntEnum):
    HALT = 0

    DATA_MEMORY_STORE = 1

    INSTRUCTION_MEMORY_LOAD = 2

    IO_READ = 3
    IO_WRITE = 4

    WB_FROM_ALU = 5

    LATCH_TMP2_REG = 6
    LATCH_TMP2_MEM = 7
    LATCH_TMP2_IO = 8
    LATCH_TMP2_IMM = 9

    LATCH_TMP1_REG = 10
    LATCH_TMP1_MEM = 11
    LATCH_TMP1_IMM = 12

    OP_ADD = 13
    OP_ADC = 14
    OP_SUB = 15
    OP_MUL = 16
    OP_DIV = 17
    OP_REM = 18
    OP_NEG = 19
    OP_AND = 20
    OP_OR = 21
    OP_NOT = 22
    OP_PASS_TMP1 = 23
    OP_PASS_TMP2 = 24
    SET_AR_SRC = 25
    SET_AR_DST = 26
    SET_AR_SRC_OFF = 27
    SET_AR_DST_OFF = 28

    COND_TRUE = 29
    COND_EQUAL = 30
    COND_NOT_EQUAL = 31
    COND_GREATER = 32
    COND_GREATER_EQUAL = 33
    COND_LESS = 34
    COND_LESS_EQUAL = 35

    PC_BRANCH = 36
    LATCH_IR = 37
    MPC_DECODE = 38


@dataclass(frozen=True)
class MicroInstruction:
    signals: frozenset[Signal]
    next_addr: int


def mi(signals: set[Signal], next_addr: int = 0) -> MicroInstruction:
    return MicroInstruction(signals=frozenset(signals), next_addr=next_addr)


DISPATCH_OPCODE_SRC_DST = {
    (1, 1, 0): 1,   # MOVE imm, reg        [1-2]
    (1, 0, 0): 3,   # MOVE reg, reg        [3-4]
    (1, 0, 2): 5,   # MOVE reg, [reg]      [5-7]
    (1, 2, 0): 8,   # MOVE [reg], reg      [8-10]
    (1, 0, 3): 11,  # MOVE reg, [reg+off]  [11-13]
    (1, 1, 2): 14,  # MOVE imm, [reg]      [14-16]
    (1, 3, 0): 17,  # MOVE [reg+off], reg  [17-19]
    (2, 1, 0): 20,  # ADD imm, reg         [20-22]
    (2, 0, 0): 23,  # ADD reg, reg         [23-25]
    (3, 1, 0): 26,  # ADC imm, reg         [26-28]
    (3, 0, 0): 29,  # ADC reg, reg         [29-31]
    (4, 1, 0): 32,  # SUB imm, reg         [32-34]
    (4, 0, 0): 35,  # SUB reg, reg         [35-37]
    (5, 0, 0): 38,  # MUL reg, reg         [38-40]
    (6, 0, 0): 41,  # DIV reg, reg         [41-43]
    (7, 0, 0): 44,  # REM reg, reg         [44-46]
    (8, 0, 0): 47,  # NEG reg              [47-48]
    (9, 0, 0): 49,  # AND reg, reg         [49-51]
    (10, 0, 0): 52, # OR reg, reg          [52-54]
    (11, 0, 0): 55, # NOT reg              [55-56]
    (12, 1, 0): 57, # CMP imm, reg         [57-59]
    (12, 0, 0): 60, # CMP reg, reg         [60-62]
    (13, 1, 0): 63, # IN port, reg         [63-64]
    (14, 0, 1): 65, # OUT reg, port        [65-66]
    (15, 0, 1): 67, # JMP imm              [67]
    (16, 0, 1): 68, # BEQ imm              [68]
    (17, 0, 1): 69, # BNE imm              [69]
    (18, 0, 1): 70, # BGE imm              [70]
    (19, 0, 1): 71, # BGT imm              [71]
    (20, 0, 1): 72, # BLE imm              [72]
    (21, 0, 1): 73, # BLT imm              [73]
    (0, 0, 0): 74,  # HALT                 [74]
}

MICROPROGRAM: list[MicroInstruction] = [mi(set(), 0)] * 75

# [0] FETCH
MICROPROGRAM[0] = mi({Signal.INSTRUCTION_MEMORY_LOAD, Signal.LATCH_IR, Signal.MPC_DECODE})

# MOVE imm, reg
MICROPROGRAM[1] = mi({Signal.LATCH_TMP1_IMM}, next_addr=2)
MICROPROGRAM[2] = mi({Signal.OP_PASS_TMP1, Signal.WB_FROM_ALU}, next_addr=0)

# MOVE reg, reg
MICROPROGRAM[3] = mi({Signal.LATCH_TMP1_REG}, next_addr=4)
MICROPROGRAM[4] = mi({Signal.OP_PASS_TMP1, Signal.WB_FROM_ALU}, next_addr=0)

# MOVE reg, [reg]
MICROPROGRAM[5] = mi({Signal.SET_AR_DST}, next_addr=6)
MICROPROGRAM[6] = mi({Signal.LATCH_TMP1_REG}, next_addr=7)
MICROPROGRAM[7] = mi({Signal.OP_PASS_TMP1, Signal.DATA_MEMORY_STORE}, next_addr=0)

# MOVE [reg], reg
MICROPROGRAM[8] = mi({Signal.SET_AR_SRC}, next_addr=9)
MICROPROGRAM[9] = mi({Signal.LATCH_TMP1_MEM}, next_addr=10)
MICROPROGRAM[10] = mi({Signal.OP_PASS_TMP1, Signal.WB_FROM_ALU}, next_addr=0)

# MOVE reg, [reg+off]
MICROPROGRAM[11] = mi({Signal.SET_AR_DST_OFF}, next_addr=12)
MICROPROGRAM[12] = mi({Signal.LATCH_TMP1_REG}, next_addr=13)
MICROPROGRAM[13] = mi({Signal.OP_PASS_TMP1, Signal.DATA_MEMORY_STORE}, next_addr=0)

# MOVE imm, [reg]
MICROPROGRAM[14] = mi({Signal.SET_AR_DST}, next_addr=15)
MICROPROGRAM[15] = mi({Signal.LATCH_TMP1_IMM}, next_addr=16)
MICROPROGRAM[16] = mi({Signal.OP_PASS_TMP1, Signal.DATA_MEMORY_STORE}, next_addr=0)

# MOVE [reg+off], reg
MICROPROGRAM[17] = mi({Signal.SET_AR_SRC_OFF}, next_addr=18)
MICROPROGRAM[18] = mi({Signal.LATCH_TMP1_MEM}, next_addr=19)
MICROPROGRAM[19] = mi({Signal.OP_PASS_TMP1, Signal.WB_FROM_ALU}, next_addr=0)

# ADD imm, reg
MICROPROGRAM[20] = mi({Signal.LATCH_TMP1_IMM}, next_addr=21)
MICROPROGRAM[21] = mi({Signal.LATCH_TMP2_REG}, next_addr=22)
MICROPROGRAM[22] = mi({Signal.OP_ADD, Signal.WB_FROM_ALU}, next_addr=0)

# ADD reg, reg
MICROPROGRAM[23] = mi({Signal.LATCH_TMP1_REG}, next_addr=24)
MICROPROGRAM[24] = mi({Signal.LATCH_TMP2_REG}, next_addr=25)
MICROPROGRAM[25] = mi({Signal.OP_ADD, Signal.WB_FROM_ALU}, next_addr=0)

# ADC imm, reg
MICROPROGRAM[26] = mi({Signal.LATCH_TMP1_IMM}, next_addr=27)
MICROPROGRAM[27] = mi({Signal.LATCH_TMP2_REG}, next_addr=28)
MICROPROGRAM[28] = mi({Signal.OP_ADC, Signal.WB_FROM_ALU}, next_addr=0)

# ADC reg, reg
MICROPROGRAM[29] = mi({Signal.LATCH_TMP1_REG}, next_addr=30)
MICROPROGRAM[30] = mi({Signal.LATCH_TMP2_REG}, next_addr=31)
MICROPROGRAM[31] = mi({Signal.OP_ADC, Signal.WB_FROM_ALU}, next_addr=0)

# SUB imm, reg
MICROPROGRAM[32] = mi({Signal.LATCH_TMP1_IMM}, next_addr=33)
MICROPROGRAM[33] = mi({Signal.LATCH_TMP2_REG}, next_addr=34)
MICROPROGRAM[34] = mi({Signal.OP_SUB, Signal.WB_FROM_ALU}, next_addr=0)

# SUB reg, reg
MICROPROGRAM[35] = mi({Signal.LATCH_TMP1_REG}, next_addr=36)
MICROPROGRAM[36] = mi({Signal.LATCH_TMP2_REG}, next_addr=37)
MICROPROGRAM[37] = mi({Signal.OP_SUB, Signal.WB_FROM_ALU}, next_addr=0)

# MUL reg, reg
MICROPROGRAM[38] = mi({Signal.LATCH_TMP1_REG}, next_addr=39)
MICROPROGRAM[39] = mi({Signal.LATCH_TMP2_REG}, next_addr=40)
MICROPROGRAM[40] = mi({Signal.OP_MUL, Signal.WB_FROM_ALU}, next_addr=0)

# DIV reg, reg
MICROPROGRAM[41] = mi({Signal.LATCH_TMP1_REG}, next_addr=42)
MICROPROGRAM[42] = mi({Signal.LATCH_TMP2_REG}, next_addr=43)
MICROPROGRAM[43] = mi({Signal.OP_DIV, Signal.WB_FROM_ALU}, next_addr=0)

# REM reg, reg
MICROPROGRAM[44] = mi({Signal.LATCH_TMP1_REG}, next_addr=45)
MICROPROGRAM[45] = mi({Signal.LATCH_TMP2_REG}, next_addr=46)
MICROPROGRAM[46] = mi({Signal.OP_REM, Signal.WB_FROM_ALU}, next_addr=0)

# NEG reg
MICROPROGRAM[47] = mi({Signal.LATCH_TMP1_REG}, next_addr=48)
MICROPROGRAM[48] = mi({Signal.OP_NEG, Signal.WB_FROM_ALU}, next_addr=0)

# AND reg, reg
MICROPROGRAM[49] = mi({Signal.LATCH_TMP1_REG}, next_addr=50)
MICROPROGRAM[50] = mi({Signal.LATCH_TMP2_REG}, next_addr=51)
MICROPROGRAM[51] = mi({Signal.OP_AND, Signal.WB_FROM_ALU}, next_addr=0)

# OR reg, reg
MICROPROGRAM[52] = mi({Signal.LATCH_TMP1_REG}, next_addr=53)
MICROPROGRAM[53] = mi({Signal.LATCH_TMP2_REG}, next_addr=54)
MICROPROGRAM[54] = mi({Signal.OP_OR, Signal.WB_FROM_ALU}, next_addr=0)

# NOT reg
MICROPROGRAM[55] = mi({Signal.LATCH_TMP1_REG}, next_addr=56)
MICROPROGRAM[56] = mi({Signal.OP_NOT, Signal.WB_FROM_ALU}, next_addr=0)

# CMP imm, reg
MICROPROGRAM[57] = mi({Signal.LATCH_TMP1_IMM}, next_addr=58)
MICROPROGRAM[58] = mi({Signal.LATCH_TMP2_REG}, next_addr=59)
MICROPROGRAM[59] = mi({Signal.OP_SUB}, next_addr=0)
# CMP reg, reg
MICROPROGRAM[60] = mi({Signal.LATCH_TMP1_REG}, next_addr=61)
MICROPROGRAM[61] = mi({Signal.LATCH_TMP2_REG}, next_addr=62)
MICROPROGRAM[62] = mi({Signal.OP_SUB}, next_addr=0)

# IN port, reg
MICROPROGRAM[63] = mi({Signal.IO_READ, Signal.LATCH_TMP2_IO}, next_addr=64)
MICROPROGRAM[64] = mi({Signal.OP_PASS_TMP2, Signal.WB_FROM_ALU}, next_addr=0)

# OUT reg, port
MICROPROGRAM[65] = mi({Signal.LATCH_TMP1_REG}, next_addr=66)
MICROPROGRAM[66] = mi({Signal.OP_PASS_TMP1, Signal.IO_WRITE}, next_addr=0)

# JMP imm
MICROPROGRAM[67] = mi({Signal.COND_TRUE, Signal.PC_BRANCH}, next_addr=0)
# BEQ imm
MICROPROGRAM[68] = mi({Signal.COND_EQUAL, Signal.PC_BRANCH}, next_addr=0)
# BNE imm
MICROPROGRAM[69] = mi({Signal.COND_NOT_EQUAL, Signal.PC_BRANCH}, next_addr=0)
# BGE imm
MICROPROGRAM[70] = mi({Signal.COND_GREATER_EQUAL, Signal.PC_BRANCH}, next_addr=0)
# BGT imm
MICROPROGRAM[71] = mi({Signal.COND_GREATER, Signal.PC_BRANCH}, next_addr=0)
# BLE imm
MICROPROGRAM[72] = mi({Signal.COND_LESS_EQUAL, Signal.PC_BRANCH}, next_addr=0)
# BLT imm
MICROPROGRAM[73] = mi({Signal.COND_LESS, Signal.PC_BRANCH}, next_addr=0)

# HALT
MICROPROGRAM[74] = mi({Signal.HALT}, next_addr=74)

MICROCODE_WORD_BYTES = 6


def encode_microprogram(program: list[MicroInstruction]) -> bytes:
    result = bytearray()
    for mc in program:
        word = 0
        for signal in mc.signals:
            word |= 1 << int(signal)
        word |= (mc.next_addr & 0x1FF) << 39
        result += word.to_bytes(MICROCODE_WORD_BYTES, byteorder="big")
    return bytes(result)


def decode_microinstruction(data: bytes, addr: int) -> MicroInstruction:
    offset = addr * MICROCODE_WORD_BYTES
    word = int.from_bytes(data[offset : offset + MICROCODE_WORD_BYTES], byteorder="big")
    signals = frozenset(Signal(i) for i in range(39) if (word >> i) & 1 and i in Signal._value2member_map_)
    next_addr = (word >> 39) & 0x1FF
    return MicroInstruction(signals, next_addr)


MICROCODE_BYTES: bytes = encode_microprogram(MICROPROGRAM)
