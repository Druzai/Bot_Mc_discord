from os import path, system, chdir
from sys import platform, argv


def generate_pot_file():
    if platform == "linux" or platform == "linux2":
        system("python3 ./generate_translation_lines.py")
        chdir("locales")
        system_code = system("pygettext3 -d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    elif platform == "darwin":
        system("python3 ./generate_translation_lines.py")
        chdir("locales")
        system_code = system(f"python3 pygettext.py -d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    elif platform == "win32":
        system("python .\\generate_translation_lines.py")
        chdir("locales")
        system_code = system(f"python pygettext.py -d lang -o lang.pot -v -k get_translation ..\\*.py ..\\*\\*.py")
    else:
        print("Your system - unknown.")
        return
    if system_code == 0:
        print("Made lang.pot!")


if __name__ == '__main__':
    chdir(path.dirname(argv[0]))
    chdir("..")
    generate_pot_file()
