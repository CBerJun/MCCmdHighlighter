# The main command tokenizer

from mccmdhl.tokenizer_base import *
from mccmdhl.json_helper import JSONTokenizer
from mccmdhl.error import *
from mccmdhl.version_control import *

__all__ = ["CommandTokenizer"]

class CommandTokenizer(Tokenizer, VersionedMixin):
    
    def __init__(
        self, src: str, version=(1, 19, 70), lineno_start=1, col_start=0
    ):
        super().__init__(src, lineno_start, col_start)
        self.set_version(version)
        self.file()
    
    def get_tokens(self):
        return self.tokens
    
    def get_warnings(self):
        return self.warnings
    
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
        elif not self.line_not_end():
            pass # empty line
        else:
            self.token_command()
        self.forward() # skip \n or EOF
    
    @staticmethod
    def is_number(char: str):
        return char == "-" or char == "+" or char.isdigit()
    
    def is_terminating_char(self, char: str):
        # Test result in MCBE 1.19.30
        return char in ' ,@~^/$&"\'!#%+*=[{]}\\|<>`\n' or char == self.EOF
    
    def next_is_number(self):
        return self.is_number(self.current_char)
    
    def next_is_terminating_char(self):
        return self.is_terminating_char(self.current_char)
    
    def next_is_pos(self):
        return (
            self.next_is_number() or
            self.current_char == "~" or
            self.current_char == "^"
        )
    
    def next_is_rotation(self):
        return self.next_is_number() or self.current_char == "~"
    
    def peek_word(self):
        # Peek the next `word`, starting from current char
        i = 0
        chars = []
        cur = self.current_char
        while not self.is_terminating_char(cur):
            chars.append(cur)
            cur = self.peek(i)
            i += 1
        return "".join(chars)
    
    def skip_space_until(self, rule):
        # What this does:
        # 1. find the first non-space character `char`
        # 2. calculate `rule(char)`,
        #    if it is True, skip to the `char` and return True
        #    else, return False
        if self.current_char == " ":
            i = 0
            while self.peek(i) == " ":
                i += 1
            succeed = rule(self.peek(i))
            if succeed:
                # Above we are using `peek`, now we really skip the spaces
                for _ in range(i + 1):
                    self.forward()
            return succeed
        elif rule(self.current_char):
            return True
        return False

    def skip_line(self):
        return super().skip_line().rstrip()
    
    def expect(self, func, token: Token):
        try:
            return func()
        except Error as err:
            token.type = TokenType.error
            token.value = err
            return None
    
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
            tok.value = Error(ErrorType.NUMBER_OUT_OF_RANGE, min=min, max=max)

    def argument_end(self):
        if not self.next_is_terminating_char():
            raise Error(ErrorType.EXP_TERMINATING_CHAR)
        if self.current_char == " ":
            self.skip_spaces() # multiple spaces are skipped

    # The following methods read different kinds of arguments.
    # After reading the expecting characters, they will expect a
    # "terminating character" like space, "@", "~", etc.
    # Also, Spaces are allowed to seperate the arguments.
    # These 2 things are done by `argument_end` method

    # The methods start with `raw_` will not call the `argument_end` method.
    # e.g. `number_range` calls `raw_integer` rather than `integer`, since
    # using `integer` is going to call `argument_end` twice

    # `char` and `quoted_string` method are exceptions.
    # Since usually we don't want a terminating character after a single char
    # like "=" or a quoted string, `char` and `quoted_string` does not call
    # `argument_end`. However, we still want the spaces to be skipped,
    # so `skip_spaces` is called

    def raw_word(self):
        # an unquoted string
        res = ""
        while not self.next_is_terminating_char():
            res += self.current_char
            self.forward()
        if not res:
            raise Error(ErrorType.EXP_WORD)
        # if an unquoted string looks like a number,
        # Minecraft thinks it is a number.
        try:
            float(res)
        except ValueError:
            pass
        else:
            raise Error(ErrorType.NUMLIKE_WORD)
        return res
    
    def raw_integer(self):
        res = ""
        if self.current_char == "-" or self.current_char == "+":
            res += self.current_char
            self.forward() # skip +/-
        if not self.current_char.isdigit():
            raise Error(ErrorType.EXP_INTEGER)
        while self.current_char.isdigit():
            res += self.current_char
            self.forward()
        num = int(res)
        if not -2**31 <= num <= 2**31-1:
            raise Error(ErrorType.INT_OVERFLOW)
        return num
    
    def raw_number(self):
        # integer or floating number
        res = ""
        if self.current_char == "-" or self.current_char == "+":
            res += self.current_char
            self.forward() # skip +/-
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
        return float(res)
    
    def raw_quoted_string(self):
        # a quoted string "xxx"
        self.raw_char('"') # skip '"'
        while self.current_char != '"':
            if not self.line_not_end():
                raise Error(ErrorType.UNCLOSED_STRING)
            next_two = self.current_char + self.peek()
            if next_two == "\\\\" or next_two == '\\"':
                self.forward() # Forward 1 more time
            self.forward()
        self.raw_char('"') # skip last '"'

    def word(self):
        res = self.raw_word()
        self.argument_end()
        return res
    
    def quoted_string(self):
        res = self.raw_quoted_string()
        self.skip_spaces()
        return res
    
    def string(self):
        # word or quoted string
        if self.current_char == '"':
            return self.quoted_string()
        else:
            return self.word()
        # this does not need to call `argument_end`, since
        # both `quoted_string` and `word` handle this for us
    
    def namespaced_id(self):
        # This name is from MinecraftWiki, representing item id, block id, etc.
        # See https://wiki.biligame.com/mc/命名空间ID
        res = ""
        while not self.next_is_terminating_char():
            res += self.current_char
            self.forward()
        if not res:
            raise Error(ErrorType.EXP_ID)
        if not all((
            "0" <= char <= "9" or "a" <= char <= "z" or char in "_-.:"
        ) for char in res):
            raise Error(ErrorType.ILLEGAL_CHAR_IN_ID)
        if res.count(":") > 1:
            raise Error(ErrorType.MULTIPLE_COLONS_IN_ID)
        # if an unquoted namespace id looks like a number,
        # Minecraft thinks it is a number.
        try:
            float(res)
        except ValueError:
            pass
        else:
            raise Error(ErrorType.NUMLIKE_ID)
        self.skip_spaces()
        return res
    
    def integer(self):
        # read an integer
        res = self.raw_integer()
        self.argument_end()
        return res
    
    def number(self):
        res = self.raw_number()
        self.argument_end()
        return res
    
    def number_range(self):
        # a number range like "2", "-1..", "!3..+5"
        start, end = None, None
        if self.current_char == "!":
            self.char("!")
        if self.next_is_number():
            start = self.raw_integer()
        using_dot = self.skip_space_until(lambda c: c == ".")
        if using_dot:
            self.forward() # skip one "."
            self.raw_char(".") # expect another "."
            using_end = self.skip_space_until(self.is_number)
            if using_end:
                end = self.raw_integer()
        if start is None and end is None:
            raise Error(ErrorType.EXP_INT_RANGE)
        if (start is not None) and (end is not None) and (start > end):
            raise Error(ErrorType.IMPOSSIBLE_RANGE)
        self.argument_end()

    def boolean(self):
        word = self.raw_word()
        if word not in ("true", "false"):
            raise Error(ErrorType.EXP_BOOL)
        self.argument_end()
    
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
                self.raw_number()
        else: # number is a must when using absolute pos
            if not self.next_is_number():
                raise Error(ErrorType.EXP_POS)
            self.raw_number()
        self.argument_end()
        return res
    
    # The following method create tokens

    def token_command(self):
        # one command
        ## read command name
        with self.create_token(TokenType.command) as tok:
            # Get the command
            command = self.expect(self.word, tok)
            if command is None:
                tok.type = TokenType.error
                tok.value = Error(ErrorType.EXP_COMMAND)
                self.skip_line()
                return
            ALIAS = {
                "?": "help", "connect": "wsserver", "daylock": "alwaysday",
                "msg": "tell", "w": "tell", "tp": "teleport",
                "wb": "worldbuilder"
            }
            raw_command = command
            command = ALIAS.get(command, command)
            # Parse arguments
            try:
                command_method = getattr(self, "c_%s" % command, None)
            except NotImplementedError:
                # Can be raised by version control system
                command_method = None
            if command_method is None:
                tok.type = TokenType.error
                tok.value = Error(ErrorType.UNKNOWN_COMMAND, command=command)
                self.skip_line()
                return
            tok.value = command
        ## check if function can executes this command
        if command in (
            "connect", "deop", "op", "setmaxplayers", "whitelist",
            "save", "reload"
        ):
            self.warn_at(tok, WarningType.NO_PERMISSION, command=raw_command)
        ## read argument of command
        command_method()
        ## line should end here
        if self.line_not_end():
            with self.create_token(
                TokenType.error, Error(ErrorType.TOO_MANY_ARGS)
            ): self.skip_line()

    def token_comment(self):
        # create token for comment
        with self.create_token(TokenType.comment):
            self.forward() # skip "#"
            self.skip_line()

    def token_target(self):
        # selector or player name
        def _handle_scores():
            # just to decrease indentation :)
            for _ in self.token_list("{", "}", allow_empty=False):
                with self.create_token(TokenType.scoreboard) as tok:
                    # NOTE scores allow quoted string as key!!!
                    # e.g. @a[scores={"xxx"=1}]
                    self.expect(self.string, tok)
                self.expect_char("=")
                with self.create_token(TokenType.number) as tok:
                    self.expect(self.number_range, tok)
    
        def _hasitem_component():
            # just to decrease indentation :)
            # One object quoted by {} in hasitem
            args = []
            for _ in self.token_list("{", "}", allow_empty=False):
                arg = self.token_options(
                    "item", "data", "quantity", "location", "slot"
                )
                args.append(arg)
                self.expect_char("=")
                if arg == "item":
                    self.token_namespaced_id()
                elif arg == "data":
                    # Yep, range of hasitem "data" is from -32768 to 32767,
                    # not -1 to 32767
                    with self.create_token(TokenType.number) as tok:
                        value = self.expect(self.integer, tok)
                    if value and value < 0:
                        self.warn_at(tok, WarningType.DANGEROUS_HASITEM_DATA)
                elif arg in ("quantity", "slot"):
                    with self.create_token(TokenType.number) as tok:
                        self.expect(self.number_range, tok)
                elif arg == "location":
                    with self.create_token(TokenType.string) as tok:
                        self.expect(self.word, tok)
            if "item" not in args:
                with self.create_token(
                    TokenType.error, Error(ErrorType.HASITEM_MISSING_ITEM)
                ): pass
        
        def _handle_hasitem():
            if self.current_char == "[":
                for _ in self.token_list("[", "]", allow_empty=False):
                    _hasitem_component()
            else:
                _hasitem_component()

        def _handle_haspermission():
            for _ in self.token_list("{", "}", allow_empty=False):
                self.token_permission()
                self.expect_char("=")
                self.token_state()

        ALL_ARGS = [
            "x", "y", "z", "dx", "dy", "dz", "r", "rm",
            "scores", "tag", "name", "type", "family", "rx",
            "rxm", "ry", "rym", "hasitem", "l", "lm", "m", "c"
        ]
        if self.version >= (1, 19, 80):
            ALL_ARGS.append("haspermission")

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
                    tok.value = Error(ErrorType.INVALID_SELECTOR_TYPE, var=var)
            if self.current_char == "[":
                for _ in self.token_list("[", "]", allow_empty=False):
                # We have tested that `@e[]` is not a valid selector
                    arg = self.token_options(*ALL_ARGS)
                    self.expect_char("=")
                    if arg in ("r", "rm"):
                        self.token_number(check_min=0)
                    if arg in (
                        "dx", "dy", "dz", "rx", "rxm", "ry", "rym"
                    ):
                        self.token_number()
                    elif arg == "c":
                        self.token_integer()
                    elif arg in ("l", "lm"):
                        self.token_integer(check_min=0)
                    elif arg in ("name", "family"):
                        if self.current_char == "!":
                            self.char("!") # skip "!" if exists
                        self.token_string()
                    elif arg == "type":
                        if self.current_char == "!":
                            self.char("!")
                        self.token_namespaced_id()
                    elif arg in ("x", "y", "z"):
                        with self.create_token(TokenType.pos) as tok:
                            kind = self.expect(self.pos, tok)
                            if kind == "local":
                                tok.type = TokenType.error
                                tok.value = Error(
                                    ErrorType.LOCAL_POS_FOR_SELECTOR
                                )
                    elif arg == "scores":
                        _handle_scores()
                    elif arg == "tag":
                        if self.current_char == "!":
                            self.char("!") # skip "!" if exists
                        # NOTE tag accepts empty argument like "@a[tag=]"
                        if not self.next_is_terminating_char() or \
                            self.current_char == '"':
                            with self.create_token(TokenType.tag) as tok:
                                self.expect(self.string, tok)
                    elif arg == "hasitem":
                        _handle_hasitem()
                    elif arg == "m":
                        if self.current_char == "!":
                            self.char("!")
                        self.token_gamemode_option()
                    elif arg == "haspermission":
                        _handle_haspermission()
        self.skip_spaces()
    
    def token_options(self, *options):
        # choose between `options`
        with self.create_token(TokenType.option) as tok:
            option = self.expect(self.word, tok)
            if option is not None and option not in options:
                tok.type = TokenType.error
                tok.value = Error(
                    ErrorType.INVALID_OPTION, option=option,
                    correct = ", ".join(repr(opt) for opt in options)
                )
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
        for _ in self.token_list("[", "]", allow_empty=True):
            with self.create_token(TokenType.option) as tok:
                self.expect(self.quoted_string, tok)
            self.expect_char(":")
            if self.current_char == '"':
                with self.create_token(TokenType.string) as tok:
                    self.expect(self.quoted_string, tok)
            elif self.next_is_number():
                self.token_integer()
            else: # try boolean
                with self.create_token() as tok:
                    word = self.expect(self.word, tok)
                    if word in ("true", "false"):
                        tok.type = TokenType.boolean
                    else:
                        tok.type = TokenType.error
                        tok.value = Error(ErrorType.EXP_BS_VALUE)

    @versioned_method(version=MIN_VERSION)
    def token_bs_or_data(self):
        # blockstate or block data (integer)
        if self.next_is_number(): # data value
            self.token_integer(-1, 32767)
        elif self.current_char == "[": # block state
            self.token_blockstate()
        else:
            with self.create_token(
                TokenType.error, Error(ErrorType.EXP_BS_DV)
            ): self.skip_line()

    @token_bs_or_data.variation(version=(1, 19, 70))
    def _token_bs_or_data_1_19_70(self):
        self.token_blockstate()

    @token_bs_or_data.variation(version=(1, 19, 80))
    def _token_bs_or_data_1_19_80(self):
        # Above 1.19.80, block states are optional
        if self.current_char == "[":
            self.token_blockstate()
    
    def token_rotation(self):
        # one rotation like `0`, `~3`
        # NOTE we allow rotation out of [-180, 180] & [-90, 90] here
        # since they might be used when using bisection
        with self.create_token(TokenType.pos) as tok:
            if self.current_char == "~":
                self.forward()
                if self.next_is_number():
                    self.expect(self.number, tok)
            else:
                self.expect(self.number, tok)
        self.skip_spaces()
    
    def token_full_pos(self, dimension = 3):
        # a full_pos consists of `dimension` `pos`es
        kinds = []
        for _ in range(dimension):
            with self.create_token(TokenType.pos) as tok:
                kinds.append(self.expect(self.pos, tok))
            if "relative" in kinds and "local" in kinds:
                tok.type = TokenType.error
                tok.value = Error(ErrorType.LOCAL_POS_WITH_RELATIVE)
    
    def token_namespaced_id(self):
        with self.create_token(TokenType.string) as tok:
            self.expect(self.namespaced_id, tok)
    
    def token_string(self):
        with self.create_token(TokenType.string) as tok:
            self.expect(self.string, tok)
    
    def token_boolean(self):
        with self.create_token(TokenType.boolean) as tok:
            self.expect(self.boolean, tok)
    
    def token_scoreboard(self):
        with self.create_token(TokenType.scoreboard) as tok:
            self.expect(self.string, tok)
    
    def token_integer(self, check_min: int = None, check_max: int = None):
        with self.create_token(TokenType.number) as tok:
            value = self.expect(self.integer, tok)
            if check_min is not None:
                self.check_number(value, tok, check_min, check_max)
        return value
    
    def token_number(self, check_min: int = None, check_max: int = None):
        with self.create_token(TokenType.number) as tok:
            value = self.expect(self.number, tok)
            if check_min is not None:
                self.check_number(value, tok, check_min, check_max)
        return value
    
    def token_skip_line(
        self, error_type=ErrorType.EXP_MESSAGE, required=False
    ):
        with self.create_token(TokenType.string) as tok:
            path = self.skip_line()
            if (not path) and required:
                tok.type = TokenType.error
                tok.value = Error(error_type)
    
    def token_bool_or_options(self, *options):
        # true, false, or `options`
        # return True if true or false is used,
        # return False if `options` are used
        # return None if error
        with self.create_token() as tok:
            word = self.expect(self.word, tok)
            if word in ("true", "false"):
                tok.type = TokenType.boolean
                return True
            elif word in options:
                tok.type = TokenType.option
                return False
            else:
                tok.type = TokenType.error
                tok.value = Error(
                    ErrorType.EXP_BOOL_OR_OPTION,
                    options=", ".join(repr(opt) for opt in options)
                )
                return None
    
    def token_chained_arguments(self, *funcs):
        # Read a series of optional arguments, which are processed using the
        # given `funcs` (functions).
        # For every argument to read, it can only be specified when
        # all the arguments before it are specified.
        # It is something like this grammar:
        #  [<arg_1> [<arg_2> [... [<arg_n>]]]]
        # Most of the optional argument structure in MC are defined like this
        for func in funcs:
            if self.line_not_end():
                func()
            else:
                break
    
    # Following are the definitions of commands
    
    def c_ability(self):
        self.token_target()
        self.token_chained_arguments(
            lambda: self.token_options("worldbuilder", "mayfly", "mute"),
            self.token_boolean
        )
    
    def c_alwaysday(self):
        if self.line_not_end():
            self.token_boolean()
    
    def c_camerashake(self):
        mode = self.token_options("add", "stop")
        if mode == "add":
            self.token_target()
            self.token_chained_arguments(
                lambda: self.token_number(0, 4), # intensity
                self.token_number, # seconds
                lambda: self.token_options("positional", "rotational")
            )
        elif mode == "stop":
            if self.line_not_end():
                self.token_target()
    
    def c_clear(self):
        self.token_chained_arguments(
            self.token_target,
            self.token_namespaced_id, # item id
            lambda: self.token_integer(check_min=-1), # data
            lambda: self.token_integer(check_min=-1) # max count
        )
    
    def c_clearspawnpoint(self):
        if self.line_not_end():
            self.token_target()
    
    def c_clone(self):
        CLONEMODES = ("force", "move", "normal")
        for _ in range(3):
            self.token_full_pos()
        if self.line_not_end():
            maskmode = self.token_options("masked", "replace", "filtered")
            if maskmode == "filtered":
                self.token_options(*CLONEMODES)
                self.token_namespaced_id()
                self.token_bs_or_data()
            else:
                if self.line_not_end():
                    self.token_options(*CLONEMODES)
    
    def c_damage(self):
        self.token_target()
        self.token_integer(check_min=0) # amount
        if self.line_not_end():
            with self.create_token(TokenType.string) as tok:
                self.expect(self.word, tok) # damage cause
            if self.line_not_end():
                self.token_options("entity")
                self.token_target()
    
    def c_deop(self):
        self.token_target()
    
    def c_dialogue(self):
        mode = self.token_options("change", "open")
        self.token_target() # npc
        if mode == "change":
            self.token_string() # sceneName
            if self.line_not_end():
                self.token_target() # players
        elif mode == "open":
            self.token_target() # player
            if self.line_not_end():
                self.token_string() # sceneName
    
    def c_difficulty(self):
        if self.next_is_number():
            with self.create_token(TokenType.option) as tok:
                value = self.expect(self.integer, tok)
                self.check_number(value, tok, 0, 3)
        else:
            self.token_options(
                "easy", "normal", "hard", "peaceful",
                "p", "e", "n", "h"
            )
    
    def c_effect(self):
        self.token_target() # player
        with self.create_token() as tok:
            effect = self.expect(self.namespaced_id, tok)
            if effect == "clear":
                tok.type = TokenType.option
                return
            elif effect is not None: # make sure no error happens
                tok.type = TokenType.string
        self.token_chained_arguments(
            lambda: self.token_integer(check_min=0), # seconds
            lambda: self.token_integer(0, 255), # amplifier
            self.token_boolean # hide particles
        )
    
    def c_enchant(self):
        self.token_target() # player
        with self.create_token() as tok:
            if self.next_is_number():
                tok.type = TokenType.number
                self.expect(self.integer, tok)
            else:
                tok.type = TokenType.string
                self.expect(self.namespaced_id, tok)
        if self.line_not_end():
            self.token_integer() # level
    
    def c_event(self):
        self.token_options("entity")
        self.token_target()
        self.token_string()
    
    def token_anchor_option(self):
        self.token_options("eyes", "feet")
    
    @versioned_method(version=(1, 19, 50))
    def c_execute(self):
        subcmd = ""
        if not self.line_not_end():
            with self.create_token(
                TokenType.error, Error(ErrorType.EXP_EXECUTE_SUBCMD)
            ): pass
        while self.line_not_end() and subcmd is not None:
            subcmd = self.token_options(
                "align", "anchored", "as", "at", "facing", "in",
                "positioned", "rotated", "run", "if", "unless"
            )
            if subcmd == "align":
                with self.create_token(TokenType.option) as tok:
                    axes = self.expect(self.word, tok)
                    if axes is not None:
                        axes = sorted(axes)
                        axes_set = set(axes)
                        if not axes_set.issubset({"x", "y", "z"}):
                            tok.type = TokenType.error
                            tok.value = Error(ErrorType.ILLEGAL_CHAR_IN_AXES)
                        if len(axes) != len(axes_set):
                            tok.type = TokenType.error
                            tok.value = Error(ErrorType.REPEAT_CHAR_IN_AXES)
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
                    if self.current_char == "[" or self.next_is_number():
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
                TokenType.error, Error(ErrorType.WRONG_EXECUTE_END)
            ): pass
    
    @c_execute.variation(version=MIN_VERSION)
    def _c_execute_1_19_0(self):
        # Old /execute syntax
        # /execute <target> <pos> [detect <pos> <block> <data value>] <command>
        self.token_target()
        self.token_full_pos()
        if self.peek_word() == "detect":
            self.token_options("detect")
            self.token_full_pos()
            self.token_namespaced_id()
            self.token_integer(-1, 32767)
        self.token_command()
    
    def c_fill(self):
        for _ in range(2):
            self.token_full_pos()
        self.token_namespaced_id()
        if self.line_not_end():
            self.token_bs_or_data()
            if self.line_not_end():
                mode = self.token_options(
                    "destroy", "hollow", "keep", "outline", "replace"
                )
                if mode == "replace" and self.line_not_end():
                    self.token_namespaced_id()
                    if self.line_not_end():
                        self.token_bs_or_data()
    
    def c_fog(self):
        self.token_target()
        mode = self.token_options("push", "pop", "remove")
        if mode == "push":
            self.token_namespaced_id() # Fog id
        self.token_string() # userProvidedID
    
    def c_function(self):
        self.token_skip_line(ErrorType.EXP_FUNCTION_PATH, required=True)
    
    def token_gamemode_option(self):
        if self.next_is_number():
            with self.create_token(TokenType.option) as tok:
                gm = self.expect(self.integer, tok)
                if gm is not None and gm not in (0, 1, 2, 5):
                    tok.type = TokenType.error
                    tok.value = Error(ErrorType.INVALID_GAMEMODE_ID)
        else:
            self.token_options(
                "s", "c", "a", "d", "survival", "default",
                "creative", "adventure", "spectator"
            )
    
    def c_gamemode(self):
        self.token_gamemode_option()
        if self.line_not_end():
            self.token_target()
    
    def c_gamerule(self):
        if self.line_not_end():
            with self.create_token(TokenType.string) as tok:
                self.expect(self.word, tok)
            if self.line_not_end():
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
        self.token_chained_arguments(
            lambda: self.token_integer(1, 32767), # amount
            lambda: self.token_integer(0, 32767), # data
            lambda: self.token_json("object") # component
        )
    
    def c_help(self):
        if self.line_not_end():
            with self.create_token() as tok:
                if self.next_is_number():
                    tok.type = TokenType.number
                    self.expect(self.integer, tok)
                else:
                    tok.type = TokenType.string
                    self.expect(self.word, tok)

    def c_immutableworld(self):
        if self.line_not_end():
            self.token_boolean()

    def token_permission(self):
        self.token_options("camera", "movement")

    def token_state(self):
        with self.create_token(TokenType.boolean) as tok:
            state = self.expect(self.word, tok)
            if state not in ("enabled", "disabled"):
                tok.type = TokenType.error
                tok.value = Error(ErrorType.EXP_STATE)

    @versioned_method(version=(1, 19, 80))
    def c_inputpermission(self):
        mode = self.token_options("query", "set")
        self.token_target()
        self.token_permission()
        # In query mode, state is optional and in set mode its required
        if mode == "set" or self.line_not_end():
            self.token_state()
    
    def c_kick(self):
        self.token_target()
        self.skip_line() # reason (optional)
    
    def c_kill(self):
        if self.line_not_end():
            self.token_target()
    
    def c_list(self):
        pass
    
    def c_locate(self):
        mode = self.token_options("biome", "structure")
        if mode == "biome":
            self.token_namespaced_id()
        elif mode == "structure":
            self.token_namespaced_id()
            if self.line_not_end():
                self.token_boolean()
    
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
            self.token_integer() # slot id
            if self.next_is_number():
                self.token_integer(check_min=1) # amount
        source_mode = self.token_options("kill", "loot")
        if source_mode == "kill":
            self.token_target()
        elif source_mode == "loot":
            self.token_string() # loot table
        # mainhand | offhand | string (a tool)
        if self.line_not_end():
            with self.create_token() as tok:
                tool = self.expect(self.string, tok)
                if tool == "mainhand" or tool == "offhand":
                    tok.type = TokenType.option
                elif tool is not None: # make sure no error happens
                    tok.type = TokenType.string

    def c_me(self):
        self.token_skip_line()
    
    def c_mobevent(self):
        self.token_namespaced_id()
        if self.line_not_end():
            self.token_boolean()
    
    def c_tell(self):
        self.token_target()
        self.token_skip_line()
    
    def c_music(self):
        mode = self.token_options("play", "queue", "stop", "volumn")
        def _volumn():
            self.token_number(0, 1)
        def _fade():
            self.token_number(0, 10)
        if mode == "play" or mode == "queue":
            self.token_string()
            self.token_chained_arguments(
                _volumn,
                _fade,
                lambda: self.token_options("play_once", "loop")
            )
        elif mode == "stop":
            if self.line_not_end():
                _fade()
        elif mode == "volumn":
            _volumn()
    
    def c_op(self):
        self.token_target()
    
    def c_particle(self):
        self.token_namespaced_id()
        if self.line_not_end():
            self.token_full_pos()
    
    def c_playanimation(self):
        self.token_target()
        self.token_string() # animation
        self.token_chained_arguments(
            self.token_string, # next state
            self.token_number, # blend out time
            self.token_string, # stop expression
            self.token_string # controller
        )
    
    def c_playsound(self):
        self.token_string() # sound
        self.token_chained_arguments(
            self.token_target, # player
            self.token_full_pos, # position
            lambda: self.token_number(check_min=0), # volumn
            lambda: self.token_number(0, 256), # pitch
            lambda: self.token_number(check_min=0) # min volumn
        ) 
    
    def c_reload(self):
        pass
    
    def c_replaceitem(self):
        mode = self.token_options("block", "entity")
        if mode == "block":
            self.token_full_pos()
            self.token_options("slot.container")
        elif mode == "entity":
            self.token_target()
            with self.create_token(TokenType.string) as tok:
                self.expect(self.word, tok) # slot
        self.token_integer() # slot id
        # [oldItemHandling: ReplaceMode] <itemName: Item>
        using_handle_mode = False
        with self.create_token() as tok:
            item_or_handle = self.expect(self.namespaced_id, tok)
            if item_or_handle in ("destroy", "keep"):
                tok.type = TokenType.option
                using_handle_mode = True
            elif item_or_handle is not None: # make sure no error happens
                tok.type = TokenType.string
        if using_handle_mode: # require item name
            self.token_namespaced_id()
        # [amount: int] [data: int] [components: json]
        self.token_chained_arguments(
            lambda: self.token_integer(1, 64), # amount
            lambda: self.token_integer(0, 32767), # data
            lambda: self.token_json("object") # components
        )
    
    def c_ride(self):
        self.token_target()
        mode = self.token_options(
            "start_riding", "stop_riding", "evict_riders",
            "summon_rider", "summon_ride"
        )
        if mode == "start_riding":
            self.token_target()
            self.token_chained_arguments(
                lambda: self.token_options("teleport_ride", "teleport_rider"),
                lambda: self.token_options("if_group_fits", "until_full")
            )
        elif mode == "summon_rider":
            self.token_namespaced_id() # entityType
            self.token_chained_arguments(
                self.token_spawn_event, # spawn event
                self.token_string # name tag
            )
        elif mode == "summon_ride":
            self.token_namespaced_id() # entityType
            self.token_chained_arguments(
                lambda: self.token_options(
                    "skip_riders", "no_ride_change", "reassign_rides"
                ),
                self.token_spawn_event, # spawn event
                self.token_string # name tag
            )
    
    def c_save(self):
        self.token_options("hold", "query", "resume")
    
    def c_say(self):
        self.token_skip_line()
    
    def token_circle(self):
        # <center:full_pos(3)> <radius:int>
        self.token_full_pos()
        self.token_integer(check_min=0) # radius

    def c_schedule(self):
        self.token_options("on_area_loaded")
        self.token_options("add")
        if self.next_is_pos():
            self.token_full_pos()
            self.token_full_pos()
        else:
            mode = self.token_options("circle", "tickingarea")
            if mode == "circle":
                self.token_circle()
            elif mode == "tickingarea":
                self.token_string() # name of tickingarea
        self.token_skip_line(ErrorType.EXP_FUNCTION_PATH, required=True)
    
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
                if self.line_not_end():
                    self.token_string() # display name
            elif submode == "remove":
                self.token_scoreboard()
            elif submode == "setdisplay":
                display_mode = self.token_options(
                    "list", "sidebar", "belowname"
                )
                if self.line_not_end():
                    self.token_scoreboard()
                    if self.line_not_end():
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
                self.token_integer()
            elif submode == "list":
                if self.line_not_end():
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
                        TokenType.error, Error(ErrorType.EXP_SCB_OP)
                    ): pass
                self.skip_spaces()
                self.token_starrable_target()
                self.token_scoreboard()
            elif submode == "random":
                self.token_starrable_target()
                self.token_scoreboard()
                min_ = self.token_integer()
                with self.create_token(TokenType.number) as tok:
                    max_ = self.expect(self.integer, tok)
                    if (min_ is not None and max_ is not None) and \
                        min_ > max_:
                        tok.type = TokenType.error
                        tok.value = Error(ErrorType.IMPOSSIBLE_RANDOM)
            elif submode == "reset":
                self.token_starrable_target()
                if self.line_not_end():
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
                if self.line_not_end():
                    with self.create_token(TokenType.number) as tok:
                        if self.current_char == "*":
                            self.char("*")
                        else:
                            max_ = self.expect(self.integer, tok)
                            if (min_ is not None and max_ is not None) and \
                                min_ > max_:
                                tok.type = TokenType.error
                                tok.value = Error(ErrorType.IMPOSSIBLE_TEST)
    
    def c_seed(self):
        pass
    
    def c_setblock(self):
        self.token_full_pos()
        self.token_namespaced_id()
        self.token_chained_arguments(
            self.token_bs_or_data,
            lambda: self.token_options("destroy", "keep", "replace")
        )
    
    def c_setmaxplayers(self):
        self.token_integer(1, 30)
    
    def c_setworldspawn(self):
        if self.line_not_end():
            self.token_full_pos()
    
    def c_spawnpoint(self):
        self.token_chained_arguments(
            self.token_target,
            self.token_full_pos
        )
    
    def c_spreadplayers(self):
        self.token_full_pos(2)
        distance = self.token_number(check_min=0)
        with self.create_token(TokenType.number) as tok:
            max_range = self.expect(self.number, tok)
            self.check_number(max_range, tok, 1)
            if max_range is not None and distance is not None and \
                max_range <= distance:
                tok.type = TokenType.error
                tok.value = Error(ErrorType.IMPOSSIBLE_SPREAD)
        self.token_target()
    
    def c_stop(self):
        pass
    
    def c_stopsound(self):
        self.token_target()
        if self.line_not_end():
            self.token_string()
    
    def c_structure(self):
        mode = self.token_options("save", "load", "delete")
        self.token_string() # structure name
        if mode == "save":
            for _ in range(2):
                self.token_full_pos()
            if self.line_not_end():
                entity_given = self.token_bool_or_options("memory", "disk")
                if entity_given and self.line_not_end():
                    self.token_options("memory", "disk")
                    if self.line_not_end():
                        self.token_boolean() # include blocks
        elif mode == "load":
            def _optional_args():
                ## First part:
                # [animationMode] [animationSeconds] [includeEntities]
                # or just [includeEntities]
                ## Second part:
                # [includeBlocks] [integrity] [seed]
                animate_given = not self.token_bool_or_options(
                    "block_by_block", "layer_by_layer"
                ) # animationMode or includeEntities
                arguments_next = []
                if animate_given:
                    arguments_next.extend((
                        # animation seconds
                        lambda: self.token_number(check_min=0),
                        # include entities
                        self.token_boolean
                    ))
                arguments_next.extend((
                    self.token_boolean, # include blocks
                    lambda: self.token_number(0, 1), # integrity
                    self.token_string # seed
                ))
                self.token_chained_arguments(*arguments_next)
            
            self.token_full_pos()
            self.token_chained_arguments(
                lambda: self.token_options(
                    "0_degrees", "90_degrees", "180_degrees", "270_degrees"
                ), # rotation
                lambda: self.token_options("none", "x", "z", "xz"), # mirror
                _optional_args
            )
    
    def token_spawn_event(self):
        if self.current_char == "*":
            with self.create_token(TokenType.string):
                self.char("*")
        else:
            self.token_namespaced_id()

    @versioned_method(version=MIN_VERSION)
    def c_summon(self):
        self.token_namespaced_id() # entity type
        if self.line_not_end():
            if self.next_is_pos():
                self.token_full_pos() # spawn pos
                self.token_chained_arguments(
                    self.token_spawn_event, # spawn event
                    self.token_string # name tag
                )
            else:
                self.token_string() # name tag
                if self.line_not_end():
                    self.token_full_pos() # spawn pos
    
    @c_summon.variation(version=(1, 19, 80))
    def _c_summon_1_19_80(self):
        self.token_namespaced_id() # entity type
        if self.line_not_end():
            if self.next_is_pos():
                self.token_full_pos()
                def _rot_or_facing():
                    if self.next_is_rotation():
                        self.token_rotation()
                        if self.line_not_end():
                            self.token_rotation()
                    else:
                        self.token_options("facing")
                        if self.next_is_pos():
                            self.token_full_pos()
                        else:
                            self.token_target()
                self.token_chained_arguments(
                    _rot_or_facing,
                    self.token_spawn_event,
                    self.token_string # name
                )
            else:
                self.token_string() # name tag
                if self.line_not_end():
                    self.token_full_pos() # spawn pos

    def c_tag(self):
        self.token_starrable_target()
        mode = self.token_options("add", "remove", "list")
        if mode == "add" or mode == "remove":
            with self.create_token(TokenType.tag) as tok:
                self.expect(self.string, tok)
    
    def c_teleport(self):
        # tp [<target>]
        if not self.next_is_pos():
            self.token_target()
            # We allow the command just ends here, when only a target is given
            # because this matches `tp <destination: target>`
            # But you might think: Can there be `checkForBlocks: Boolean`
            # after target?
            # The answer is no. In Minecraft, "tp @s true" seems to be
            # understood as "teleport @s to a player named 'true'"
            if not self.line_not_end():
                return
        # <target> | <position>
        # if using position:
        # [(facing (<entity> | <position>)) |
        #  (<YRot> <XRot> [<check_for_blocks>]) |
        #  <YRot>]
        if self.next_is_pos():
            self.token_full_pos()
            if self.line_not_end():
                if self.next_is_rotation():
                    check_for_blocks = False
                    self.token_rotation()
                    if self.line_not_end():
                        self.token_rotation()
                    else: # only YRot is given, the last boolean is not allowed
                        return
                else:
                    check_for_blocks = self.token_bool_or_options("facing")
                    if not check_for_blocks: # if using facing
                        # <entity> | <position>
                        if self.next_is_pos():
                            self.token_full_pos()
                        else:
                            self.token_target()
                if not check_for_blocks and self.line_not_end():
                    # [<check_for_blocks>]
                    self.token_boolean()
        else:
            self.token_target()
            # [<check_for_blocks>]
            if self.line_not_end():
                self.token_boolean()
    
    def c_tellraw(self):
        self.token_target()
        self.token_json("object")
    
    def c_testfor(self):
        self.token_target()
    
    def c_testforblock(self):
        self.token_full_pos()
        self.token_namespaced_id() # block
        if self.line_not_end():
            self.token_bs_or_data()
    
    def c_testforblocks(self):
        for _ in range(3):
            self.token_full_pos()
        if self.line_not_end():
            self.token_options("masked", "all")
    
    def c_tickingarea(self):
        mode = self.token_options(
            "add", "remove", "remove_all", "preload", "list"
        )
        if mode == "add":
            if self.next_is_pos():
                for _ in range(2):
                    self.token_full_pos()
            else:
                self.token_options("circle")
                self.token_circle()
            self.token_chained_arguments(
                self.token_string, # name
                self.token_boolean # preload
            )
        elif mode == "remove":
            if self.next_is_pos():
                self.token_full_pos()
            else:
                self.token_string()
        elif mode == "preload":
            if self.next_is_pos():
                self.token_full_pos()
            else:
                self.token_string()
            if self.line_not_end():
                self.token_boolean() # preload
        elif mode == "list":
            if self.line_not_end():
                self.token_options("all-dimensions")
    
    def c_time(self):
        mode = self.token_options("add", "query", "set")
        if mode == "add":
            self.token_integer()
        elif mode == "query":
            self.token_options("daytime", "gametime", "day")
        elif mode == "set":
            if self.next_is_number():
                self.token_integer()
            else:
                self.token_options(
                    "day", "noon", "sunrise", "sunset", "night", "midnight"
                )
    
    def _title(self, token_msg_func):
        self.token_target()
        mode = self.token_options(
            "clear", "reset", "title", "subtitle", "actionbar", "times"
        )
        if mode in ("title", "subtitle", "actionbar"):
            token_msg_func()
        elif mode == "times":
            for _ in range(3):
                self.token_integer()
    
    def c_title(self):
        self._title(self.token_skip_line)
    
    def c_titleraw(self):
        self._title(lambda: self.token_json("object"))
    
    def c_toggledownfall(self):
        pass
    
    def c_volumearea(self):
        mode = self.token_options("add", "list", "remove", "remove_all")
        if mode == "add":
            self.token_string() # identifier
            self.token_full_pos() # from
            self.token_full_pos() # to
            if self.line_not_end():
                self.token_string() # name
        elif mode == "list":
            if self.line_not_end():
                self.token_options("all-dimensions")
        elif mode == "remove":
            if self.next_is_pos():
                self.token_full_pos()
            else:
                self.token_string()
    
    def c_worldbuilder(self):
        pass
    
    def c_weather(self):
        mode = self.token_options("clear", "rain", "thunder", "query")
        if mode in ("clear", "rain", "thunder"):
            if self.line_not_end():
                self.token_integer(0, 1000000) # duration
    
    def c_whitelist(self):
        mode = self.token_options(
            "add", "list", "off", "on", "reload", "remove"
        )
        if mode == "add" or mode == "remove":
            self.token_target()
    
    def c_wsserver(self):
        with self.create_token() as tok:
            arg = self.skip_line()
            if arg == "out":
                tok.type = TokenType.option
            else:
                tok.type = TokenType.string
    
    def c_xp(self):
        with self.create_token(TokenType.number) as tok:
            self.expect(self.raw_integer, tok)
            # Here we expect raw integer.
            # If not so, "/xp 1L @s" throws "Expecting a terminating character"
            if self.current_char == "L" or self.current_char == "l":
                self.forward()
            # Now that we have detected "L", we should call `argument_end`
            self.expect(self.argument_end, tok)
        if self.line_not_end():
            self.token_target()

    # TODO? /gametest /scriptevent
