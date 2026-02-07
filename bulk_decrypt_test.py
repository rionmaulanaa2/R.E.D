#!/usr/bin/env python3
import os
import tempfile

import decrypt
import pyc_decryptor
import script_redirect


def main():
    root = os.path.join(os.path.dirname(__file__), "test")
    log_path = os.path.join(root, "decrypt_report.txt")
    skip_ext = {".py", ".pyc", ".out", ".decrypted.py"}

    processed = 0
    success = 0
    fail = 0

    temp_dir = tempfile.mkdtemp(prefix="raic1_bulk_")
    decryptor = pyc_decryptor.PYCEncryptor()

    with open(log_path, "w", encoding="utf8") as log:
        for dirpath, _dirs, filenames in os.walk(root):
            for name in filenames:
                _, ext = os.path.splitext(name)
                if ext.lower() in skip_ext:
                    continue

                infile = os.path.join(dirpath, name)
                out_py = infile + ".decrypted.py"
                pyc_out = infile + ".pyc"
                out_path = os.path.join(temp_dir, name + ".out")

                processed += 1
                try:
                    data = script_redirect.unnpk(open(infile, "rb").read())
                except Exception as exc:
                    fail += 1
                    log.write("FAIL: %s\n" % infile)
                    log.write("stage=unnpk error=%s\n\n" % exc)
                    continue

                try:
                    with open(out_path, "wb") as f:
                        f.write(data)
                    decryptor.decrypt_file(out_path, pyc_out)
                except Exception as exc:
                    fail += 1
                    log.write("FAIL: %s\n" % infile)
                    log.write("stage=pyc error=%s\n\n" % exc)
                    continue

                ok = decrypt._run_uncompyle6(pyc_out, out_py)
                if ok and os.path.exists(out_py):
                    success += 1
                else:
                    fail += 1
                    log.write("FAIL: %s\n" % infile)
                    log.write("stage=decompile error=uncompyle6_failed\n\n")

        log_summary = "Processed: %d, Success: %d, Fail: %d\n" % (processed, success, fail)
        log.write(log_summary)

    print(log_summary)


if __name__ == "__main__":
    main()
