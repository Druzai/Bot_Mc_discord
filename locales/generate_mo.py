from os import path, system, chdir, listdir, getcwd, __file__ as os_file
from sys import platform, argv


def generate_mo_files(python_home=None, python_version=None):
    chdir(path.dirname(argv[0]))
    system_code = 0
    for directory in listdir():
        if path.isdir(directory):
            chdir(path.join(getcwd(), directory, "LC_MESSAGES"))
            if platform == "linux" or platform == "linux2":
                system_code = system("msgfmt -o lang.mo lang")
            elif platform == "darwin":
                system_code = system(f"python \"{python_home}/share/doc/{python_version}"
                                     "/examples/Tools/i18n/msgfmt.py\" -o lang.mo lang")
            elif platform == "win32":
                system_code = system(f"python \"{python_home}\\Tools\\i18n\\msgfmt.py\" -o lang.mo lang")
            if system_code != 0:
                return system_code
            chdir("../..")

    print("Made lang.mo files!")


if __name__ == '__main__':
    python_home = None
    if platform == "win32":
        python_home = "\\".join(os_file.split("\\")[:-2])
        generate_mo_files(python_home)
    elif platform == "linux" or platform == "linux2" or platform == "darwin":
        python_version = None
        if platform == "darwin":
            python_home = "/".join(os_file.split("/")[:-3])
            python_version = os_file.split("/")[-2]
        code = generate_mo_files(python_home, python_version)
        if code is not None and platform != "darwin":
            print("Check if you have gettext installed\nTo install: 'sudo apt install gettext'")
    else:
        print("Your system is unknown")
