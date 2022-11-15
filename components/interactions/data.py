from enum import Enum, auto


class SelectChoice(Enum):
    DO_NOTHING = auto()
    STOP_VIEW = auto()
    DELETE_SELECT = auto()
