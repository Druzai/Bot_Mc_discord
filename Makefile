ifeq ($(OS), Windows_NT)
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
ifeq ($(uname_S), Darwin)
    target = dist_build/Discord_bot
    _clean = clear_lin
endif

.PHONY = clean_lin, clear_win

install: $(target) $(_clean)

dist_build/Discord_bot.exe:
	python ./locales/generate_mo.py
	@echo Translations generated
	pyinstaller --distpath=./dist_build Discord_bot.spec
	@echo Built

dist_build/Discord_bot:
	python3 ./locales/generate_mo.py
	@echo Translations generated
	pyinstaller --distpath=./dist_build Discord_bot.spec
	@echo Built

clear_lin:
	$(shell rm -f -r ./build ./__pycache__)
	@echo Cleaned

clear_win:
	cmd /c "rd /s /q build __pycache__"
	@echo Cleaned