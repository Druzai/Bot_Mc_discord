py ./locales/generate_mo.py
@echo Translations generated
pyinstaller -F --distpath=./dist_build Discord_bot.spec
@echo Built