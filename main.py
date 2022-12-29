# The Minecraft command syntax highlighter
#   by CBerJun 2022.12

from mccmdhl.gui import MCCommandHightlighter

import tkinter
from tkinter.font import Font as TkFont

root = tkinter.Tk()
font = TkFont(root, size=14)
text = tkinter.Text(root, font=font)
text.grid(row=0, column=0)
error_var = tkinter.StringVar(root)
lab = tkinter.Label(root, font=font, textvariable=error_var, foreground="red")
lab.grid(row=1, column=0)
highlighter = MCCommandHightlighter(text, error_var)
highlighter.text_insert("1.0", """# Comment
ability @a[name=string,tag=tag,scores={score=1..2},y=~1] mute true
""")
root.mainloop()
