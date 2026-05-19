from src.isa.isa import AddrMode, Instruction, Opcode, Register
from src.translator.ast_nodes import (
    Ast,
    AstArrayReference,
    AstAssign,
    AstBinaryOperation,
    AstBlock,
    AstDeclaration,
    AstIf,
    AstNumber,
    AstPrint,
    AstRead,
    AstString,
    AstUnaryOperation,
    AstVariableReference,
    AstWhile,
    NodeVisitor,
)
from src.translator.symbol import SymbolTable, SymbolType
from src.translator.token import TokenType

arithmetic_map = {
    TokenType.PLUS: Opcode.ADD,
    TokenType.MINUS: Opcode.SUB,
    TokenType.MUL: Opcode.MUL,
    TokenType.DIV: Opcode.DIV,
    TokenType.MOD: Opcode.REM,
    TokenType.BIT_AND: Opcode.AND,
    TokenType.BIT_OR: Opcode.OR,
}

cmp_map = {
    TokenType.EQUALS: Opcode.BEQ,
    TokenType.NOT_EQUALS: Opcode.BNE,
    TokenType.GREATER: Opcode.BGT,
    TokenType.GREATER_EQUAL: Opcode.BGE,
    TokenType.LESS: Opcode.BLT,
    TokenType.LESS_EQUAL: Opcode.BLE,
}


class Label:
    def __init__(self, address: int = 0) -> None:
        self.address = address


class BranchStub:
    def __init__(self, label: Label, opcode: Opcode) -> None:
        self.label = label
        self.opcode = opcode


