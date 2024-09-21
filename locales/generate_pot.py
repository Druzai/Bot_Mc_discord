from os import path, system, chdir
from sys import platform, argv

allowed_folders = ['commands', 'components', 'config']
allowed_files = ['Discord_bot.py', '_frozen_translations.py']


def generate_pot_file():
    input_files_line = (
        " ".join([f"../{s}" for s in allowed_files]) + " " +
        " ".join([f"../{f}/*.py" for f in allowed_folders])
    )
    if platform == "linux" or platform == "linux2":
        system("python3 ./generate_translation_lines.py")
        chdir("locales")
        system_code = system("pygettext3 -d lang -o lang.pot -v -k get_translation " + input_files_line)
    elif platform == "darwin":
        system("python3 ./generate_translation_lines.py")
        chdir("locales")
        system_code = system(f"python3 pygettext.py -d lang -o lang.pot -v -k get_translation " + input_files_line)
    elif platform == "win32":
        system("python .\\generate_translation_lines.py")
        chdir("locales")
        system_code = system(f"python pygettext.py -d lang -o lang.pot -v -k get_translation " + input_files_line)
    else:
        print("Your system - unknown.")
        return
    if system_code == 0:
        print("Made lang.pot!")


if __name__ == '__main__':
    chdir(path.dirname(argv[0]))
    chdir("..")
    generate_pot_file()
