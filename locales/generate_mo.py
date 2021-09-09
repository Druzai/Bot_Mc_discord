import os
from os import path, system, chdir, listdir
from sys import platform, argv


def generate_mo_files(python_home=None):
    chdir(path.dirname(argv[0]))
    for directory in listdir():
        if path.isdir(directory):
            chdir(path.join(os.getcwd(), directory, "LC_MESSAGES"))
            if platform == "linux" or platform == "linux2":
                system("msgfmt -o lang.mo lang")
            elif platform == "win32":
                system(f"python {python_home}\\Tools\\i18n\\msgfmt.py -o lang.mo lang")
            chdir("../..")

    print("Made lang.mo files!")


if __name__ == '__main__':
    if platform == "win32":
        generate_mo_files("\\".join(os.__file__.split("\\")[:-2]))
    elif platform == "linux" or platform == "linux2":
        print("Check if you have gettext installed\nTo install: 'sudo apt install gettext'")
        generate_mo_files()
    else:
        print("Your system is unknown")
