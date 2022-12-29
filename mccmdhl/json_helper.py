# Helper and highlighter of JSON
from mccmdhl.tokenizer_base import *

class _JSONSyntaxError(Exception):
    pass

class JSONTokenizer(Tokenizer):
    
    def get_tokens(self, expect = "any"):
        self.tokens = []
        self.skip_spaces()
        meth = getattr(self, "token_%s" % expect, None)
        if meth is None:
            raise ValueError("Invalid expect type")
        meth()
        return self.tokens
    
    def expect(self, func, tok: Token):
        try:
            return func()
        except _JSONSyntaxError as err:
            tok.type = TokenType.error
            tok.value = str(err)
            return None
    
    def expect_char(self, char: str):
        try:
            self.char(char)
        except _JSONSyntaxError as err:
            with self.create_token(TokenType.error, str(err)):
                pass
    
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
            with self.create_token(TokenType.error, "Expecting a JSON object"):
                pass
    
    def token_array(self):
        # A JSON array
        self.expect_char("[")
        while self.current_char != "]":
            self.token_any()
            try:
                self.char(",")
            except _JSONSyntaxError:
                break
            else: # JSON does not allow trailing comma
                continue
        self.expect_char("]")
    
    def token_object(self):
        # A JSON object {...}
        self.expect_char("{")
        while self.current_char != "}":
            with self.create_token(TokenType.option) as tok:
                self.expect(self.string, tok)
            self.expect_char(":")
            self.token_any()
            try:
                self.char(",")
            except _JSONSyntaxError:
                break
            else: # JSON does not allow trailing comma
                continue
        self.expect_char("}")
    
    def char(self, char):
        if self.current_char != char:
            raise _JSONSyntaxError("Expecting %r" % char)
        self.forward() # skip char
        self.skip_spaces()
    
    def number(self):
        # integer or floating number
        res = ""
        if self.current_char == "-":
            self.forward() # skip minus
            res += "-"
        if not self.current_char.isdigit():
            raise _JSONSyntaxError("Expecting a number")
        while self.current_char.isdigit():
            res += self.current_char
            self.forward()
        if self.current_char == ".":
            self.forward() # skip "."
            res += "."
            if not self.current_char.isdigit():
                raise _JSONSyntaxError("Incomplete floating number")
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
            if self.current_char == self.EOF:
                raise _JSONSyntaxError("Unclosed string")
            ## TODO more escapes
            self.forward()
        self.forward() # skip '"'
        self.skip_spaces()
    
    def try_token_constant(self):
        # try to read true, false or null, return if success
        for const in ("true", "false", "null"):
            chars = [self.current_char]
            for i in range(len(const) - 1):
                chars.append(self.peek(i))
            if "".join(chars) == const:
                with self.create_token(TokenType.boolean):
                    for _ in range(len(const)):
                        self.forward()
                self.skip_spaces()
                return True
        return False

if __name__ == "__main__":
    tokenizer = JSONTokenizer('["x", 1, {"x": true}]')
    print(tokenizer.get_tokens())
