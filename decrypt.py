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


def _ensure_python_packages(packages) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "-U"] + list(packages)
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
    except (ModuleNotFoundError, ImportError):
        if auto_install and _ensure_python_packages(("uncompyle6", "xdis")):
            return _run_uncompyle6(pyc_path, output_path, auto_install=False)
        module_candidates = ["uncompyle6", "uncompyle6.main"]
        for module_name in module_candidates:
            cmd = [sys.executable, "-m", module_name, "-o", os.path.dirname(output_path) or ".", pyc_path]
            if subprocess.run(cmd, check=False).returncode == 0:
                return _ensure_output_path(pyc_path, output_path)
    except BaseException:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
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
    except (ModuleNotFoundError, ImportError):
        if auto_install and _ensure_python_packages(("decompyle3", "xdis")):
            return _run_decompyle3(pyc_path, output_path, auto_install=False)
        module_candidates = ["decompyle3", "decompyle3.main"]
        for module_name in module_candidates:
            cmd = [sys.executable, "-m", module_name, "-o", os.path.dirname(output_path) or ".", pyc_path]
            if subprocess.run(cmd, check=False).returncode == 0:
                return _ensure_output_path(pyc_path, output_path)
    except BaseException:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        return False
    return False


_PARSE_ERROR_RE = re.compile(
    r"^def\s+([A-Za-z_]\w*)Parse error at or near [`']([^`']+)[`'] instruction at offset (\d+)\s*$"
)


def _has_parse_errors(output_path: str) -> bool:
    try:
        with open(output_path, "r", encoding="utf8", errors="replace") as infile:
            for line in infile:
                if _PARSE_ERROR_RE.match(line.strip()):
                    return True
    except OSError:
        return False
    return False


def _count_code_lines(output_path: str) -> int:
    try:
        with open(output_path, "r", encoding="utf8", errors="replace") as infile:
            count = 0
            for line in infile:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                count += 1
            return count
    except OSError:
        return 0


def _sanitize_parse_errors(output_path: str) -> bool:
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
                "    raise RuntimeError(\"decompiler parse error: %s at offset %s\")\n"
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


def _run_decompiler_chain(pyc_path: str, output_path: str, auto_install: bool = False):
    runners = ("uncompyle6", _run_uncompyle6), ("decompyle3", _run_decompyle3)
    results = []
    for name, runner in runners:
        temp_out = output_path + ".tmp." + name
        if os.path.exists(temp_out):
            os.remove(temp_out)
        if runner(pyc_path, temp_out, auto_install=auto_install):
            score = _count_code_lines(temp_out)
            has_errors = _has_parse_errors(temp_out)
            results.append((score, has_errors, name, temp_out))
    if results:
        results.sort(key=lambda item: (item[0], not item[1]), reverse=True)
        _score, _has_errors, name, temp_out = results[0]
        shutil.move(temp_out, output_path)
        for _score, _has_errors, _name, other_path in results[1:]:
            if os.path.exists(other_path):
                os.remove(other_path)
        return name
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Decrypt obfuscated script to .pyc/.py",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Examples:\n"
        "  python decrypt.py encrypted_file\n"
        "  python decrypt.py encrypted_file --out-dir out\n"
        "  python decrypt.py encrypted_file --no-decompile\n"
        "  python decrypt.py encrypted_file --auto-install\n",
    )
    parser.add_argument("input", help="input script")
    parser.add_argument("--pyc-out", help="output .pyc path")
    parser.add_argument("--py-out", help="output .py path")
    parser.add_argument("--out-dir", help="output directory (default: input folder)")
    parser.add_argument("--no-decompile", action="store_true", help="skip decompilation")
    parser.add_argument("--auto-install", action="store_true", help="auto install missing python packages")
    parser.add_argument("--keep-temp", action="store_true", help="keep intermediate .out")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print("[!] input not found: %s" % input_path, file=sys.stderr)
        sys.exit(2)
    input_dir = os.path.dirname(os.path.abspath(input_path))
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_dir = args.out_dir or input_dir
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    pyc_out = args.pyc_out or os.path.join(output_dir, base_name + ".pyc")
    py_out = args.py_out or os.path.join(output_dir, base_name + ".py")

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
        else:
            if _sanitize_parse_errors(py_out):
                print("[i] sanitized decompiler parse errors", file=sys.stderr)

    if os.path.exists(pyc_out):
        print("[i] wrote: %s" % pyc_out)
    if not args.no_decompile and os.path.exists(py_out):
        print("[i] wrote: %s" % py_out)

    if args.keep_temp:
        print("[i] temp output: %s" % out_path)
    else:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
