import gettext
import sys
from os import path, listdir, getcwd
from pathlib import Path
from sys import argv

_locales_path = getcwd()
if getattr(sys, 'frozen', False):
    _locales_path = sys._MEIPASS
_locales_path = Path(_locales_path + "/locales").as_posix()

_locales = sorted([d for d in listdir(_locales_path) if path.isdir(path.join(_locales_path, d))])
_current_locale = ""
_translation = None


def set_locale(locale: str, set_eng_if_error=False):
    global _translation, _current_locale
    if locale.lower() in _locales or set_eng_if_error:
        _current_locale = "en" if locale.lower() not in _locales and set_eng_if_error else locale.lower()
        _translation = gettext.translation("lang", localedir=_locales_path, languages=[_current_locale])
        return _current_locale
    return None


def get_translation(text: str) -> str:
    if _translation is not None:
        return _translation.gettext(text)
    else:
        return text


def get_locales():
    return _locales


def get_current_locale():
    return _current_locale


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


if len(argv) > 1 and argv[1] == "-g":
    for lang in _locales:
        RuntimeTextHandler.add_translation(lang)
