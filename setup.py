from glob import glob
from pathlib import Path

from setuptools import setup, find_packages

from Discord_bot import VERSION

setup(
    name="Discord_bot",
    version=VERSION,
    description="Discord bot to manage Minecraft server(s)",
    packages=find_packages() + ["commands", "components", "config"],
    py_modules=["Discord_bot"],
    data_files=[("./" + str(Path(i).parent), [i]) for i in glob("locales/*/LC_MESSAGES/*.mo")],
    entry_points=dict(
        console_scripts=["Discord_bot=Discord_bot:main"],
    ),
)
