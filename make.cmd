py ./locales/generate_mo.py
@echo Translations generated
pyinstaller --distpath=./dist_build Discord_bot.spec
@echo Built
rd /s /q build __pycache__
@echo Cleaned