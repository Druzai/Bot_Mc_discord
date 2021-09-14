import os
from sys import platform

if platform == "linux" or platform == "linux2":
    os.chdir("..")
    os.system("python3 ./Discord_bot.py -g")
    os.chdir("locales")
    os.system("pygettext3 -d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    print("Made lang.pot!")
elif platform == "win32":
    python_home = "\\".join(os.__file__.split("\\")[:-2])
    os.chdir("..")
    os.system("py .\\Discord_bot.py -g")
    os.chdir("locales")
    os.system(f"python {python_home}\\Tools\\i18n\\pygettext.py "
              "-d lang -o lang.pot -v -k get_translation ..\\*.py ..\\*\\*.py")
    print("Made lang.pot!")
else:
    print("Your system - unknown.")
