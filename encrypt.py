#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import pyc_encryptor
import script_unredirect


def _find_python2(executable: str) -> str:
    if os.path.isabs(executable) and os.path.exists(executable):
        return executable
    return shutil.which(executable) or ""


def _compile_py2(python2: str, source_path: str, work_dir: str) -> str:
    cmd = [python2, "-m", "py_compile", source_path]
    result = subprocess.run(cmd, cwd=work_dir, check=False)
    if result.returncode != 0:
        return ""
    return source_path + "c"


def _ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Encrypt .py/.pyc into obfuscated script",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Examples:\n"
        "  python encrypt.py myfile.py\n"
        "  python encrypt.py myfile.pyc --out-dir out\n"
        "  python encrypt.py myfile.py --python2 C:/Python27/python.exe\n",
    )
    parser.add_argument("input", help="input .py or .pyc")
    parser.add_argument("--output", help="output script path")
    parser.add_argument("--out-dir", help="output directory (default: input folder)")
    parser.add_argument("--python2", default="python2", help="python2 executable for compiling .py")
    parser.add_argument("--keep-temp", action="store_true", help="keep intermediate .out")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print("[!] input not found: %s" % input_path, file=sys.stderr)
        sys.exit(2)
    base_name, ext = os.path.splitext(os.path.basename(input_path))
    input_dir = os.path.dirname(os.path.abspath(input_path))
    output_dir = args.out_dir or input_dir
    _ensure_dir(output_dir)
    output_path = args.output or os.path.join(output_dir, base_name)

    temp_dir = tempfile.mkdtemp(prefix="raic1_")
    pyc_path = ""
    cleanup_pyc = False

    if ext.lower() == ".pyc":
        pyc_path = input_path
    elif ext.lower() == ".py":
        python2 = _find_python2(args.python2)
        if not python2:
            print(
                "[!] python2 not found; provide --python2 or use a .pyc input",
                file=sys.stderr,
            )
            sys.exit(2)
        pyc_path = _compile_py2(python2, os.path.abspath(input_path), os.path.dirname(os.path.abspath(input_path)))
        if not pyc_path:
            print("[!] python2 compile failed", file=sys.stderr)
            sys.exit(2)
        cleanup_pyc = True
    else:
        print("[!] input must be .py or .pyc", file=sys.stderr)
        sys.exit(2)

    out_path = os.path.join(temp_dir, base_name + ".out")
    encryptor = pyc_encryptor.PYCEncryptor()
    encryptor.decrypt_file(pyc_path, out_path)

    obfuscated = script_unredirect.unnpk(open(out_path, "rb").read())
    with open(output_path, "wb") as f:
        f.write(obfuscated)

    print("[i] wrote: %s" % output_path)

    if not args.keep_temp:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if cleanup_pyc and os.path.exists(pyc_path):
        os.remove(pyc_path)


if __name__ == "__main__":
    main()
