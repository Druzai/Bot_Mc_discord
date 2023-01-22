# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from os import path

block_cipher = None


def get_certs():
    from PyInstaller.utils.hooks import exec_statement

    cert_datas = exec_statement("""
        import ssl
        print(ssl.get_default_verify_paths().cafile)""").strip().split()
    return [(f, 'lib') for f in cert_datas]


def get_datas():
    data = [(f"./locales/{d}/LC_MESSAGES/lang.mo", f"locales/{d}/LC_MESSAGES") for d in os.listdir("locales") if
            path.isdir(path.join("locales", d))]
    if sys.platform == "darwin":
        data += get_certs()
    return data


a = Analysis(['Discord_bot.py'],
             pathex=['.'],
             binaries=[],
             datas=get_datas(),
             hiddenimports=['certifi'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Discord_bot',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          target_arch='x86_64',
          runtime_tmpdir=None,
          console=True, icon='images\\bot.ico')
