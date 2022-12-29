import tkinter
from tkinter.font import Font as TkFont
# Yes, we do need idlelib since listening to insert and delete event of the
# Text widget needs some trick that I don't want to do again...
from idlelib.redirector import WidgetRedirector

from mccmdhl.command import TokenType, CommandTokenizer

class MCCommandHightlighter:
    ERROR_FORMAT = "{pos_begin}-{pos_end}: {message}"

    def __init__(self, text: tkinter.Text, error_var: tkinter.StringVar):
        self.text = text
        self.error_var = error_var # Error message will be updated to it
        self.root = self.text.tk
        self.text_redir = WidgetRedirector(self.text)
        self.orig_ins = self.text_redir.register("insert", self.on_text_insert)
        self.orig_del = self.text_redir.register("delete", self.on_text_delete)
        # create color font
        self.TOKEN2FORMAT = {
            TokenType.comment: {"foreground": "DeepSkyBlue"},
            TokenType.command: {"foreground": "green"},
            TokenType.option: {"foreground": "DarkOrange"},
            TokenType.number: {"foreground": "MediumSeaGreen"},
            TokenType.string: {"foreground": "SandyBrown"},
            TokenType.boolean: {"foreground": "MediumSeaGreen"},
            TokenType.selector: {"foreground": "DarkViolet"},
            TokenType.scoreboard: {
                "foreground": "DarkBlue",
                "font": TkFont(self.root, slant="italic")
            },
            TokenType.tag: {
                "foreground": "Blue",
                "font": TkFont(self.root, slant="italic")
            },
            TokenType.pos: {"foreground": "DarkTurquoise"},
            TokenType.error: {
                "foreground": "red", "underline": True
            }
        }
        # register color tags to Text widget
        for tok_type, color in self.TOKEN2FORMAT.items():
            self.text.tag_config(tok_type.name, **color)
    
    @staticmethod
    def lineno_from_index(index: str):
        # get lineno from Text widget index "X.X"
        return int(index.split(".")[0])

    def on_text_insert(self, index: str, chars: str, tags=None):
        index = self.text.index(index)
        self.orig_ins(index, chars, tags)
        # We update in group of lines
        line_count = chars.count("\n")
        line_start = self.lineno_from_index(index)
        line_end = line_start + line_count
        self.update_text(line_start, line_end)
    
    def on_text_delete(self, index1: str, index2=None):
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
        self.error_var.set("") # empty error
        for token in tokens:
            # Update error message if token is error
            if token.type is TokenType.error:
                # Update error message, if user's cursor is at this line
                # and if the message is empty (not set) yet
                if (
                    self.error_var.get() == "" and \
                    self.lineno_from_index(token.pos_begin) == cursor_line
                ):
                    msg = self.ERROR_FORMAT.format(
                        pos_begin = token.pos_begin,
                        pos_end = token.pos_end,
                        message = token.value
                    )
                    if len(msg) > 60:
                        msg = msg[:57] + " ..."
                    self.error_var.set(msg)
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

if __name__ == "__main__":
    tokenizer = CommandTokenizer("camerashake add @a ")
    print(tokenizer.get_tokens())
