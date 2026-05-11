from src.translator.token import Token, TokenType
from src.util.exceptions import UnknownSymbolError


class LexicalAnalyzer:
    def __init__(self, text) -> None:
        self.text = text
        self.pos = 0
        self.current_char = text[0] if text else None
        self.line = 1
        self.column = 1

    def advance(self) -> None:
        if self.current_char == "\n":
            self.line += 1
            self.column = 0
        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]
        self.column += 1

    def peek(self):
        if self.pos + 1 < len(self.text):
            return self.text[self.pos + 1]
        return None

    def skip_whitespace(self) -> None:
        while self.current_char and self.current_char.isspace():
            self.advance()

    def skip_comment(self) -> None:
        while self.current_char and self.current_char != "\n":
            self.advance()
        if self.current_char == "\n":
            self.advance()

    def make_token(self, type_, value, line=None, column=None):
        return Token(
            type_, value, line if line is not None else self.line, column if column is not None else self.column
        )

    def parse_number(self):
        start_line = self.line
        start_column = self.column
        result = ""
        while self.current_char and self.current_char.isdigit():
            result += self.current_char
            self.advance()
        return self.make_token(TokenType.NUMBER, result, start_line, start_column)

    def parse_identifier(self):
        start_line = self.line
        start_column = self.column
        result = ""
        while self.current_char and (self.current_char.isalnum() or self.current_char == "_"):
            result += self.current_char
            self.advance()
        try:
            token_type = TokenType(result)
        except ValueError:
            token_type = TokenType.VARIABLE_NAME
        return self.make_token(token_type, result, start_line, start_column)

    def parse_string(self):
        start_line = self.line
        start_column = self.column
        self.advance()
        result = ""
        while self.current_char and self.current_char != '"':
            if self.current_char == "\\":
                next_char = self.peek()
                if next_char == "n":
                    result += "\n"
                    self.advance()
                    self.advance()
                    continue
            result += self.current_char
            self.advance()
        if self.current_char != '"':
            raise UnknownSymbolError("Unterminated string", self.make_token(None, result, start_line, start_column))
        self.advance()
        return self.make_token(TokenType.STRING, result, start_line, start_column)

    def two_symbols(self, token_type, value):
        start_line = self.line
        start_column = self.column
        self.advance()
        self.advance()
        return self.make_token(token_type, value, start_line, start_column)

    def get_next_token(self):
        while self.current_char:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char == "/" and self.peek() == "/":
                self.skip_comment()
                continue

            if self.current_char.isdigit():
                return self.parse_number()

            if self.current_char.isalpha() or self.current_char == "_":
                return self.parse_identifier()

            if self.current_char == '"':
                return self.parse_string()

            if self.current_char == "=" and self.peek() == "=":
                return self.two_symbols(TokenType.EQUALS, "==")

            if self.current_char == "!" and self.peek() == "=":
                return self.two_symbols(TokenType.NOT_EQUALS, "!=")

            if self.current_char == ">" and self.peek() == "=":
                return self.two_symbols(TokenType.GREATER_EQUAL, ">=")

            if self.current_char == "<" and self.peek() == "=":
                return self.two_symbols(TokenType.LESS_EQUAL, "<=")

            if self.current_char == "&" and self.peek() == "&":
                return self.two_symbols(TokenType.AND, "&&")

            if self.current_char == "|" and self.peek() == "|":
                return self.two_symbols(TokenType.OR, "||")

            char = self.current_char
            try:
                token_type = TokenType(char)
                self.advance()
                return self.make_token(token_type, char)
            except ValueError as err:
                raise UnknownSymbolError(char, self.make_token(None, char)) from err
        return self.make_token(TokenType.EOF, None, self.line, self.column)
