from os import path, system, chdir, __file__ as os_file
from sys import platform, argv


def generate_pot_file():
    if platform == "linux" or platform == "linux2":
        system("python3 ./Discord_bot.py -g")
        chdir("locales")
        system_code = system("pygettext3 -d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    elif platform == "win32":
        system("py .\\Discord_bot.py -g")
        chdir("locales")
        python_home = "\\".join(os_file.split("\\")[:-2])
        system_code = system(f"python {python_home}\\Tools\\i18n\\pygettext.py "
                             "-d lang -o lang.pot -v -k get_translation ..\\*.py ..\\*\\*.py")
    else:
        print("Your system - unknown.")
        return
    if system_code == 0:
        print("Made lang.pot!")


if __name__ == '__main__':
    chdir(path.dirname(argv[0]))
    chdir("..")
    generate_pot_file()
