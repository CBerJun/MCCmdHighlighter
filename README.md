# Minecraft Command Syntax Highlighter
This is a syntax highlighter for Minecraft Bedrock Edition commands.

## How do I use it?
You can run `main.py` with Python and a window will appear where you can type commands and see the commands colored.
No thirdparty package is required.
Tags and scoreboards are marked in *italic form*.
Options in command, selector, namespaced identifier and number all have different colors.
Also, error tokens are marked red and underlined.
All errors come with a message that tells you what's wrong!

By calling `update_version` method for `MCCommandHighlighter`, you can specify the version of the system, using a tuple like `(1, 19, 80)`.
The minimum version supported is `(1, 19, 0)`

## Notice
This project supports command in Minecraft Bedrock Edition, from 1.19.0 to 1.20.0.
Since command engine of Minecraft Bedrock Edition is not open-source, the parse result this program gives **may differ from the original command system of Minecraft in some aspects**.
Besides, not all commands are supported.
In specific, `/gametest` and `/scriptevent` are not supported yet.
Each command is supported in `mccmdhl.command.CommandTokenizer.c_<Name>`.

