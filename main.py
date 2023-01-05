# The Minecraft command syntax highlighter
#   by CBerJun 2022.12

from mccmdhl import MCCommandHightlighter, Token

import tkinter
from tkinter.font import Font as TkFont

root = tkinter.Tk()
font = TkFont(root, size=14)
text = tkinter.Text(root, font=font)
text.grid(row=0, column=0)
error_var = tkinter.StringVar(root)
lab = tkinter.Label(
    root, font=font, textvariable=error_var,
    foreground="red", wraplength=750
)
lab.grid(row=1, column=0)

def errmsg_update(token: Token):
    if token is None:
        error_var.set("")
    else:
        msg = highlighter.errmsg_from_token(token)
        error_var.set(msg)

highlighter = MCCommandHightlighter(text, errmsg_update)
highlighter.text_insert("1.0", """# Comment
tp @a[name=string,tag=tag,scores={score=1..2},y=~1] 10 10 ~1 facing @p true
""")
root.mainloop()
