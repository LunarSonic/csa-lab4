import json
from enum import Enum


class Opcode(Enum):
    HALT = 0
    MOVE = 1
    ADD = 2
    ADC = 3
    SUB = 4
    MUL = 5
    DIV = 6
    REM = 7
    NEG = 8
    AND = 9
    OR = 10
    NOT = 11
    CMP = 12
    IN = 13
    OUT = 14
    JMP = 15
    BEQ = 16
    BNE = 17
    BGE = 18
    BGT = 19
    BLE = 20
    BLT = 21

    def __str__(self):
        return self.name


class AddrMode(Enum):
    DIRECT = 0
    IMMEDIATE = 1
    INDIRECT = 2
    INDIRECT_OFFSET = 3

    def __str__(self):
        return self.name


class Register(Enum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7

    def __str__(self):
        return self.name


class Instruction:
    def __init__(self, opcode, src_mode, src_index, dst_mode, dst_index, src_imm=0, dst_imm=0) -> None:
        self.opcode = opcode
        self.src_mode = src_mode
        self.src_index = src_index
        self.dst_mode = dst_mode
        self.dst_index = dst_index
        self.src_imm = src_imm
        self.dst_imm = dst_imm


def need_imm(mode: AddrMode) -> bool:
    return mode in (AddrMode.IMMEDIATE, AddrMode.INDIRECT_OFFSET)


def encode_instruction(instruction: Instruction) -> bytearray:
    binary_bytes = bytearray()
    word = (
        ((instruction.dst_mode.value & 0b11) << 14)
        | ((instruction.dst_index.value & 0b111) << 11)
        | ((instruction.src_mode.value & 0b11) << 9)
        | ((instruction.src_index.value & 0b111) << 6)
        | (instruction.opcode.value & 0b111111)
    )
    binary_bytes.append((word >> 8) & 0xFF)
    binary_bytes.append(word & 0xFF)

    if need_imm(instruction.src_mode):
        binary_bytes += (instruction.src_imm & 0xFFFFFFFF).to_bytes(4, byteorder="big", signed=False)
    if need_imm(instruction.dst_mode):
        binary_bytes += (instruction.dst_imm & 0xFFFFFFFF).to_bytes(4, byteorder="big", signed=False)
    return binary_bytes


def to_bytes(instructions: list[Instruction]) -> bytearray:
    binary_bytes = bytearray()
    for instruction in instructions:
        binary_bytes += encode_instruction(instruction)
    return binary_bytes


def to_hex(instructions: list[Instruction]) -> str:
    binary_bytes = to_bytes(instructions)
    result = []
    i = 0
    while i < len(binary_bytes):
        addr = i
        instruction, i_new = decode_instruction(binary_bytes, i)
        chunk = binary_bytes[i:i_new]
        hex_word = chunk.hex().upper()
        asm = to_str(instruction)
        result.append(f"{addr:3} - {hex_word:20} - {asm}")
        i = i_new
    return "\n".join(result)


def decode_instruction(data: bytearray, i: int):
    word = (data[i] << 8) | data[i + 1]
    i += 2
    opcode = Opcode(word & 0b111111)
    src_index = Register((word >> 6) & 0b111)
    src_mode = AddrMode((word >> 9) & 0b11)
    dst_index = Register((word >> 11) & 0b111)
    dst_mode = AddrMode((word >> 14) & 0b11)
    src_imm = 0
    if need_imm(src_mode):
        src_imm = int.from_bytes(data[i : i + 4], byteorder="big", signed=True)
        i += 4
    dst_imm = 0
    if need_imm(dst_mode):
        dst_imm = int.from_bytes(data[i : i + 4], byteorder="big", signed=True)
        i += 4
    instruction = Instruction(opcode, src_mode, src_index, dst_mode, dst_index, src_imm, dst_imm)
    return instruction, i


def from_bytes(data: bytearray):
    i = 0
    instructions = []
    while i < len(data):
        instruction, i = decode_instruction(data, i)
        instructions.append(instruction)
    return instructions


def format_operand(mode, reg, imm) -> str:
    if mode == AddrMode.DIRECT:
        return str(reg)
    if mode == AddrMode.IMMEDIATE:
        return str(imm)
    if mode == AddrMode.INDIRECT:
        return f"[{reg}]"
    return f"[{reg}+{imm}]"


def to_str(instruction: Instruction) -> str:
    op = instruction.opcode
    if op == Opcode.HALT:
        return "HALT"
    if op in {Opcode.JMP, Opcode.BEQ, Opcode.BNE, Opcode.BGE, Opcode.BGT, Opcode.BLE, Opcode.BLT}:
        return f"{op} {instruction.dst_imm}"
    src = format_operand(instruction.src_mode, instruction.src_index, instruction.src_imm)
    dst = format_operand(instruction.dst_mode, instruction.dst_index, instruction.dst_imm)
    return f"{op} {src} {dst}"


def to_json(instructions: list[Instruction]) -> str:
    instructions_list = []
    for ind, instruction in enumerate(instructions):
        instructions_list.append(
            {
                "address": ind,
                "opcode": instruction.opcode.value,
                "src_mode": instruction.src_mode.value,
                "src_index": instruction.src_index.value,
                "src_imm": instruction.src_imm if need_imm(instruction.src_mode) else None,
                "dst_mode": instruction.dst_mode.value,
                "dst_index": instruction.dst_index.value,
                "dst_imm": instruction.dst_imm if need_imm(instruction.dst_mode) else None,
            }
        )
    return json.dumps(instructions_list, indent=2)
