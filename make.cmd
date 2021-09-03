pyinstaller -F --icon=images/bot.ico --add-data "images\sad_dog.jpg;images" --distpath=./dist_build Discord_bot.py
@echo Built
cmd /c "rd /s /q build __pycache__"
del *.spec
@echo Cleaned