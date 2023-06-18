:locales
py ./locales/generate_mo.py
@echo Translations generated

if ["%~1"]==[""] goto pyinstaller
if ["%~1"]==["build_pyz"] goto shiv

@echo Wrong target!
goto :eof

:shiv
shiv -c Discord_bot -o dist_build/Discord_bot.pyz . -r requirements.txt
@echo Built
goto clean

:pyinstaller
pyinstaller --distpath=./dist_build Discord_bot.spec
@echo Built

:clean
rd /s /q build __pycache__ Discord_bot.egg-info
@echo Cleaned