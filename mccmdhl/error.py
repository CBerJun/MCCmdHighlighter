# Error definitions for Minecraft Command Tokenizer
import enum

__all__ = ["ErrorType", "Error"]

class ErrorType(enum.Enum):
    EXP_TERMINATING_CHAR = "Expecting a terminating character"
    EXP_WORD = "Expecting a word"
    EXP_ID = "Expecting an namespaced identifier"
    EXP_MESSAGE = "Expecting a message"
    EXP_CHAR = "Expecting character {char!r}"
    EXP_INTEGER = "Expecting an integer"
    EXP_NUMBER = "Expecting a number"
    EXP_INT_RANGE = "Expecting an integer range"
    EXP_BOOL = "Expecting a boolean value"
    EXP_BOOL_OR_OPTION = "Expecting boolean or {options}"
    EXP_POS = "Expecting a position"
    EXP_JSON = "Expecting a JSON object"
    EXP_COMMAND = "Expecting a command"
    EXP_BS_DV = "Expecting block state or data value"
    EXP_BS_VALUE = "Expecting a boolean, an integer or a string"
    EXP_EXECUTE_SUBCMD = "Expecting an execute subcommand"
    EXP_FUNCTION_PATH = "Expecting function path"
    EXP_SCB_OP = "Expecting one of +=, -=, *=, /=, %=, =, >, <, ><"
    UNCLOSED_STRING = "Unclosed string"
    UNCLOSED_BRACE = "Unclosed '{{'"
    UNCLOSED_BRACKET = "Unclosed '['"
    TRAILING_COMMA = "Trailing comma is not allowed"
    NUMBER_OUT_OF_RANGE = "Number not in range: [{min}, {max}]"
    INT_OVERFLOW = "Integer overflow"
    INCOMPLETE_FLOAT = "Incomplete floating number"
    IMPOSSIBLE_RANGE = "Start of integer range is larger than end"
    IMPOSSIBLE_RANDOM = "Random minimum value larger than maximum"
    IMPOSSIBLE_TEST = "Test minimum value larger than maximum"
    IMPOSSIBLE_SPREAD = "Spread range must be larger than distance"
    NUMLIKE_WORD = "A number-like word must be quoted"
    NUMLIKE_ID = "A namespaced ID can't be number-like"
    ILLEGAL_CHAR_IN_ID = "Namespaced ID should only include " \
        "a-z, 0-9, _, -, . and :"
    ILLEGAL_CHAR_IN_AXES = '"align" axes can only include character ' \
        "'x', 'y' and 'z'"
    REPEAT_CHAR_IN_AXES = "Repeat 'x', 'y' or 'z' in \"align\" axes"
    MULTIPLE_COLONS_IN_ID = "More than 1 colon in namespaced id"
    UNKNOWN_COMMAND = "Unknown command: {command!r}"
    TOO_MANY_ARGS = "Too many arguments"
    TOO_MUCH_JSON = "Characters after end of JSON"
    INVALID_OPTION = "Invalid option: {option!r}; Expecting {correct}"
    INVALID_HASITEM_ARG = "Invalid hasitem argument: {arg!r}"
    HASITEM_MISSING_ITEM = '"item" argument is required for hasitem'
    INVALID_SELECTOR_TYPE = "Invalid selector type: {var!r}"
    INVALID_SELECTOR_ARG = "Invalid selector argument: {arg!r}"
    INVALID_GAMEMODE_ID = "Invalid game mode id"
    LOCAL_POS_FOR_SELECTOR = "^ pos can not be used for " \
        "selector argument 'x', 'y' and 'z'"
    LOCAL_POS_WITH_RELATIVE = "~ and ^ can not be used together in postion"
    WRONG_EXECUTE_END = '"execute" must end with "run", "if" or "unless"'

class Error(Exception):
    def __init__(self, error_type: ErrorType, **kwargs) -> None:
        super().__init__()
        self.type = error_type
        self.error_kwargs = kwargs
    
    def __str__(self) -> str:
        return self.type.value.format(**self.error_kwargs)
