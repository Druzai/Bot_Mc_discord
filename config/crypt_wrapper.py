import binascii
from os import path

from cryptography.fernet import Fernet

_fernet: Fernet


def _init():
    global _fernet
    if not path.isfile('key'):
        key = Fernet.generate_key()
        with open("key", "wb") as key_file:
            key_file.write(key)
    try:
        with open("key", "rb") as key:
            _fernet = Fernet(key.read())  # Initialize crypt module with key
    except (ValueError, TypeError, binascii.Error):
        key = Fernet.generate_key()
        _fernet = Fernet(key)
        with open("key", "wb") as key_file:
            key_file.write(key)


def encrypt_string(string: str):
    return _fernet.encrypt(string.encode()).decode()


def decrypt_string(string: str):
    return _fernet.decrypt(string.encode()).decode()


_init()
del _init
