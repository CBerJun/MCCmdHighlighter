import enum
import contextlib

from .error import *

__all__ = ["Token", "TokenType", "Tokenizer", "WarningToken"]

class Token:
    def __init__(self, type, pos_begin, pos_end, value) -> None:
        self.type = type
        self.value = value
        self.pos_begin = pos_begin
        self.pos_end = pos_end
    
    def __repr__(self) -> str:
        return "<Token %s(%s) at %s-%s>" % (
            self.type.name, self.value, self.pos_begin, self.pos_end
        )

class TokenType(enum.Enum):
    comment = 1 # Comments
    command = 2 # Name of a command like "execute"
    option = 3 # Option of command like "players" after "scoreboard"
    number = 4 # Number or range like "1", "3.4" or "2.."
    string = 5 # String like `"abcd"` or `xyz` in `say xyz`
    boolean = 6 # Boolean "true" and "false"
    selector = 7 # The "@x" part of selector or a player name
    scoreboard = 8 # Scoreboard name
    tag = 9 # Tag name
    pos = 10 # Position like "~1" or "^" or "3.2"
    error = 11 # Unexpected
    warning = 12 # Understood, but probably wrong

class WarningToken(Token):
    def __init__(self, pos_begin, pos_end, type_: WarningType, **kwargs):
        self.type = type_
        self.warning_kwargs = kwargs
        super().__init__(TokenType.warning, pos_begin, pos_end, str(self))
    
    def __str__(self) -> str:
        return self.type.value.format(**self.warning_kwargs)

class Tokenizer:
    EOF = "\x04"

    def __init__(self, src: str, lineno_start = 1, col_start = 0) -> None:
        # lineno_start & col_start: position of the first char in `src`
        self.src = src
        self.current_lineno = lineno_start
        self.current_col = col_start - 1
        self.current_char = None
        self.tokens = [] # Result of tokenizing
        self.warnings = [] # Store warning `Token`s
        self.forward()
    
    @property
    def current_index(self):
        # index in the form of "X.X"
        return "%d.%d" % (self.current_lineno, self.current_col)
    
    @contextlib.contextmanager
    def create_token(self, type = None, value = None):
        # `type` and `value` can be completed later using `with ... as tok`
        tok = Token(type, None, None, value)
        tok.pos_begin = self.current_index
        yield tok
        tok.pos_end = self.current_index
        assert tok.type is not None
        self.tokens.append(tok)
    
    def warn_at(self, token: Token, type_: WarningType, **kwargs):
        # Create a warning at `token`
        self.warnings.append(WarningToken(
            token.pos_begin, token.pos_end, type_, **kwargs
        ))
    
    def forward(self):
        # Update position
        self.current_col += 1
        if self.current_char == "\n":
            self.current_lineno += 1
            self.current_col = 0
        # Move to next char
        if not self.src:
            self.current_char = self.EOF
            return
        self.current_char = self.src[0]
        self.src = self.src[1:]
    
    def peek(self, offset = 0):
        # get the next character
        try:
            return self.src[offset]
        except IndexError:
            return self.EOF
    
    def skip_spaces(self):
        while self.current_char == " ":
            self.forward()
    
    def skip_line(self):
        # skip the whole line
        res = ""
        while self.line_not_end():
            res += self.current_char
            self.forward()
        return res

    def line_not_end(self):
        return self.current_char != "\n" and self.current_char != self.EOF
    
    # Utils
    
    def raw_char(self, char: str):
        if self.current_char != char:
            raise Error(ErrorType.EXP_CHAR, char=char)
        self.forward()
    
    def char(self, char):
        self.raw_char(char)
        self.skip_spaces()
    
    def expect_char(self, char: str):
        try:
            self.char(char)
        except Error as err:
            with self.create_token(TokenType.error, err):
                pass
    
    def token_list(self, start: str, end: str, allow_empty=True):
        # Used as an generator, read a list of values started with `start`,
        # seperated with comma "," and ends with `end`
        # `allow_empty` specifies whether at least 1 element is required
        self.expect_char(start)
        self.skip_spaces()
        if self.current_char == end and (not allow_empty):
            with self.create_token(
                TokenType.error, Error(ErrorType.AT_LEAST_ONE_ELEMENT)
            ): self.char(end)
            return
        while self.current_char != end:
            yield
            try:
                self.char(",")
            except Error:
                break
            else: # disallow trailing comma
                if self.current_char == end:
                    with self.create_token(
                        TokenType.error, Error(ErrorType.TRAILING_COMMA)
                    ): pass
        self.expect_char(end)
