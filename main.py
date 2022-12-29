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
MCCommandHightlighter(text, error_var)
root.mainloop()

'''
# This is a comment
camerashake add @e[name="xxx",tag=xyz,scores={sc=-1}] 2.3 10 positional
ability @e[type=minecraft:xxx,tag=xyz,scores={sc=!-2..5}] worldbuilder false
clear CBerJun minecraft:some_item 0 10
'''
