from os import path, system, chdir, listdir, getcwd, __file__ as os_file
from sys import platform, argv


def generate_mo_files(python_home=None):
    chdir(path.dirname(argv[0]))
    system_code = 0
    for directory in listdir():
        if path.isdir(directory):
            chdir(path.join(getcwd(), directory, "LC_MESSAGES"))
            if platform == "linux" or platform == "linux2" or platform == "darwin":
                system_code = system("msgfmt -o lang.mo lang")
            elif platform == "win32":
                system_code = system(f"python \"{python_home}\\Tools\\i18n\\msgfmt.py\" -o lang.mo lang")
            if system_code != 0:
                return system_code
            chdir("../..")

    print("Made lang.mo files!")


if __name__ == '__main__':
    if platform == "win32":
        generate_mo_files("\\".join(os_file.split("\\")[:-2]))
    elif platform == "linux" or platform == "linux2" or platform == "darwin":
        code = generate_mo_files()
        if code is not None:
            if platform != "darwin":
                print("Check if you have gettext installed\nTo install: 'sudo apt install gettext'")
            else:
                print("Check if you have gettext installed\nTo install: 'sudo brew install gettext'")
    else:
        print("Your system is unknown")
