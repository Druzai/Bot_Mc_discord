ifeq ($(OS),Windows_NT)
    uname_S := Windows
else
    uname_S := $(shell uname -s)
endif

ifeq ($(uname_S), Windows)
    target = Discord_bot.exe
    _clean = clear_win
endif
ifeq ($(uname_S), Linux)
    target = Discord_bot
    _clean = clear_lin
endif

.PHONY = clean_lin, clear_win

install: $(target) $(_clean)

Discord_bot.exe:
	pyinstaller -F --icon=images/bot.ico --add-data "images\sad_dog.jpg;images" --distpath=./dist_build Discord_bot.py
	@echo Built

Discord_bot:
	pyinstaller -F --add-data "images/sad_dog.jpg:images" --distpath=./dist_build Discord_bot.py
	@echo Built

clear_lin:
	$(shell rm -f -r ./build ./__pycache__)
	$(shell rm -f *.spec)
	@echo Cleaned

clear_win:
	cmd /c "rd /s /q build __pycache__ && del *.spec"
	@echo Cleaned