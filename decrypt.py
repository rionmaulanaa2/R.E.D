#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pyc_decryptor
import script_redirect


def _ensure_output_path(pyc_path: str, output_path: str) -> bool:
    if os.path.exists(output_path):
        return True
    candidate = os.path.join(
        os.path.dirname(output_path) or ".", os.path.splitext(os.path.basename(pyc_path))[0] + ".py"
    )
    if os.path.exists(candidate):
        shutil.move(candidate, output_path)
        return True
    return False


def _ensure_python_package(package: str) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", package]
    return subprocess.run(cmd, check=False).returncode == 0


def _run_uncompyle6(pyc_path: str, output_path: str, auto_install: bool = False) -> bool:
    try:
        from uncompyle6.main import decompile_file
        import contextlib

        with open(output_path, "w", encoding="utf8", errors="replace") as out:
            with open(os.devnull, "w", encoding="utf8") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    decompile_file(pyc_path, outstream=out)
        return True
    except ModuleNotFoundError:
        if auto_install and _ensure_python_package("uncompyle6"):
            return _run_uncompyle6(pyc_path, output_path, auto_install=False)
        module_candidates = ["uncompyle6", "uncompyle6.main"]
        for module_name in module_candidates:
            cmd = [sys.executable, "-m", module_name, "-o", os.path.dirname(output_path) or ".", pyc_path]
            if subprocess.run(cmd, check=False).returncode == 0:
                return _ensure_output_path(pyc_path, output_path)
    except BaseException:
        return False
    return False


def _run_decompyle3(pyc_path: str, output_path: str, auto_install: bool = False) -> bool:
    try:
        from decompyle3.main import decompile_file
        import contextlib

        with open(output_path, "w", encoding="utf8", errors="replace") as out:
            with open(os.devnull, "w", encoding="utf8") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    decompile_file(pyc_path, outstream=out)
        return True
    except ModuleNotFoundError:
        if auto_install and _ensure_python_package("decompyle3"):
            return _run_decompyle3(pyc_path, output_path, auto_install=False)
        module_candidates = ["decompyle3", "decompyle3.main"]
        for module_name in module_candidates:
            cmd = [sys.executable, "-m", module_name, "-o", os.path.dirname(output_path) or ".", pyc_path]
            if subprocess.run(cmd, check=False).returncode == 0:
                return _ensure_output_path(pyc_path, output_path)
    except BaseException:
        return False
    return False


def _run_decompiler_chain(pyc_path: str, output_path: str, auto_install: bool = False):
    for name, runner in (("uncompyle6", _run_uncompyle6), ("decompyle3", _run_decompyle3)):
        if runner(pyc_path, output_path, auto_install=auto_install):
            return name
    return None


_PARSE_ERROR_RE = re.compile(
    r"^def\s+([A-Za-z_]\w*)Parse error at or near `([^`]+)` instruction at offset (\d+)\s*$"
)


def _sanitize_uncompyle6_output(output_path: str) -> bool:
    try:
        with open(output_path, "r", encoding="utf8", errors="replace") as infile:
            lines = infile.readlines()
    except OSError:
        return False

    changed = False
    new_lines = []
    for line in lines:
        match = _PARSE_ERROR_RE.match(line.strip())
        if match:
            func_name, opcode, offset = match.group(1), match.group(2), match.group(3)
            new_lines.append("def %s(*args, **kwargs):\n" % func_name)
            new_lines.append(
                "    raise RuntimeError(\"uncompyle6 parse error: %s at offset %s\")\n"
                % (opcode, offset)
            )
            new_lines.append("\n")
            changed = True
        else:
            new_lines.append(line)

    if changed:
        with open(output_path, "w", encoding="utf8", errors="replace") as outfile:
            outfile.writelines(new_lines)
    return changed


def main():
    parser = argparse.ArgumentParser(description="Decrypt obfuscated script to .pyc/.py")
    parser.add_argument("input", help="input script")
    parser.add_argument("--pyc-out", help="output .pyc path")
    parser.add_argument("--py-out", help="output .py path")
    parser.add_argument("--no-decompile", action="store_true", help="skip decompilation")
    parser.add_argument("--auto-install", action="store_true", help="auto install missing python packages")
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
        decompiler = _run_decompiler_chain(pyc_out, py_out, auto_install=args.auto_install)
        if not decompiler:
            print("[!] decompile failed or decompiler is not installed", file=sys.stderr)
        elif decompiler == "uncompyle6":
            if _sanitize_uncompyle6_output(py_out):
                print("[i] sanitized uncompyle6 parse errors", file=sys.stderr)

    if args.keep_temp:
        print("[i] temp output: %s" % out_path)
    else:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
