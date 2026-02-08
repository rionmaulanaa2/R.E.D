Python 3 port
=============

Purpose
-------
This repo provides a Python 3-compatible reimplementation of the original
tools. The goal is to keep the same pipeline while removing Python 2-only
modules. The rotor cipher is reimplemented in pure Python to match Python 2
rotor behavior.

Requirements
------------
Core runtime
- Python 3.10+ (tested with 3.11)

Python packages
- uncompyle6
- xdis

Optional tools
- python2 (only needed when encrypting a .py input)

Setup
-----
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U uncompyle6 xdis

Quick start
-----------
Decrypt to .pyc and .py:
python decrypt.py script_file

Decrypt with a specific output name:
python decrypt.py script_file --py-out output.py

Encrypt from .pyc:
python encrypt.py file.pyc --output script_file

Encrypt from .py (automatically uses python2 if available):
python encrypt.py file.py --output script_file

Batch decrypt (test folder)
---------------------------
.venv\Scripts\python.exe bulk_decrypt_test.py
This writes per-file outputs alongside inputs and a report at:
test\decrypt_report.txt

Pipeline summary
----------------
1) script_redirect.py reverses the obfuscation (rotor + zlib + reverse/xor).
2) pyc_decryptor.py converts the custom marshaled stream into a Python 2.7 .pyc.
3) uncompyle6 decompiles the .pyc into .py source.
4) The reverse path is used for encryption.

Files and responsibilities
--------------------------
decrypt.py
  Decrypts an obfuscated script into .pyc and optionally .py. Uses
  script_redirect.py and pyc_decryptor.py, then uncompyle6 for decompile.

encrypt.py
  Encrypts a .pyc into the obfuscated script format. If input is .py, it
  compiles with python2 first (if available).

script_redirect.py
  De-obfuscation step. Rotor decrypt -> zlib decompress -> reverse/xor.

script_unredirect.py
  Obfuscation step. Reverse/xor -> zlib compress -> rotor encrypt.

pyc_decryptor.py
  Converts a custom marshaled code object stream into a Python 2.7 .pyc.

pyc_encryptor.py
  Converts a Python 2.7 .pyc into the custom marshaled stream.

pymarshal.py
  Custom marshal implementation that can remap bytecode opcodes.

rotor_compat.py
  Pure Python rotor implementation compatible with the Python 2 rotor module.

grep.py
  Searches for a pattern inside script_* files.

install.py
  Moves a script into the Android app data directory structure.

bulk_decrypt_test.py
  Batch decryption helper for the test folder; writes a report file.
