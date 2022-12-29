# This is Minecraft's official one written in Java for Java Edition:
#   https://github.com/Mojang/brigadier/
# Might help anyway.

from mccmdhl.tokenizer_base import *
from mccmdhl.json_helper import JSONTokenizer

class _CommandSyntaxError(Exception):
    pass

class CommandTokenizer(Tokenizer):

    def get_tokens(self):
        # get all the tokens
        self.tokens = []
        self.file()
        return self.tokens
    
    def file(self):
        # the whole mcfunction file
        while self.current_char != self.EOF:
            self.line()
    
    def line(self):
        # one line in mcfunction file
        # could be comment, command, or empty line
        self.skip_spaces()
        if self.current_char == "#":
            self.token_comment()
        elif self.current_char == "\n":
            self.forward()
        else:
            self.token_command()
    
    def command_not_end(self):
        return self.current_char != "\n" and self.current_char != self.EOF
    
    def next_is_number(self):
        return self.current_char == "-" or self.current_char.isdigit()
    
    def next_is_word(self):
        return (
            "0" <= self.current_char <= "9" or
            "a" <= self.current_char <= "z" or
            "A" <= self.current_char <= "Z" or
            self.current_char in "_-.+"
        )
    
    def next_is_pos(self):
        return (
            self.next_is_number() or
            self.current_char == "~" or
            self.current_char == "^"
        )
    
    def next_is_rotation(self):
        return self.next_is_number() or self.current_char == "~"

    def skip_line(self):
        # skip the whole line
        res = ""
        while self.command_not_end():
            res += self.current_char
            self.forward()
        self.forward() # skip "\n"
        res = res.rstrip()
        return res
    
    def expect(self, func, token: Token):
        try:
            return func()
        except _CommandSyntaxError as err:
            token.type = TokenType.error
            token.value = str(err)
            return None
    
    def expect_char(self, char: str):
        try:
            self.char(char)
        except _CommandSyntaxError as err:
            with self.create_token(TokenType.error, str(err)):
                pass
    
    def check_number(self, number: int, tok: Token, min: int, max: int = None):
        # check the range of number
        if number is None:
            return
        if max is None:
            test = number >= min
        else:
            test = min <= number <= max
        if not test:
            tok.type = TokenType.error
            tok.value = "Number not in range: [%d, %s]" % (min, max)

    # The following methods read different kinds of arguments.
    # Spaces are allowed to seperate the arguments. Therefore, they all call
    # the `skip_spaces` method when finish reading

    def word(self):
        # just like com.mojang.brigadier.StringReader.readUnquotedString
        res = ""
        while self.next_is_word():
            res += self.current_char
            self.forward()
        if not res:
            raise _CommandSyntaxError("Expecting a word")
        self.skip_spaces()
        return res
    
    def quoted_string(self):
        # a quoted string "xxx"
        self.char('"') # skip '"'
        while self.current_char != '"':
            if self.current_char == "\\" and self.peek() == '"':
                self.forward() # skip "\\"
                self.forward() # skip '"'
                continue
            if self.current_char == self.EOF:
                raise _CommandSyntaxError("Unclosed string")
            self.forward()
        self.forward() # skip last '"'
        self.skip_spaces()
    
    def string(self):
        # word or quoted string
        if self.current_char == '"':
            self.quoted_string()
        else:
            self.word()
    
    def namespaced_id(self):
        # This name is given from MinecraftWiki,
        # representing item id, block id, etc.
        # See https://wiki.biligame.com/mc/命名空间ID
        res = ""
        while (
            "0" <= self.current_char <= "9" or
            "a" <= self.current_char <= "z" or
            self.current_char in "_-.:"
        ):
            res += self.current_char
            self.forward()
        if not res:
            raise _CommandSyntaxError("Expecting an namespaced identifier")
        if res.count(":") > 1:
            raise _CommandSyntaxError("More than 1 colon in namespaced id")
        self.skip_spaces()
        return res
    
    def integer(self):
        # read an integer
        res = ""
        if self.current_char == "-":
            self.forward() # skip minus
            res += "-"
        if not self.current_char.isdigit():
            raise _CommandSyntaxError("Expecting an integer")
        while self.current_char.isdigit():
            res += self.current_char
            self.forward()
        self.skip_spaces()
        num = int(res)
        if not -2**31 <= num <= 2**31-1:
            raise _CommandSyntaxError("Integer overflow")
        return num
    
    def number(self):
        # integer or floating number
        res = ""
        if self.current_char == "-":
            self.forward() # skip minus
            res += "-"
        if not self.current_char.isdigit():
            raise _CommandSyntaxError("Expecting a number")
        while self.current_char.isdigit():
            res += self.current_char
            self.forward()
        if self.current_char == ".":
            self.forward() # skip "."
            res += "."
            if not self.current_char.isdigit():
                raise _CommandSyntaxError("Incomplete floating number")
            while self.current_char.isdigit():
                res += self.current_char
                self.forward()
        self.skip_spaces()
        return float(res)
    
    def number_range(self):
        # a number range like "2", "-1..", "3..5"
        start, end = None, None
        if self.next_is_number():
            start = self.integer()
        if self.current_char == ".":
            self.forward() # skip one "."
            self.char(".")
            if self.next_is_number():
                end = self.integer()
        if start is None and end is None:
            raise _CommandSyntaxError("Expecting a number range")
        if (start is not None) and (end is not None) and (start > end):
            raise _CommandSyntaxError("Number range start larger than end")

    def boolean(self):
        word = self.word()
        if word is not None and word not in ("true", "false"):
            raise _CommandSyntaxError("Expecting a boolean value")
    
    def char(self, char: str):
        # a character
        if self.current_char != char:
            raise _CommandSyntaxError("Expecting %r" % char)
        self.forward()
        self.skip_spaces()
    
    def pos(self):
        # one dimension of postion
        # e.g. "-3.1", "~2", "^"
        if self.current_char == "~":
            self.forward()
            res = "relative"
        elif self.current_char == "^":
            self.forward()
            res = "local"
        else:
            res = "absolute"
        if res in ("relative", "local"):
            # number is not a must when "~" or "^" exist
            if self.next_is_number():
                self.number()
        else: # number is a must when using absolute pos
            if not self.next_is_number():
                raise _CommandSyntaxError("Expecting a position")
            self.number()
        self.skip_spaces()
        return res
    
    # The following method create tokens

    def token_command(self):
        # one command
        ## read command name
        with self.create_token(TokenType.command) as tok:
            command = self.expect(self.word, tok)
            if command is None:
                tok.type = TokenType.error
                tok.value = "Expecting a command"
                self.skip_line()
                return
            # handle alias
            ALIAS = {
                "?": "help", "connect": "wsserver", "daylock": "alwaysday",
                "msg": "tell", "w": "tell"
            }
            command = ALIAS.get(command, command)
            command_method = getattr(self, "c_%s" % command, None)
            if command_method is None:
                tok.type = TokenType.error
                tok.value = "Unknown command: %r" % command
                self.skip_line()
                return
            tok.value = command
        ## read argument of command
        command_method()
        ## line should end here
        if self.command_not_end():
            with self.create_token(TokenType.error, "Expecting a new line"):
                self.skip_line()

    def token_comment(self):
        # create token for comment
        with self.create_token(TokenType.comment):
            self.forward() # skip "#"
            self.skip_line()

    def token_target(self):
        # selector or player name
        def _handle_scores():
            # just to decrease indentation :)
            self.expect_char("{")
            while True:
                self.skip_spaces() # allow spaces before arguments
                with self.create_token(TokenType.scoreboard) as tok:
                    # NOTE scores allow quoted string as key!!!
                    # e.g. @a[scores={"xxx"=1}]
                    self.expect(self.string, tok)
                    if self.current_char == self.EOF:
                        tok.type = TokenType.error
                        tok.value = 'Unclosed "{"'
                        return
                self.expect_char("=")
                if self.current_char == "!":
                    self.forward()
                with self.create_token(TokenType.number) as tok:
                    self.expect(self.number_range, tok)
                try:
                    self.char(",")
                except _CommandSyntaxError:
                    break # if couldn't find char ","
                else:
                    # since MC does not allow trailing comma,
                    # "," means there must be more arguments
                    continue
            self.forward() # skip "}"
    
        def _handle_hasitem():
            # just to decrease indentation :)
            self.expect_char("{")
            args = []
            while True:
                self.skip_spaces() # allow spaces before arguments
                with self.create_token(TokenType.option) as tok:
                    arg = self.expect(self.word, tok)
                    if self.current_char == self.EOF:
                        tok.type = TokenType.error
                        tok.value = 'Unclosed "{"'
                        return
                    if arg is None:
                        self.skip_line()
                        return
                    if arg not in (
                        "item", "data", "quantity", "location", "slot"
                    ):
                        tok.type = TokenType.error
                        tok.value = "Invalid hasitem argument"
                        return
                args.append(arg)
                self.expect_char("=")
                if arg == "item":
                    self.token_namespaced_id()
                elif arg == "data":
                    with self.create_token(TokenType.number) as tok:
                        value = self.expect(self.integer, tok)
                        self.check_number(value, tok, 0, 2**15-1)
                elif arg in ("quantity", "slot"):
                    if self.current_char == "!":
                        self.forward()
                    with self.create_token(TokenType.number) as tok:
                        self.expect(self.number_range, tok)
                elif arg == "location":
                    with self.create_token(TokenType.string) as tok:
                        self.expect(self.word, tok)
                try:
                    self.char(",")
                except _CommandSyntaxError:
                    break # if couldn't find char ","
                else: # to disallow trailing comma
                    continue
            self.expect_char("}")
            if "item" not in args:
                with self.create_token(
                    TokenType.error, '"item" argument is required for hasitem'
                ): pass
        if self.current_char != "@":
            # a name
            with self.create_token(TokenType.selector) as tok:
                self.expect(self.string, tok)
        else:
            # a selector
            with self.create_token(TokenType.selector) as tok:
                self.forward() # skip "@"
                var = self.expect(self.word, tok) # xxx in @xxx
                if (var is not None) and var not in (
                    "a", "e", "r", "s", "p", "c", "v", "initiator"
                ):
                    tok.type = TokenType.error
                    tok.value = "Invalid selector type: %r" % var
            if self.current_char == "[":
                self.forward() # skip "["
                while True:
                    self.skip_spaces() # allow spaces before arguments
                    with self.create_token(TokenType.option) as tok:
                        arg = self.expect(self.word, tok)
                        if arg is None:
                            self.skip_line()
                            return
                        if self.current_char == self.EOF:
                            tok.type = TokenType.error
                            tok.value = 'Unclosed "["'
                            return
                        if arg not in (
                            "x", "y", "z", "dx", "dy", "dz", "r", "rm",
                            "scores", "tag", "name", "type", "family", "rx",
                            "rxm", "ry", "rym", "hasitem", "l", "lm", "m", "c"
                        ):
                            self.skip_line()
                            # we don't know what should be after an unknown arg,
                            # so we skip the remaining line
                            tok.type = TokenType.error
                            tok.value = "Invalid selector argument: %r" % arg
                            return
                    self.expect_char("=")
                    if arg in (
                        "dx", "dy", "dz", "r", "rm",
                        "rx", "rxm", "ry", "rym"
                    ):
                        with self.create_token(TokenType.number) as tok:
                            self.expect(self.number, tok)
                    elif arg in ("l", "lm", "c"):
                        with self.create_token(TokenType.number) as tok:
                            self.expect(self.integer, tok)
                    elif arg in ("name", "family"):
                        if self.current_char == "!":
                            self.forward() # skip "!" if exists
                        self.token_string()
                    elif arg == "type":
                        if self.current_char == "!":
                            self.forward()
                        self.token_namespaced_id()
                    elif arg in ("x", "y", "z"):
                        with self.create_token(TokenType.pos) as tok:
                            kind = self.expect(self.pos, tok)
                            if kind == "local":
                                tok.type = TokenType.error
                                tok.value = ("^ pos can not be used for "
                                "selector argument 'x', 'y' and 'z'")
                    elif arg == "scores":
                        _handle_scores()
                    elif arg == "tag":
                        if self.current_char == "!":
                            self.forward() # skip "!" if exists
                        # NOTE tag accepts empty argument like "@a[tag=]"
                        if self.next_is_word() or self.current_char == '"':
                            with self.create_token(TokenType.tag) as tok:
                                self.expect(self.string, tok)
                    elif arg == "hasitem":
                        _handle_hasitem()
                    elif arg == "m":
                        self.token_gamemode_option()
                    try:
                        self.char(",")
                    except _CommandSyntaxError:
                        break # if couldn't find char ","
                    else:
                        continue # to disallow trailing comma
                self.expect_char("]")
        self.skip_spaces()
    
    def token_options(self, *options):
        # choose between `options`
        with self.create_token(TokenType.option) as tok:
            option = self.expect(self.word, tok)
            if option is not None and option not in options:
                tok.type = TokenType.error
                tok.value = "Invalid option: %r" % option
                return None
        return option
    
    def token_json(self, expect = "any"):
        # a JSON object
        # NOTE this would consump all the chars left in current line
        start_lineno, start_col = self.current_lineno, self.current_col
        json = self.skip_line()
        tokens = JSONTokenizer(json, start_lineno, start_col).get_tokens(
            expect = expect
        )
        self.tokens.extend(tokens)
    
    def token_blockstate(self):
        # blockstate like ["anchor": "north"]
        # only boolean, string, integer is allowed as value
        self.expect_char("[")
        while True:
            self.skip_spaces() # allow spaces before arguments
            with self.create_token(TokenType.option) as tok:
                self.expect(self.quoted_string, tok)
            self.expect_char(":")
            if self.current_char == '"':
                with self.create_token(TokenType.string) as tok:
                    self.expect(self.quoted_string, tok)
            elif self.next_is_number():
                with self.create_token(TokenType.number) as tok:
                    self.expect(self.integer, tok)
            else: # try boolean
                with self.create_token() as tok:
                    word = self.expect(self.word, tok)
                    if word in ("true", "false"):
                        tok.type = TokenType.boolean
                    else:
                        tok.type = TokenType.error
                        tok.value = "Expecting boolean, integer or string"
            try:
                self.char(",")
            except _CommandSyntaxError:
                break
            else:
                continue
        self.expect_char("]")

    def token_bs_or_data(self):
        # blockstate or block data (integer)
        if self.next_is_number(): # data value
            with self.create_token(TokenType.number) as tok:
                data = self.expect(self.integer, tok)
            self.check_number(data, tok, -1, 32767)
        elif self.current_char == "[": # block state
            self.token_blockstate()
        else:
            with self.create_token(
                TokenType.error, "Expecting block state or data value"
            ): self.skip_line()
    
    def token_rotation(self):
        # rotation like `90 ~-90`
        with self.create_token(TokenType.pos) as tok:
            if self.current_char == "~":
                self.forward()
            yaw = self.number()
            self.check_number(yaw, tok, -180, 180)
        with self.create_token(TokenType.pos) as tok:
            if self.current_char == "~":
                self.forward()
            pitch = self.number()
            self.check_number(pitch, tok, -90, 90)
    
    def token_full_pos(self, dimension = 3):
        # a full_pos consists of `dimension` `pos`es
        kinds = []
        for _ in range(dimension):
            with self.create_token(TokenType.pos) as tok:
                kinds.append(self.expect(self.pos, tok))
            if "relative" in kinds and "local" in kinds:
                tok.type = TokenType.error
                tok.value = "~ and ^ can not be used together"
    
    def token_namespaced_id(self):
        with self.create_token(TokenType.string) as tok:
            self.expect(self.namespaced_id, tok)
    
    def token_string(self):
        with self.create_token(TokenType.string) as tok:
            self.expect(self.string, tok)
    
    def token_scoreboard(self):
        with self.create_token(TokenType.scoreboard) as tok:
            self.expect(self.string, tok)
    
    def token_any_integer(self):
        with self.create_token(TokenType.number) as tok:
            self.expect(self.integer, tok)
    
    def token_skip_line(self, error = "Expecting a message"):
        with self.create_token(TokenType.string) as tok:
            path = self.skip_line()
            if not path:
                tok.type = TokenType.error
                tok.value = error
    
    # Following are the definitions of commands

    def c_help(self):
        with self.create_token() as tok:
            if self.next_is_number():
                tok.type = TokenType.number
                self.expect(self.integer, tok)
            else:
                tok.type = TokenType.string
                self.expect(self.word, tok)
    
    def c_ability(self):
        self.token_target()
        if self.command_not_end():
            self.token_options("worldbuilder", "mayfly", "mute")
            with self.create_token(TokenType.boolean) as tok:
                self.expect(self.boolean, tok)
    
    def c_alwaysday(self):
        if self.command_not_end():
            with self.create_token(TokenType.boolean) as tok:
                self.expect(self.boolean, tok)
    
    def c_camerashake(self):
        mode = self.token_options("add", "stop")
        if mode == "add":
            self.token_target()
            if self.command_not_end():
                with self.create_token(TokenType.number) as tok:
                    intensity = self.expect(self.number, tok)
                    self.check_number(intensity, tok, 0, 4)
                if self.command_not_end():
                    with self.create_token(TokenType.number) as tok:
                        self.expect(self.number, tok)
                    if self.command_not_end():
                        self.token_options("positional", "rotational")
        elif mode == "stop":
            if self.command_not_end():
                self.token_target()
    
    def c_clear(self):
        if self.command_not_end():
            self.token_target()
            if self.command_not_end():
                self.token_namespaced_id()
                if self.command_not_end():
                    with self.create_token(TokenType.number) as tok:
                        data = self.expect(self.integer, tok)
                        self.check_number(data, tok, -1, 2**31-1)
                    if self.command_not_end():
                        with self.create_token(TokenType.number) as tok:
                            maxcount = self.expect(self.integer, tok)
                            self.check_number(maxcount, tok, -1, 2**31-1)
    
    def c_clearspawnpoint(self):
        if self.command_not_end():
            self.token_target()
    
    def c_clone(self):
        CLONEMODES = ("force", "move", "normal")
        for _ in range(3):
            self.token_full_pos()
        if self.command_not_end():
            maskmode = self.token_options("masked", "replace", "filtered")
            if maskmode == "filtered":
                self.token_options(*CLONEMODES)
                self.token_namespaced_id()
                self.token_bs_or_data()
            else:
                if self.command_not_end():
                    self.token_options(*CLONEMODES)
    
    def c_damage(self):
        self.token_target()
        with self.create_token(TokenType.number) as tok:
            amount = self.expect(self.integer, tok)
            self.check_number(amount, tok, 0, 2**31-1)
        if self.command_not_end():
            with self.create_token(TokenType.string) as tok:
                self.expect(self.word, tok) # damage cause
            if self.command_not_end():
                self.token_options("entity")
                self.token_target()
    
    def c_deop(self):
        self.token_target()
    
    def c_dialogue(self):
        mode = self.token_options("change", "open")
        self.token_target() # npc
        if mode == "change":
            self.token_string() # sceneName
            if self.command_not_end():
                self.token_target() # players
        elif mode == "open":
            self.token_target() # player
            if self.command_not_end():
                self.token_string() # sceneName
    
    def c_difficulty(self):
        self.token_options(
            "easy", "normal", "hard", "peaceful",
            "p", "e", "n", "h", "0", "1", "2", "3"
        )
    
    def c_effect(self):
        self.token_target() # player
        with self.create_token() as tok:
            effect = self.expect(self.namespaced_id, tok)
            if effect == "clear":
                tok.type = TokenType.option
                return
            else:
                tok.type = TokenType.string
        if self.command_not_end():
            with self.create_token(TokenType.number) as tok:
                seconds = self.expect(self.integer, tok)
                self.check_number(seconds, tok, 0, 2**31-1)
            if self.command_not_end():
                with self.create_token(TokenType.number) as tok:
                    amplifier = self.expect(self.integer, tok)
                    self.check_number(amplifier, tok, 0, 255)
                if self.command_not_end():
                    with self.create_token(TokenType.boolean) as tok:
                        self.expect(self.boolean, tok)
    
    def c_enchant(self):
        self.token_target() # player
        with self.create_token() as tok:
            if self.next_is_number():
                tok.type = TokenType.number
                self.expect(self.integer, tok)
            else:
                tok.type = TokenType.string
                self.expect(self.namespaced_id, tok)
        if self.command_not_end():
            with self.create_token(TokenType.number) as tok:
                self.expect(self.integer, tok) # level
    
    def c_event(self):
        self.token_options("entity")
        self.token_target()
        self.token_string()
    
    def token_anchor_option(self):
        self.token_options("eyes", "feet")

    def c_execute(self):
        subcmd = None
        if not self.command_not_end():
            with self.create_token(TokenType.error, "Expecting a subcommand"):
                pass
        while self.command_not_end():
            subcmd = self.token_options(
                "align", "anchored", "as", "at", "facing", "in",
                "positioned", "rotated", "run", "if", "unless"
            )
            if subcmd is None:
                self.skip_line() # invalid subcommand -> end
                break
            if subcmd == "align":
                with self.create_token(TokenType.option) as tok:
                    axes = self.expect(self.word, tok)
                    if axes is not None:
                        axes = sorted(axes)
                        axes_set = set(axes)
                        if not axes_set.issubset({"x", "y", "z"}):
                            tok.type = TokenType.error
                            tok.value = \
                                "Axes can only include 'x', 'y' and 'z'"
                        if len(axes) != len(axes_set):
                            tok.type = TokenType.error
                            tok.value = "Repeat 'x', 'y' or 'z'"
            elif subcmd == "anchored":
                self.token_anchor_option()
            elif subcmd == "as" or subcmd == "at":
                self.token_target()
            elif subcmd == "facing":
                if self.next_is_pos():
                    self.token_full_pos()
                else:
                    self.token_options("entity")
                    self.token_target()
                    self.token_anchor_option()
            elif subcmd == "in":
                self.token_namespaced_id()
            elif subcmd == "positioned":
                if self.next_is_pos():
                    self.token_full_pos()
                else:
                    self.token_options("as")
                    self.token_target()
            elif subcmd == "rotated":
                if self.next_is_rotation():
                    self.token_rotation()
                else:
                    self.token_options("as")
                    self.token_target()
            elif subcmd == "run":
                self.token_command()
            elif subcmd in ("if", "unless"):
                testcmd = self.token_options(
                    "block", "blocks", "entity", "score"
                )
                if testcmd == "block":
                    self.token_full_pos()
                    self.token_namespaced_id()
                    self.token_bs_or_data()
                elif testcmd == "blocks":
                    for _ in range(3):
                        self.token_full_pos()
                    self.token_options("all", "masked")
                elif testcmd == "entity":
                    self.token_target()
                elif testcmd == "score":
                    self.token_target()
                    self.token_scoreboard()
                    if self.current_char == ">" or self.current_char == "<":
                        self.forward()
                        if self.current_char == "=":
                            self.forward()
                        match_mode = False
                    elif self.current_char == "=":
                        self.forward()
                        match_mode = False
                    else:
                        match_mode = True
                    self.skip_spaces()
                    if match_mode:
                        self.token_options("matches")
                        with self.create_token(TokenType.number) as tok:
                            self.expect(self.number_range, tok)
                    else:
                        self.token_target()
                        self.token_scoreboard()
        # the last subcommand must be "run", "if" or "unless"
        if (subcmd is not None) and (subcmd not in ("run", "if", "unless")):
            with self.create_token(
                TokenType.error,
                '"execute" must end with "run", "if" or "unless"'
            ): pass
    
    def c_fill(self):
        for _ in range(2):
            self.token_full_pos()
        self.token_namespaced_id()
        if self.command_not_end():
            self.token_bs_or_data()
            if self.command_not_end():
                mode = self.token_options(
                    "destroy", "hollow", "keep", "outline", "replace"
                )
                if mode == "replace" and self.command_not_end():
                    self.token_namespaced_id()
                    if self.command_not_end():
                        self.token_bs_or_data()
    
    def c_fog(self):
        self.token_target()
        mode = self.token_options("push", "pop", "remove")
        if mode == "push":
            self.token_namespaced_id() # Fog id
        self.token_string() # userProvidedID
    
    def c_function(self):
        self.token_skip_line("Expecting mcfunction path")
    
    def token_gamemode_option(self):
        self.token_options(
            "s", "c", "a", "d", "survival", "default"
            "creative", "adventure", "0", "1", "2", "5"
        )
    
    def c_gamemode(self):
        self.token_gamemode_option()
        if self.command_not_end():
            self.token_target()
    
    def c_gamerule(self):
        if self.command_not_end():
            with self.create_token(TokenType.string) as tok:
                self.expect(self.word, tok)
            if self.command_not_end():
                with self.create_token() as tok:
                    if self.next_is_number():
                        tok.type = TokenType.number
                        self.expect(self.integer,tok)
                    else:
                        tok.type = TokenType.boolean
                        self.expect(self.boolean, tok)
    
    def c_give(self):
        self.token_target()
        self.token_namespaced_id() # item
        if self.command_not_end():
            with self.create_token(TokenType.number) as tok:
                amount = self.expect(self.integer, tok)
                self.check_number(amount, tok, 1, 32767)
            if self.command_not_end():
                with self.create_token(TokenType.number) as tok:
                    data = self.expect(self.integer, tok)
                    self.check_number(data, tok, 0, 32767)
                if self.command_not_end():
                    self.token_json("object") # component
    
    def c_immutableworld(self):
        if self.command_not_end():
            with self.create_token(TokenType.boolean) as tok:
                self.expect(self.boolean, tok)
    
    def c_kick(self):
        self.token_target()
        self.skip_line() # reason (optional)
    
    def c_kill(self):
        if self.command_not_end():
            self.token_target()
    
    def c_list(self):
        pass
    
    def c_locate(self):
        mode = self.token_options("biome", "structure")
        if mode == "biome":
            self.token_namespaced_id()
        elif mode == "structure":
            self.token_namespaced_id()
            if self.command_not_end():
                with self.create_token(TokenType.boolean) as tok:
                    self.expect(self.boolean, tok)
    
    def c_loot(self):
        target_mode = self.token_options("spawn", "give", "insert", "replace")
        if target_mode == "spawn" or target_mode == "insert":
            self.token_full_pos()
        elif target_mode == "give":
            self.token_target()
        elif target_mode == "replace":
            replace_mode = self.token_options("block", "entity")
            if replace_mode == "block":
                self.token_full_pos()
                self.token_options("slot.container")
            elif replace_mode == "entity":
                self.token_target()
                with self.create_token(TokenType.string) as tok:
                    self.expect(self.word, tok)
            with self.create_token(TokenType.number) as tok:
                self.expect(self.integer, tok)
            if self.next_is_number():
                with self.create_token(TokenType.number) as tok:
                    amount = self.expect(self.integer, tok)
                    self.check_number(amount, tok, 1, 2**31-1)
        source_mode = self.token_options("kill", "loot")
        if source_mode == "kill":
            self.token_target()
        elif source_mode == "loot":
            self.token_namespaced_id() # loot table
        # mainhand | offhand | namespaced id (a tool)
        if self.command_not_end():
            with self.create_token() as tok:
                tool = self.expect(self.namespaced_id, tok)
                if tool == "mainhand" or tool == "offhand":
                    tok.type = TokenType.option
                else:
                    tok.type = TokenType.string

    def c_me(self):
        self.token_skip_line()
    
    def c_mobevent(self):
        self.token_namespaced_id()
        if self.command_not_end():
            with self.create_token(TokenType.boolean) as tok:
                self.expect(self.boolean, tok)
    
    def c_tell(self):
        self.token_target()
        self.token_skip_line()
    
    def c_music(self):
        mode = self.token_options("play", "queue", "stop", "volumn")
        def _volumn():
            with self.create_token(TokenType.number) as tok:
                volumn = self.expect(self.number, tok)
                self.check_number(volumn, tok, 0, 1)
        def _fade():
            with self.create_token(TokenType.number) as tok:
                fade = self.expect(self.number, tok)
                self.check_number(fade, tok, 0, 10)
        if mode == "play" or mode == "queue":
            self.token_string()
            if self.command_not_end():
                _volumn()
                if self.command_not_end():
                    _fade()
                    if self.command_not_end():
                        self.token_options("play_once", "loop")
        elif mode == "stop":
            if self.command_not_end():
                _fade()
        elif mode == "volumn":
            _volumn()
    
    def c_op(self):
        self.token_target()
    
    def c_particle(self):
        self.token_namespaced_id()
        if self.command_not_end():
            self.token_full_pos()
    
    def c_playanimation(self):
        self.token_target()
        self.token_string() # animation
        if self.command_not_end():
            self.token_string() # next state
            if self.command_not_end():
                with self.create_token(TokenType.number) as tok:
                    self.expect(self.number, tok) # blend out time
                if self.command_not_end():
                    self.token_string() # stop_expression
                    if self.command_not_end():
                        self.token_string() # controller
    
    def c_playsound(self):
        self.token_string() # sound
        if self.command_not_end():
            self.token_target() # player
            if self.command_not_end():
                self.token_full_pos() # position
                if self.command_not_end():
                    with self.create_token(TokenType.number) as tok:
                        volumn = self.expect(self.number, tok)
                        self.check_number(volumn, tok, 0)
                    if self.command_not_end():
                        with self.create_token(TokenType.number) as tok:
                            pitch = self.expect(self.number, tok)
                            self.check_number(pitch, tok, 0, 256)
                        if self.command_not_end():
                            with self.create_token(TokenType.number) as tok:
                                min_volumn = self.expect(self.number, tok)
                                self.check_number(min_volumn, tok, 0)

    def c_replaceitem(self):
        mode = self.token_options("block", "entity")
        if mode == "block":
            self.token_full_pos()
            self.token_options("slot.container")
            with self.create_token(TokenType.number) as tok:
                self.expect(self.integer, tok)
        elif mode == "entity":
            self.token_target()
            with self.create_token(TokenType.string) as tok:
                self.expect(self.word, tok) # slot
        # [oldItemHandling: ReplaceMode] <itemName: Item>
        using_handle_mode = False
        with self.create_token() as tok:
            item_or_handle = self.expect(self.namespaced_id, tok)
            if item_or_handle in ("destroy", "keep"):
                tok.type = TokenType.option
                using_handle_mode = True
            else:
                tok.type = TokenType.string
        if using_handle_mode: # require item name
            self.token_namespaced_id()
        # [amount: int] [data: int] [components: json]
        if self.command_not_end():
            with self.create_token(TokenType.number) as tok:
                amount = self.expect(self.integer, tok)
                self.check_number(amount, tok, 1, 64)
            if self.command_not_end():
                with self.create_token(TokenType.number) as tok:
                    data = self.expect(self.integer, tok)
                    self.check_number(data, tok, 0, 32767)
                if self.command_not_end():
                    self.token_json("object")
    
    def c_ride(self):
        self.token_target()
        mode = self.token_options(
            "start_riding", "stop_riding", "evict_riders",
            "summon_rider", "summon_ride"
        )
        if mode == "start_riding":
            self.token_target()
            if self.command_not_end():
                self.token_options("teleport_ride", "teleport_rider")
                if self.command_not_end():
                    self.token_options("if_group_fits", "until_full")
        elif mode == "summon_rider":
            self.token_namespaced_id() # entityType
            if self.command_not_end():
                self.token_namespaced_id() # spawnEvent
                if self.command_not_end():
                    self.token_string() # nameTag
        elif mode == "summon_ride":
            self.token_namespaced_id() # entityType
            if self.command_not_end():
                self.token_options(
                    "skip_riders", "no_ride_change", "reassign_rides"
                )
                if self.command_not_end():
                    self.token_namespaced_id() # spawnEvent
                    if self.command_not_end():
                        self.token_string() # nameTag
    
    def c_save(self):
        self.token_options("hold", "query", "resume")
    
    def c_say(self):
        self.token_skip_line()
    
    def c_schedule(self):
        self.token_options("on_area_loaded")
        self.token_options("add")
        if self.next_is_pos():
            self.token_full_pos()
            self.token_full_pos()
        else:
            mode = self.token_options("circle", "tickingarea")
            if mode == "circle":
                self.token_full_pos()
                with self.create_token(TokenType.number) as tok:
                    radius = self.expect(self.number, tok)
                    self.check_number(radius, tok, 0)
            elif mode == "tickingarea":
                self.token_string() # name of tickingarea
        self.token_skip_line("Expecting mcfunction path")
    
    def token_starrable_target(self):
        if self.current_char == "*":
            with self.create_token(TokenType.selector):
                self.char("*")
        else:
            self.token_target()

    def c_scoreboard(self):
        mode = self.token_options("objectives", "players")
        if mode == "objectives":
            submode = self.token_options("add", "list", "remove", "setdisplay")
            if submode == "add":
                self.token_scoreboard()
                self.token_options("dummy")
                if self.command_not_end():
                    self.token_string() # display name
            elif submode == "remove":
                self.token_scoreboard()
            elif submode == "setdisplay":
                display_mode = self.token_options(
                    "list", "sidebar", "belowname"
                )
                if self.command_not_end():
                    self.token_scoreboard()
                    if self.command_not_end():
                        if display_mode == "list" or display_mode == "sidebar":
                            self.token_options("ascending", "descending")
        elif mode == "players":
            submode = self.token_options(
                "set", "add", "remove", "list", "operation",
                "random", "reset", "test"
            )
            if submode in ("set", "add", "remove"):
                self.token_starrable_target()
                self.token_scoreboard()
                self.token_any_integer()
            elif submode == "list":
                if self.command_not_end():
                    self.token_starrable_target()
            elif submode == "operation":
                self.token_starrable_target()
                self.token_scoreboard()
                if self.current_char in "+-*/%":
                    self.forward() # skip the symbol
                    self.expect_char("=")
                elif self.current_char == "=" or self.current_char == "<":
                    self.forward()
                elif self.current_char == ">":
                    self.forward()
                    if self.current_char == "<":
                        self.forward() # <>
                else:
                    with self.create_token(
                        TokenType.error, "Expecting an operator"
                    ): pass
                self.skip_spaces()
                self.token_starrable_target()
                self.token_scoreboard()
            elif submode == "random":
                self.token_starrable_target()
                self.token_scoreboard()
                with self.create_token(TokenType.number) as tok:
                    min_ = self.expect(self.integer, tok)
                with self.create_token(TokenType.number) as tok:
                    max_ = self.expect(self.integer, tok)
                    if (min_ is not None and max_ is not None) and \
                        min_ > max_:
                        tok.type = TokenType.error
                        tok.value = "Random minimum value larger than maximum"
            elif submode == "reset":
                self.token_starrable_target()
                if self.command_not_end():
                    self.token_scoreboard()
            elif submode == "test":
                self.token_starrable_target()
                self.token_scoreboard()
                with self.create_token(TokenType.number) as tok:
                    if self.current_char == "*":
                        self.char("*")
                        min_ = None
                    else:
                        min_ = self.expect(self.integer, tok)
                if self.command_not_end():
                    with self.create_token(TokenType.number) as tok:
                        if self.current_char == "*":
                            self.char("*")
                        else:
                            max_ = self.expect(self.integer, tok)
                            if (min_ is not None and max_ is not None) and \
                                min_ > max_:
                                tok.type = TokenType.error
                                tok.value = \
                                    "Test minimum value larger than maximum"
    
    def c_seed(self):
        pass
    
    def c_setblock(self):
        self.token_full_pos()
        self.token_namespaced_id()
        if self.command_not_end():
            self.token_bs_or_data()
            if self.command_not_end():
                self.token_options("destroy", "keep", "replace")
    
    def c_setmaxplayers(self):
        with self.create_token(TokenType.number) as tok:
            value = self.expect(self.integer, tok)
            self.check_number(value, tok, 1, 30)
    
    def c_setworldspawn(self):
        if self.command_not_end():
            self.token_full_pos()
    
    def c_spawnpoint(self):
        if self.command_not_end():
            self.token_target()
            if self.command_not_end():
                self.token_full_pos()
    
    def c_spreadplayers(self):
        self.token_full_pos(2)
        with self.create_token(TokenType.number) as tok:
            distance = self.expect(self.number, tok)
            self.check_number(distance, tok, 0)
        with self.create_token(TokenType.number) as tok:
            max_range = self.expect(self.number, tok)
            self.check_number(max_range, tok, 1)
            if max_range <= distance:
                tok.type = TokenType.error
                tok.value = "Spread range must be larger than distance"
        self.token_target()
    
    def c_stop(self):
        pass
    
    def c_stopsound(self):
        self.token_target()
        if self.command_not_end():
            self.token_string()
    
    def c_structure(self):
        ...

    # TODO? /gametest /scriptevent

    def c_wsserver(self):
        with self.create_token() as tok:
            arg = self.skip_line()
            if arg == "out":
                tok.type = TokenType.option
            else:
                tok.type = TokenType.string
