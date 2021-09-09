ifeq ($(OS),Windows_NT)
    uname_S := Windows
else
    uname_S := $(shell uname -s)
endif

ifeq ($(uname_S), Windows)
    target = dist_build/Discord_bot.exe
    _clean = clear_win
endif
ifeq ($(uname_S), Linux)
    target = dist_build/Discord_bot
    _clean = clear_lin
endif

.PHONY = clean_lin, clear_win

install: $(target) $(_clean)

dist_build/Discord_bot.exe:
	py ./locales/generate_mo.py
	@echo Translations generated
	pyinstaller -F --icon=images/bot.ico --add-data "images/sad_dog.jpg;images" --add-data "./locales/en/LC_MESSAGES/lang.mo;locales/en/LC_MESSAGES" --add-data "./locales/ru/LC_MESSAGES/lang.mo;locales/ru/LC_MESSAGES" --distpath=./dist_build Discord_bot.py
	@echo Built

dist_build/Discord_bot:
	py ./locales/generate_mo.py
	@echo Translations generated
	pyinstaller -F --add-data "images/sad_dog.jpg:images" --add-data "./locales/en/LC_MESSAGES/lang.mo:locales/en/LC_MESSAGES" --add-data "./locales/ru/LC_MESSAGES/lang.mo:locales/ru/LC_MESSAGES" --distpath=./dist_build Discord_bot.py
	@echo Built

clear_lin:
	$(shell rm -f -r ./build ./__pycache__)
	$(shell rm -f *.spec)
	@echo Cleaned

clear_win:
	cmd /c "rd /s /q build __pycache__ && del *.spec"
	@echo Cleaned