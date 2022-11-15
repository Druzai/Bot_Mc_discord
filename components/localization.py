import gettext
import sys
from os import path, listdir, getcwd
from pathlib import Path
from sys import argv

from components.constants import UNITS, DEATH_MESSAGES, ENTITIES

_locales_path = getcwd()
if getattr(sys, 'frozen', False) and getattr(sys, '_MEIPASS', False):
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


def check_if_string_in_all_translations(translate_text: str, match_text: str):
    current_locale = get_current_locale()
    list_of_locales = get_locales()
    list_of_locales.remove(current_locale)
    list_of_locales.append(current_locale)
    if match_text == get_translation(translate_text):
        return True

    for locale in list_of_locales:
        set_locale(locale)
        if locale != current_locale and match_text == get_translation(translate_text):
            return True
    return False


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

    for un in UNITS:
        RuntimeTextHandler.add_translation(un)
    for msg in DEATH_MESSAGES:
        RuntimeTextHandler.add_translation(msg)
    for entity in ENTITIES:
        RuntimeTextHandler.add_translation(entity)
