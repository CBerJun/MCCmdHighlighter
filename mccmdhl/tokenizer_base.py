import contextlib

__all__ = ["Token", "Tokenizer"]

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

class Tokenizer:
    EOF = "\x04"

    def __init__(self, src: str, lineno_start = 1, col_start = 0) -> None:
        # lineno_start & col_start: position of the first char in `src`
        self.src = src
        self.current_lineno = lineno_start
        self.current_col = col_start - 1
        self.current_char = None
        self.tokens = [] # Result of tokenizing
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
