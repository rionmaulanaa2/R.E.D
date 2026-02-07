#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import pyc_decryptor
import script_redirect


def _run_uncompyle6(pyc_path: str, output_path: str) -> bool:
    try:
        from uncompyle6.main import decompile_file
        import contextlib

        with open(output_path, "w", encoding="utf8", errors="replace") as out:
            with open(os.devnull, "w", encoding="utf8") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    decompile_file(pyc_path, outstream=out)
        return True
    except ModuleNotFoundError:
        module_candidates = ["uncompyle6", "uncompyle6.main"]
        for module_name in module_candidates:
            cmd = [sys.executable, "-m", module_name, "-o", os.path.dirname(output_path) or ".", pyc_path]
            if subprocess.run(cmd, check=False).returncode == 0:
                return True
    except BaseException:
        return False
    return False


def main():
    parser = argparse.ArgumentParser(description="Decrypt obfuscated script to .pyc/.py")
    parser.add_argument("input", help="input script")
    parser.add_argument("--pyc-out", help="output .pyc path")
    parser.add_argument("--py-out", help="output .py path")
    parser.add_argument("--no-decompile", action="store_true", help="skip uncompyle6")
    parser.add_argument("--keep-temp", action="store_true", help="keep intermediate .out")
    args = parser.parse_args()

    input_path = args.input
    input_dir = os.path.dirname(os.path.abspath(input_path))
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    pyc_out = args.pyc_out or os.path.join(input_dir, base_name + ".pyc")
    py_out = args.py_out or os.path.join(input_dir, base_name + ".py")

    data = script_redirect.unnpk(open(input_path, "rb").read())

    temp_dir = tempfile.mkdtemp(prefix="raic1_")
    out_path = os.path.join(temp_dir, base_name + ".out")
    with open(out_path, "wb") as f:
        f.write(data)

    decryptor = pyc_decryptor.PYCEncryptor()
    decryptor.decrypt_file(out_path, pyc_out)

    if not args.no_decompile:
        ok = _run_uncompyle6(pyc_out, py_out)
        if not ok:
            print("[!] uncompyle6 failed or is not installed", file=sys.stderr)

    if args.keep_temp:
        print("[i] temp output: %s" % out_path)
    else:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
