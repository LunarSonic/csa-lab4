import json
import os
import re
import sys

from src.isa.isa import to_bytes, to_hex, to_json
from src.translator.ast_printer import AstPrinter
from src.translator.code_generator import CodeGenerator
from src.translator.lexical_analyzer import LexicalAnalyzer
from src.translator.parser import Parser
from src.translator.semantic_analyzer import SemanticAnalyzer
from src.util.exceptions import CompileError


def compile_source(text: str):
    lexer = LexicalAnalyzer(text)
    parser = Parser(lexer)
    tree = parser.parse_program()

    semantic_analyzer = SemanticAnalyzer()
    symbol_table, _ = semantic_analyzer.analyze(tree)

    print("AST:")
    printer = AstPrinter()
    printer.print(tree)
    print("-" * 30)

    semantic_analyzer = SemanticAnalyzer()
    symbol_table, _ = semantic_analyzer.analyze(tree)
    code_generator = CodeGenerator(tree, symbol_table)
    instructions, data = code_generator.translate()
    return instructions, data


def main(source_path: str, target_code: str, target_data: str) -> None:
    with open(source_path, encoding="utf-8") as f:
        src_content = f.read()

    src_content = re.sub(r"//.*", "", src_content)
    try:
        instructions, data = compile_source(src_content)
        os.makedirs(os.path.dirname(os.path.abspath(target_code)) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(target_data)) or ".", exist_ok=True)

        if target_code.endswith(".bin"):
            binary_instructions = to_bytes(instructions)
            with open(target_code, "wb") as f:
                f.write(binary_instructions)

            binary_data = bytearray()
            for val in data:
                binary_data += val.to_bytes(4, byteorder="big", signed=True)
            with open(target_data, "wb") as f:
                f.write(binary_data)

            with open(target_code + ".hex", "w") as f:
                f.write(to_hex(instructions))
            with open(target_data + ".hex", "w") as f:
                f.write("\n".join([f"{val:08X}" for val in data]))
        else:
            with open(target_code, "w") as f:
                f.write(to_json(instructions))
            with open(target_data, "w") as f:
                f.write(json.dumps(data, indent=2))
    except CompileError as e:
        print(f"Error: {e}")
        sys.exit(1)

    binary_code = to_bytes(instructions)
    print(f"Lines of code: {len(src_content.splitlines())}")
    print(f"Code instructions: {len(instructions)}")
    print(f"Code size (bytes): {len(binary_code)}")
    print(f"Data words (32-bit): {len(data)}")
    print(f"Data size (bytes): {len(data) * 4}")
    print(f"Total size (bytes): {len(binary_code) + len(data) * 4}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("You should write: translator.py <input_source> <target_instructions> <target_data>. Try again!")
        sys.exit(1)
    _, source_path, target_instr, target_data = sys.argv
    main(source_path, target_instr, target_data)
