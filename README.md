# Minecraft Command Syntax Highlighter
This is a tokenizer & parser for Minecraft commands (on Bedrock Edition).
A simple colorizer is also included.

## How do I use it?
You can run `main.py` and just type in commands into the GUI.
No thirdparty packages is required. You should see the commands colorized!
Tags and scoreboards are marked in *italic form*.
Options in command, selector, namespaced id and numbers all have different colors.
Also, errors are marked red and underlined.
All errors have a message!

## Notice
This project is still in develop and **not all the commands are supported**.
Each command is supported in `mccmdhl.command.CommandTokenizer.c_<Name>`.

## Troubleshooting
Your Python may tell you that `idlelib` is not installed.
This package is installed with regular Python installation.
However, if you choose not to `Install IDLE` when installing Python
or you are on a special platform (e.g. Android with simulator of Linux),
this package might not be installed. For the former situation, just
install it (`pip install idlelib`). For the later one, your installation
might not support `tkinter`, please consider changing a platform.
