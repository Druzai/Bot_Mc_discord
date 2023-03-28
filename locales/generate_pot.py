from os import path, system, chdir, __file__ as os_file
from sys import platform, argv, executable

if platform == "win32":
    import ctypes

    shell32 = ctypes.windll.shell32


def run_as_admin():
    if shell32.IsUserAnAdmin():
        return True

    argument_line = " ".join(argv)
    ret = shell32.ShellExecuteW(None, "runas", executable, argument_line, None, 1)
    if int(ret) <= 32:
        return False
    return None


def set_utf8(python_home: str):
    with open(f"{python_home}\\Tools\\i18n\\pygettext.py", "r") as f:
        file_contents = f.readlines()
    changed = False
    for i in range(len(file_contents)):
        if "open(options.outfile" in file_contents[i] and "encoding" not in file_contents[i]:
            file_contents[i] = f"{file_contents[i][:-2]}, encoding='UTF-8')\n"
            changed = True
    if changed:
        try:
            with open(f"{python_home}\\Tools\\i18n\\pygettext.py", "w") as f:
                f.writelines(file_contents)
                print("Set default encoding of pot file to 'UTF-8'.")
        except PermissionError:
            ret = run_as_admin()
            if ret is None:
                print("Elevated to admin privilege...")
                print("Assuming that default encoding of pot file is set to 'UTF-8'.")
                print("Run script again without admin privilege!")
            else:
                print(f"Error(ret={ret}): cannot elevate privilege.")
            exit(0)


def generate_pot_file():
    if platform == "linux" or platform == "linux2":
        system("python3 ./generate_translation_lines.py")
        chdir("locales")
        system_code = system("pygettext3 -d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    elif platform == "darwin":
        system("python3 ./generate_translation_lines.py")
        chdir("locales")
        python_home = "/".join(os_file.split("/")[:-3])
        python_version = os_file.split("/")[-2]
        system_code = system(f"python \"{python_home}/share/doc/{python_version}/examples/Tools/i18n/pygettext.py\" "
                             "-d lang -o lang.pot -v -k get_translation ../*.py ../*/*.py")
    elif platform == "win32":
        if not shell32.IsUserAnAdmin():
            system("py .\\generate_translation_lines.py")
        chdir("locales")
        python_home = "\\".join(os_file.split("\\")[:-2])
        set_utf8(python_home)
        if shell32.IsUserAnAdmin():
            print("Run script again without admin privilege!")
            input('Press ENTER to exit.')
            exit(0)
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
