ifeq ($(OS), Windows_NT)
    uname_S := Windows
else
    uname_S := $(shell uname -s)
endif

ifeq ($(uname_S), Windows)
    target = dist_build/Discord_bot.exe
    _locales = generate_locales_win
    _clean = clear_win
endif
ifeq ($(uname_S), Linux)
    target = dist_build/Discord_bot
    _locales = generate_locales_lin
    _clean = clear_lin
endif
ifeq ($(uname_S), Darwin)
    target = dist_build/Discord_bot
    _locales = generate_locales_lin
    _clean = clear_lin
endif

.PHONY = clean_lin, clear_win, generate_locales_lin, generate_locales_win

install: $(_locales) $(target) $(_clean)

build_pyz: $(_locales) dist_build/Discord_bot.pyz $(_clean)

dist_build/Discord_bot.pyz:
	shiv -c Discord_bot -o dist_build/Discord_bot.pyz . -r requirements.txt
	@echo Built

dist_build/Discord_bot.exe:
	pyinstaller --distpath=./dist_build Discord_bot.spec
	@echo Built

dist_build/Discord_bot:
	pyinstaller --distpath=./dist_build Discord_bot.spec
	@echo Built

generate_locales_win:
	python ./locales/generate_mo.py
	@echo Translations generated

generate_locales_lin:
	python3 ./locales/generate_mo.py
	@echo Translations generated

clear_lin:
	$(shell rm -f -r ./build ./__pycache__ ./Discord_bot.egg-info)
	@echo Cleaned

clear_win:
	cmd /c "rd /s /q build __pycache__ Discord_bot.egg-info"
	@echo Cleaned