py ./locales/generate_mo.py
@echo Translations generated
pyinstaller -F --icon=images/bot.ico --add-data "images/sad_dog.jpg;images" --add-data "./locales/en/LC_MESSAGES/lang.mo;locales/en/LC_MESSAGES" --add-data "./locales/ru/LC_MESSAGES/lang.mo;locales/ru/LC_MESSAGES" --distpath=./dist_build Discord_bot.py
@echo Built