class CodeGenerator(NodeVisitor):
    def __init__(self, tree: Ast, symbol_table: SymbolTable) -> None:
        self.tree = tree
        self.symbol_table = symbol_table
        self.data: list[int] = []
        self.instructions: list[Instruction | Label | BranchStub] = []

    def push_r0(self) -> list[Instruction]:
        """Положить на стек: R7 <- R7 - 1, mem[R7] <- R0"""
        return [
            Instruction(Opcode.SUB, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R7, src_imm=1),
            Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.INDIRECT, Register.R7),
        ]

    def pop_to_register(self, reg: Register) -> list[Instruction]:
        """Снять со стека: reg <- mem[R7], R7 <- R7 + 1"""
        return [
            Instruction(Opcode.MOVE, AddrMode.INDIRECT, Register.R7, AddrMode.DIRECT, reg),
            Instruction(Opcode.ADD, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R7, src_imm=1),
        ]

    def link(self) -> list[Instruction]:
        address = 0
        for item in self.instructions:
            if isinstance(item, Label):
                item.address = address
                continue
            if isinstance(item, BranchStub):
                address += 6
                continue
            size = 2
            if item.src_mode in (AddrMode.IMMEDIATE, AddrMode.INDIRECT_OFFSET):
                size += 4
            if item.dst_mode in (AddrMode.IMMEDIATE, AddrMode.INDIRECT_OFFSET):
                size += 4
            address += size

        result: list[Instruction] = []
        for item in self.instructions:
            if isinstance(item, Label):
                continue
            if isinstance(item, BranchStub):
                result.append(
                    Instruction(
                        item.opcode,
                        AddrMode.DIRECT,
                        Register.R0,
                        AddrMode.IMMEDIATE,
                        Register.R0,
                        dst_imm=item.label.address,
                    )
                )
            else:
                result.append(item)
        return result

    def translate(self) -> tuple[list[Instruction], list[int]]:
        self.instructions.append(
            Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R7, src_imm=2047)
        )
        self.visit(self.tree)
        self.instructions.append(Instruction(Opcode.HALT, AddrMode.DIRECT, Register.R0, AddrMode.DIRECT, Register.R0))
        return self.link(), self.data

    def visit_ast_block(self, node: AstBlock) -> None:
        for stmt in node.children:
            self.visit(stmt)

    def visit_ast_declaration(self, node: AstDeclaration) -> None:
        symbol = self.symbol_table.lookup(node.name)
        if symbol is None:
            return
        if symbol.type_ == SymbolType.INT:
            symbol_address = len(self.data)
            self.data.append(0)
            symbol.address = symbol_address

            self.emit_expression(node.value)
            self.instructions += self.pop_to_register(Register.R0)

            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=symbol_address
                )
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.INDIRECT, Register.R1)
            )

        elif symbol.type_ == SymbolType.LONG:
            symbol_address = len(self.data)
            self.data += [0, 0]
            symbol.address = symbol_address

            self.emit_expression(node.value)
            self.instructions += self.pop_to_register(Register.R1)  # Low word
            self.instructions += self.pop_to_register(Register.R2)  # High word

            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=symbol_address
                )
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R2, AddrMode.INDIRECT, Register.R0)
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R1, AddrMode.INDIRECT_OFFSET, Register.R0, dst_imm=1)
            )
        elif symbol.type_ == SymbolType.STRING:
            self.emit_string_literal(node.value)
            symbol.address = node.value.address
        elif symbol.type_ == SymbolType.ARRAY:
            node.value.address = len(self.data)
            self.data += [0] * node.value.size
            symbol.address = node.value.address

    def visit_ast_assign(self, node: AstAssign) -> None:
        symbol = self.symbol_table.lookup(node.ref.name)
        if symbol is None:
            return

        if isinstance(node.ref, AstArrayReference):
            self.emit_expression(node.expression)
            self.emit_index_address(node.ref)
            self.instructions += self.pop_to_register(Register.R1)
            self.instructions += self.pop_to_register(Register.R0)
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.INDIRECT, Register.R1)
            )
        elif symbol.type_ == SymbolType.INT:
            self.emit_expression(node.expression)
            self.instructions += self.pop_to_register(Register.R0)
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=symbol.address
                )
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.INDIRECT, Register.R1)
            )
        elif symbol.type_ == SymbolType.LONG:
            self.emit_expression(node.expression)
            self.instructions += self.pop_to_register(Register.R1)  # Low word
            self.instructions += self.pop_to_register(Register.R2)  # High word
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=symbol.address
                )
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R2, AddrMode.INDIRECT, Register.R0)
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R1, AddrMode.INDIRECT_OFFSET, Register.R0, dst_imm=1)
            )
        elif symbol.type_ in (SymbolType.STRING, SymbolType.ARRAY):
            if isinstance(node.expression, AstVariableReference):
                src_sym = self.symbol_table.lookup(node.expression.name)
                if src_sym is not None:
                    symbol.address = src_sym.address
            elif isinstance(node.expression, AstString):
                self.emit_string_literal(node.expression)
                symbol.address = node.expression.address

    def visit_ast_if(self, node: AstIf) -> None:
        else_label = Label()
        end_label = Label()

        self.emit_expression(node.condition)
        self.instructions += self.pop_to_register(Register.R0)
        self.instructions.append(
            Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
        )
        self.instructions.append(BranchStub(else_label, Opcode.BEQ))
        self.visit(node.if_block)
        self.instructions.append(BranchStub(end_label, Opcode.JMP))
        self.instructions.append(else_label)
        if node.else_block is not None:
            self.visit(node.else_block)
        self.instructions.append(end_label)

    def visit_ast_while(self, node: AstWhile) -> None:
        while_label = Label()
        end_label = Label()

        self.instructions.append(while_label)
        self.emit_expression(node.condition)
        self.instructions += self.pop_to_register(Register.R0)
        self.instructions.append(
            Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
        )
        self.instructions.append(BranchStub(end_label, Opcode.BEQ))
        self.visit(node.body)
        self.instructions.append(BranchStub(while_label, Opcode.JMP))
        self.instructions.append(end_label)

    def visit_ast_print(self, node: AstPrint) -> None:
        if node.type_ == SymbolType.INT:
            self.emit_expression(node.value)
            self.instructions += self.pop_to_register(Register.R0)
            self.instructions.append(
                Instruction(
                    Opcode.OUT, AddrMode.DIRECT, Register.R0, AddrMode.IMMEDIATE, Register.R0, dst_imm=node.port
                )
            )
        else:
            if isinstance(node.value, AstString):
                self.emit_string_literal(node.value)
                self.instructions.append(
                    Instruction(
                        Opcode.MOVE,
                        AddrMode.IMMEDIATE,
                        Register.R0,
                        AddrMode.DIRECT,
                        Register.R0,
                        src_imm=node.value.address,
                    )
                )
            else:
                sym = self.symbol_table.lookup(node.value.name)
                self.instructions.append(
                    Instruction(
                        Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=sym.address
                    )
                )
            self.emit_print_cstr_loop(node.port)

    def visit_ast_read(self, node: AstRead) -> None:
        if isinstance(node.variable, AstArrayReference):
            self.emit_index_address(node.variable)
            self.instructions += self.pop_to_register(Register.R1)
        else:
            symbol = self.symbol_table.lookup(node.variable.name)
            if symbol is None:
                return
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=symbol.address
                )
            )

        if node.type_ == SymbolType.INT:
            self.instructions.append(
                Instruction(
                    Opcode.IN, AddrMode.IMMEDIATE, Register.R0, AddrMode.INDIRECT, Register.R1, src_imm=node.port
                )
            )
        else:
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R0)
            )
            self.emit_read_cstr_loop(node.port)

    def visit_ast_number(self, node: AstNumber) -> None:
        """Положить число на стек"""
        if node.type_ == SymbolType.LONG:
            high = (node.value >> 32) & 0xFFFFFFFF
            low = node.value & 0xFFFFFFFF
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=high)
            )
            self.instructions += self.push_r0()
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=low)
            )
            self.instructions += self.push_r0()
        else:
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=node.value
                )
            )
            self.instructions += self.push_r0()

    def visit_ast_variable_reference(self, node: AstVariableReference) -> None:
        """Загрузка значения переменной на стек"""
        symbol = self.symbol_table.lookup(node.name)
        if symbol is None:
            return
        if node.type_ == SymbolType.LONG and symbol.type_ == SymbolType.INT:
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=symbol.address
                )
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.INDIRECT, Register.R1, AddrMode.DIRECT, Register.R2)
            )

            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
            )
            self.instructions += self.push_r0()

            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()
            return

        if symbol.type_ == SymbolType.LONG:
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=symbol.address
                )
            )
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.INDIRECT, Register.R1, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.INDIRECT_OFFSET, Register.R1, AddrMode.DIRECT, Register.R0, src_imm=1)
            )
            self.instructions += self.push_r0()
            return

        if symbol.type_ in (SymbolType.STRING, SymbolType.ARRAY):
            self.instructions.append(
                Instruction(
                    Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=symbol.address
                )
            )
            self.instructions += self.push_r0()
            return
        self.instructions.append(
            Instruction(
                Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=symbol.address
            )
        )
        self.instructions.append(Instruction(Opcode.MOVE, AddrMode.INDIRECT, Register.R1, AddrMode.DIRECT, Register.R0))
        self.instructions += self.push_r0()
        return

    def visit_ast_array_reference(self, node: AstArrayReference) -> None:
        """Загрузка элемента массива: mem[Base + Index]"""
        self.emit_index_address(node)
        self.instructions += self.pop_to_register(Register.R1)
        self.instructions.append(Instruction(Opcode.MOVE, AddrMode.INDIRECT, Register.R1, AddrMode.DIRECT, Register.R0))
        self.instructions += self.push_r0()

    def visit_ast_binary_operation(self, node: AstBinaryOperation) -> None:
        op_token = TokenType(node.op)

        if op_token in (TokenType.AND, TokenType.OR):
            assert node.left is not None
            self.emit_expression(node.left)
            assert node.left.type_ is not None
            self.emit_normalize_logic(node.left.type_)

            assert node.right is not None
            self.emit_expression(node.right)
            assert node.right.type_ is not None
            self.emit_normalize_logic(node.right.type_)

            self.instructions += self.pop_to_register(Register.R2)  # Right
            self.instructions += self.pop_to_register(Register.R1)  # Left

            opcode = Opcode.AND if op_token == TokenType.AND else Opcode.OR
            self.instructions.append(Instruction(opcode, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R1))
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()

            if node.type_ == SymbolType.LONG:
                self.instructions += self.pop_to_register(Register.R0)
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.DIRECT, Register.R2)
                )
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
                )
                self.instructions += self.push_r0()
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R0)
                )
                self.instructions += self.push_r0()
            return

        if node.type_ == SymbolType.LONG and op_token not in cmp_map:
            self.emit_expression(node.left)
            self.emit_expression(node.right)

            self.instructions += self.pop_to_register(Register.R2)  # Right low
            self.instructions += self.pop_to_register(Register.R1)  # Right high
            self.instructions += self.pop_to_register(Register.R4)  # Left low
            self.instructions += self.pop_to_register(Register.R3)  # Left high

            if op_token == TokenType.PLUS:
                self.instructions.append(
                    Instruction(Opcode.ADD, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R4)
                )
                self.instructions.append(
                    Instruction(Opcode.ADC, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R3)
                )
            elif op_token == TokenType.MINUS:
                self.instructions.append(
                    Instruction(Opcode.NOT, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R2)
                )
                self.instructions.append(
                    Instruction(Opcode.NOT, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R1)
                )
                self.instructions.append(
                    Instruction(Opcode.ADD, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R2, src_imm=1)
                )
                self.instructions.append(
                    Instruction(Opcode.ADC, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=0)
                )
                self.instructions.append(
                    Instruction(Opcode.ADD, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R4)
                )
                self.instructions.append(
                    Instruction(Opcode.ADC, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R3)
                )
            elif op_token == TokenType.BIT_AND:
                self.instructions.append(
                    Instruction(Opcode.AND, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R4)
                )
                self.instructions.append(
                    Instruction(Opcode.AND, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R3)
                )
            elif op_token == TokenType.BIT_OR:
                self.instructions.append(
                    Instruction(Opcode.OR, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R4)
                )
                self.instructions.append(
                    Instruction(Opcode.OR, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R3)
                )

            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R3, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R4, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()
            return

        if op_token in cmp_map:
            true_label = Label()
            end_label = Label()
            branch_op = cmp_map[op_token]
            is_long_cmp = node.left.type_ == SymbolType.LONG or node.right.type_ == SymbolType.LONG

            self.emit_expression(node.left)
            self.emit_expression(node.right)

            if is_long_cmp:
                self.instructions += self.pop_to_register(Register.R2)  # Right Low
                self.instructions += self.pop_to_register(Register.R1)  # Right High
                self.instructions += self.pop_to_register(Register.R4)  # Left Low
                self.instructions += self.pop_to_register(Register.R3)  # Left High

                check_low_label = Label()
                self.instructions.append(
                    Instruction(Opcode.CMP, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R3)
                )
                self.instructions.append(BranchStub(check_low_label, Opcode.BEQ))
                self.instructions.append(BranchStub(true_label, branch_op))
                self.instructions.append(BranchStub(end_label, Opcode.JMP))

                self.instructions.append(check_low_label)
                self.instructions.append(
                    Instruction(Opcode.CMP, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R4)
                )
                self.instructions.append(BranchStub(true_label, branch_op))
            else:
                self.instructions += self.pop_to_register(Register.R2)
                self.instructions += self.pop_to_register(Register.R1)
                self.instructions.append(
                    Instruction(Opcode.CMP, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R1)
                )
                self.instructions.append(BranchStub(true_label, branch_op))

            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
            )
            self.instructions += self.push_r0()
            self.instructions.append(BranchStub(end_label, Opcode.JMP))

            self.instructions.append(true_label)
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=1)
            )
            self.instructions += self.push_r0()
            self.instructions.append(end_label)

            if node.type_ == SymbolType.LONG:
                self.instructions += self.pop_to_register(Register.R0)
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.DIRECT, Register.R2)
                )
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
                )
                self.instructions += self.push_r0()
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R0)
                )
                self.instructions += self.push_r0()
            return

        if op_token in arithmetic_map:
            opcode = arithmetic_map[op_token]
            self.emit_expression(node.left)
            self.emit_expression(node.right)
            self.instructions += self.pop_to_register(Register.R2)
            self.instructions += self.pop_to_register(Register.R1)
            self.instructions.append(Instruction(opcode, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R1))
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()

    def visit_ast_unary_operation(self, node: AstUnaryOperation) -> None:
        op_token = TokenType(node.op)
        self.emit_expression(node.expression)

        if op_token == TokenType.PLUS:
            return

        if op_token == TokenType.MINUS:
            self.instructions += self.pop_to_register(Register.R0)
            self.instructions.append(
                Instruction(Opcode.NEG, AddrMode.DIRECT, Register.R0, AddrMode.DIRECT, Register.R0)
            )
            self.instructions += self.push_r0()

        elif op_token == TokenType.NOT:
            true_label = Label()
            end_label = Label()
            self.instructions += self.pop_to_register(Register.R0)
            self.instructions.append(
                Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
            )
            self.instructions.append(BranchStub(true_label, Opcode.BEQ))

            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
            )
            self.instructions += self.push_r0()
            self.instructions.append(BranchStub(end_label, Opcode.JMP))

            self.instructions.append(true_label)
            self.instructions.append(
                Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=1)
            )
            self.instructions += self.push_r0()
            self.instructions.append(end_label)

            if node.type_ == SymbolType.LONG:
                self.instructions += self.pop_to_register(Register.R0)
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R0, AddrMode.DIRECT, Register.R2)
                )
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
                )
                self.instructions += self.push_r0()
                self.instructions.append(
                    Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R0)
                )
                self.instructions += self.push_r0()

    def emit_expression(self, node: Ast) -> None:
        self.visit(node)

    def emit_index_address(self, node: AstArrayReference) -> None:
        """
        Вычисляет байтовый адрес элемента массива и кладёт его на стек
        Адрес = Base + Index
        """
        symbol = self.symbol_table.lookup(node.name)
        base = symbol.address

        self.emit_expression(node.index)
        self.instructions += self.pop_to_register(Register.R2)  # R2 <- Index

        self.instructions.append(
            Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=base)
        )
        self.instructions.append(Instruction(Opcode.ADD, AddrMode.DIRECT, Register.R2, AddrMode.DIRECT, Register.R0))
        self.instructions += self.push_r0()

    def emit_string_literal(self, node: AstString) -> None:
        """Запись строкового литерала в память данных"""
        if node.address != -1:
            return
        node.address = len(self.data)
        for ch in node.value:
            self.data.append(ord(ch))
        self.data.append(0)

    def emit_print_cstr_loop(self, port: int) -> None:
        """
        Цикл вывода строки:
        Читаем символы из памяти по адресу R0 и выводим в порт, пока не встретим нуль-терминатор
        """
        loop_label = Label()
        end_label = Label()
        self.instructions.append(loop_label)
        self.instructions.append(Instruction(Opcode.MOVE, AddrMode.INDIRECT, Register.R0, AddrMode.DIRECT, Register.R1))
        self.instructions.append(
            Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=0)
        )
        self.instructions.append(BranchStub(end_label, Opcode.BEQ))
        self.instructions.append(
            Instruction(Opcode.OUT, AddrMode.DIRECT, Register.R1, AddrMode.IMMEDIATE, Register.R0, dst_imm=port)
        )
        self.instructions.append(
            Instruction(Opcode.ADD, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=1)
        )
        self.instructions.append(BranchStub(loop_label, Opcode.JMP))
        self.instructions.append(end_label)

    def emit_read_cstr_loop(self, port: int) -> None:
        """
        Цикл чтения строки:
        Читаем символы из порта в память по адресу R0, пока не встретим '\n', после чего заменяем '\n' на 0
        """
        loop_label = Label()
        end_label = Label()
        self.instructions.append(loop_label)
        self.instructions.append(
            Instruction(Opcode.IN, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=port)
        )
        self.instructions.append(
            Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R1, src_imm=ord("\n"))
        )
        self.instructions.append(BranchStub(end_label, Opcode.BEQ))
        self.instructions.append(Instruction(Opcode.MOVE, AddrMode.DIRECT, Register.R1, AddrMode.INDIRECT, Register.R0))
        self.instructions.append(
            Instruction(Opcode.ADD, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=1)
        )
        self.instructions.append(BranchStub(loop_label, Opcode.JMP))
        self.instructions.append(end_label)
        self.instructions.append(
            Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.INDIRECT, Register.R0, src_imm=0)
        )

    def emit_normalize_logic(self, source_type: SymbolType) -> None:
        true_label = Label()
        end_label = Label()

        if source_type == SymbolType.LONG:
            self.instructions += self.pop_to_register(Register.R1)  # Low
            self.instructions += self.pop_to_register(Register.R2)  # High
            self.instructions.append(Instruction(Opcode.OR, AddrMode.DIRECT, Register.R1, AddrMode.DIRECT, Register.R2))
            self.instructions.append(
                Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R2, src_imm=0)
            )
        else:
            self.instructions += self.pop_to_register(Register.R0)
            self.instructions.append(
                Instruction(Opcode.CMP, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
            )

        self.instructions.append(BranchStub(true_label, Opcode.BNE))

        self.instructions.append(
            Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=0)
        )
        self.instructions += self.push_r0()
        self.instructions.append(BranchStub(end_label, Opcode.JMP))

        self.instructions.append(true_label)
        self.instructions.append(
            Instruction(Opcode.MOVE, AddrMode.IMMEDIATE, Register.R0, AddrMode.DIRECT, Register.R0, src_imm=1)
        )
        self.instructions += self.push_r0()
        self.instructions.append(end_label)
