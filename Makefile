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

$(target):
	pyinstaller -F --icon=bot.ico --distpath=./ Discord_bot.py
	@echo Built

clear_lin:
	$(shell rm -f -r ./build ./__pycache__)
	$(shell rm -f *.spec)
	@echo Cleaned

clear_win:
	cmd /c "rd /s /q build __pycache__"
	del *.spec
	@echo Cleaned