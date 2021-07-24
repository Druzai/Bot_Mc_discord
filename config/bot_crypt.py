from os import path

from cryptography.fernet import Fernet


class Crypt:
    _key = None

    @classmethod
    def _init(cls):
        if not path.isfile('key'):
            key = Fernet.generate_key()
            with open("key", "wb") as key_file:
                key_file.write(key)
        with open("key", "rb") as key:
            cls._key = key.read()  # Key to decrypt

    @classmethod
    def get_crypt(cls):
        if cls._key is None:
            cls._init()
        return Fernet(cls._key)  # Initialized crypt module with key
