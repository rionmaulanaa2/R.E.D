RAIC1 (Python 3 port)
=======================

This folder provides a Python 3-compatible reimplementation of the tools in
Work/. The goal is to keep the same pipeline while removing Python 2-only
modules. The rotor cipher is reimplemented in pure Python to match Python 2
rotor behavior.

What is included
----------------
- decrypt.py: decode an obfuscated script into .pyc and optionally .py.
- encrypt.py: encode .pyc (or .py if python2 is available) into an obfuscated script.
- script_redirect.py / script_unredirect.py: reversible obfuscation steps.
- pyc_decryptor.py / pyc_encryptor.py: marshal rewriter for Python 2.7 bytecode.
- pymarshal.py: custom marshal that understands Python 2 code objects.
- rotor_compat.py: Python 3 rotor implementation (deterministic).
- grep.py: search for patterns inside script_* files.
- install.py: move a script into the Android app data directory.

Notes
-----
- These tools are designed around Python 2.7 bytecode and .pyc headers.
- If you want to compile .py into Python 2.7 bytecode, you still need a
  python2 executable available on your system.
- uncompyle6 and xdis are required to decompile .pyc into .py during decrypt.

Setup (Python 3)
----------------
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U uncompyle6 xdis

Examples
--------
python decrypt.py script_file
python decrypt.py script_file --py-out output.py
python encrypt.py file.py --output script_file
python encrypt.py file.pyc --output script_file

Batch decrypt (test folder)
---------------------------
.venv\Scripts\python.exe bulk_decrypt_test.py
This writes per-file outputs alongside inputs and a report at:
test\decrypt_report.txt
