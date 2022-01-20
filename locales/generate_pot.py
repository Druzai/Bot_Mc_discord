from os import path, system, chdir, __file__ as os_file
from sys import platform, argv


def set_utf8(python_home: str):
    with open(f"{python_home}\\Tools\\i18n\\pygettext.py", "r") as f:
        file_contents = f.readlines()
    changed = False
    for i in range(len(file_contents)):
        if "open(options.outfile" in file_contents[i] and "encoding" not in file_contents[i]:
            file_contents[i] = f"{file_contents[i][:-2]}, encoding='UTF-8')\n"
            changed = True
    if changed:
        with open(f"{python_home}\\Tools\\i18n\\pygettext.py", "w") as f:
            f.writelines(file_contents)
            print("Set default encoding of pot file to 'UTF-8'")


def generate_pot_file():
    if platform == "linux" or platform == "linux2":
        system("python3 ./Discord_bot.py -g")
        chdir("locales")
        system_code = system("pygettext3 -d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    elif platform == "win32":
        system("py .\\Discord_bot.py -g")
        chdir("locales")
        python_home = "\\".join(os_file.split("\\")[:-2])
        set_utf8(python_home)
        system_code = system(f"python \"{python_home}\\Tools\\i18n\\pygettext.py\" "
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
