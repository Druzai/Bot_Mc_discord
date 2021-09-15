import gettext
import sys
from os import path, listdir
from pathlib import Path
from sys import argv
from typing import Optional

_locales_path = "."
if getattr(sys, 'frozen', False):
    _locales_path = sys._MEIPASS
_locales_path = Path(_locales_path + "/locales").as_posix()

_locales = [d for d in listdir(_locales_path) if path.isdir(path.join(_locales_path, d))]
_translation = None


def set_locale(locale: str, set_eng_if_error=False) -> Optional[str]:
    global _translation
    if locale.lower() in _locales or set_eng_if_error:
        _translation = gettext.translation("lang", localedir=_locales_path,
                                           languages=["en" if set_eng_if_error else locale.lower()])
    else:
        return locale


def get_translation(text: str) -> str:
    return _translation.gettext(text)


def get_locales():
    return _locales


class RuntimeTextHandler:
    _file_py = "_frozen_translations.py"
    _translations = []

    @classmethod
    def freeze_translation(cls):
        with open(Path(path.dirname(argv[0]) + f"/{cls._file_py}"), "w", encoding="utf8") as f:
            f.write("\n".join(cls._translations))

    @classmethod
    def add_translation(cls, text: str):
        cls._translations.append(f"get_translation(\"{text}\")")
