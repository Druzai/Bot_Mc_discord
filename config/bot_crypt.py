from os import path

from cryptography.fernet import Fernet


class Crypt:
    _key = None

    @staticmethod
    def init():
        if not path.isfile('key'):
            key = Fernet.generate_key()
            with open("key", "wb") as key_file:
                key_file.write(key)
        Crypt._key = open("key", "rb").read()  # Key to decrypt

    @staticmethod
    def get_crypt():
        if Crypt._key is None:
            Crypt.init()
        return Fernet(Crypt._key)  # Initialized crypt module with key
