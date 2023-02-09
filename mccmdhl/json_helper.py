# Helper and highlighter of JSON
# This JSON does not allow the "null" constant, since it seems to be
# deprecated in Minecraft
# Besides, it can not handle multi-line JSON
from mccmdhl.tokenizer_base import *
from mccmdhl.error import *

__all__ = ["JSONTokenizer"]

class JSONTokenizer(Tokenizer):
    
    def get_tokens(self, expect = "any"):
        self.tokens = []
        self.skip_spaces()
        meth = getattr(self, "token_%s" % expect, None)
        if meth is None:
            raise ValueError("Invalid expect type")
        meth()
        try:
            self.char(self.EOF)
        except Error:
            with self.create_token(
                TokenType.error, Error(ErrorType.TOO_MUCH_JSON)
            ): self.skip_line()
        return self.tokens
    
    def expect(self, func, tok: Token):
        try:
            return func()
        except Error as err:
            tok.type = TokenType.error
            tok.value = err
            return None
    
    def token_any(self):
        # Any JSON object
        if self.try_token_constant():
            pass
        elif self.current_char.isdigit() or self.current_char == "-":
            with self.create_token(TokenType.number) as tok:
                self.expect(self.number, tok)
        elif self.current_char == '"':
            with self.create_token(TokenType.string) as tok:
                self.expect(self.string, tok)
        elif self.current_char == "[":
            self.token_array()
        elif self.current_char == "{":
            self.token_object()
        else:
            with self.create_token(TokenType.error, Error(ErrorType.EXP_JSON)):
                pass
    
    def token_array(self):
        # A JSON array
        for _ in self.token_list("[", "]", allow_empty=True):
            self.token_any()
    
    def token_object(self):
        # A JSON object {...}
        for _ in self.token_list("{", "}", allow_empty=True):
            with self.create_token(TokenType.option) as tok:
                self.expect(self.string, tok)
            self.expect_char(":")
            self.token_any()
    
    def number(self):
        # integer or floating number
        res = ""
        if self.current_char == "-":
            self.forward() # skip minus
            res += "-"
        if not self.current_char.isdigit():
            raise Error(ErrorType.EXP_NUMBER)
        while self.current_char.isdigit():
            res += self.current_char
            self.forward()
        if self.current_char == ".":
            self.forward() # skip "."
            res += "."
            if not self.current_char.isdigit():
                raise Error(ErrorType.INCOMPLETE_FLOAT)
            while self.current_char.isdigit():
                res += self.current_char
                self.forward()
        self.skip_spaces()
        return float(res)
    
    def string(self):
        # Quoted string
        self.char('"')
        while self.current_char != '"':
            if self.current_char == "\\" and self.peek() == '"':
                self.forward()
                self.forward()
                continue
            if not self.line_not_end():
                raise Error(ErrorType.UNCLOSED_STRING)
            ## TODO more escapes
            self.forward()
        self.forward() # skip '"'
        self.skip_spaces()
    
    def try_token_constant(self):
        # try to read true or false, return if success
        # NOTE constant "null" seems to be deprecated in Minecraft
        ## Peek the next word
        next_word = ""
        i = 0
        p = self.current_char
        while p.isalnum():
            next_word += p
            p = self.peek(i)
            i += 1
        if next_word in ("true", "false"):
            with self.create_token(TokenType.boolean):
                for _ in range(i):
                    self.forward()
            self.skip_spaces()
            return True
        return False

if __name__ == "__main__":
    tokenizer = JSONTokenizer('["x", 1, {"x": true}]')
    print(tokenizer.get_tokens())
