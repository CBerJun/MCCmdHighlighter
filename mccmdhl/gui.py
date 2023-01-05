import tkinter
from tkinter.font import Font as TkFont
# Yes, we do need idlelib since listening to insert and delete event of the
# Text widget needs some trick that I don't want to do again...
from idlelib.redirector import WidgetRedirector

from mccmdhl.command import TokenType, CommandTokenizer

__all__ = ["MCCommandHightlighter"]

class MCCommandHightlighter:
    ERROR_FORMAT = "{pos_begin}-{pos_end}: {message}"

    def __init__(self, text: tkinter.Text, set_error_msg):
        # set_error_msg:function; Whenever error message changes, this is
        # called with 1 Token as argument, which is the error token.
        # This argument might be None when no error is found in this line
        self.text = text
        self.BASIC_FONT = TkFont(font=text.cget("font"))
        self.text_redir = WidgetRedirector(self.text)
        self.orig_ins = self.text_redir.register("insert", self.text_insert)
        self.orig_del = self.text_redir.register("delete", self.text_delete)
        self.error_set = set_error_msg
        # create color font
        # NOTE:
        #  1. If you wish to change `TOKEN2FORMAT`, please call `update_font`;
        #  2. If you wish to override "font" attribute of these tokens, please
        #  use a copy of `self.BASIC_FONT` and then `config` it. `font_scb`
        #  below is a good example.
        ## add italic to scoreboard and tag
        font_scb = self.BASIC_FONT.copy()
        font_scb.config(slant="italic")
        font_tag = font_scb.copy()
        ## define font
        self.TOKEN2FORMAT = {
            TokenType.comment: {"foreground": "DeepSkyBlue"},
            TokenType.command: {"foreground": "Green"},
            TokenType.option: {"foreground": "DarkOrange"},
            TokenType.number: {"foreground": "LimeGreen"},
            TokenType.string: {"foreground": "DimGray"},
            TokenType.boolean: {"foreground": "SeaGreen"},
            TokenType.selector: {"foreground": "DarkViolet"},
            TokenType.scoreboard: {
                "foreground": "DarkBlue", "font": font_scb
            },
            TokenType.tag: {
                "foreground": "Blue", "font": font_tag
            },
            TokenType.pos: {"foreground": "DarkTurquoise"},
            TokenType.error: {
                "foreground": "Red", "underline": True
            }
        }
        self.update_font()
    
    @staticmethod
    def lineno_from_index(index: str):
        # get lineno from Text widget index "X.X"
        return int(index.split(".")[0])
    
    def update_font(self):
        # register color tags to Text widget
        for tok_type, color in self.TOKEN2FORMAT.items():
            self.text.tag_config(tok_type.name, **color)
    
    def errmsg_from_token(self, token):
        # get error message from token
        assert token.type is TokenType.error
        return self.ERROR_FORMAT.format(
            pos_begin = token.pos_begin,
            pos_end = token.pos_end,
            message = str(token.value)
        )

    def text_insert(self, index: str, chars: str, tags=None):
        index = self.text.index(index)
        self.orig_ins(index, chars, tags)
        # We update in group of lines
        line_count = chars.count("\n")
        line_start = self.lineno_from_index(index)
        line_end = line_start + line_count
        self.update_text(line_start, line_end)
    
    def text_delete(self, index1: str, index2=None):
        index1 = self.text.index(index1)
        if index2 is not None:
            index2_ = self.text.index(index2)
        self.orig_del(index1, index2)
        # We update in group of lines
        line_start = self.lineno_from_index(index1)
        if index2 is None:
            line_end = line_start
        else:
            line_end = self.lineno_from_index(index2_)
        self.update_text(line_start, line_end)
    
    def update_text(self, line_start: int, line_end: int):
        # Recolorize the text from `line_start` to `line_end`
        ## get tokens
        index1, index2 = "%s.0" % line_start, "%s.end" % line_end
        src = self.text.get(index1, index2)
        tokenizer = CommandTokenizer(src, line_start, 0)
        tokens = tokenizer.get_tokens()
        ## remove old
        for tok_type in self.TOKEN2FORMAT:
            self.text.tag_remove(tok_type.name, index1, index2)
        ## update
        cursor_line = self.lineno_from_index(self.text.index("insert"))
        error_tok = None
        for token in tokens:
            # Update error message if token is error
            if token.type is TokenType.error:
                # Update error message, if user's cursor is at this line
                if self.lineno_from_index(token.pos_begin) == cursor_line and \
                    error_tok == None:
                    error_tok = token
            # Add tag
            if token.type is TokenType.error and \
                token.pos_begin == token.pos_end:
                # Some of the errors' length is 0 (e.g. from 1.20 to
                # 1.20), but we still want to show them. So give these errors
                # one more column
                end_lineno, end_col = token.pos_end.split(".")
                end_col = str(int(end_col) + 1)
                pos_end = "%s.%s" % (end_lineno, end_col)
            else:
                pos_end = token.pos_end
            self.text.tag_add(token.type.name, token.pos_begin, pos_end)
        self.error_set(error_tok)

if __name__ == "__main__":
    tokenizer = CommandTokenizer("camerashake add @a ")
    print(tokenizer.get_tokens())
