#!/usr/bin/env python3
import argparse
import os
import re


def main():
    parser = argparse.ArgumentParser(description="Search in script_* files")
    parser.add_argument("pattern", help="search pattern (regex supported)")
    args = parser.parse_args()

    regex = re.compile(args.pattern, re.IGNORECASE)
    for root, _dirs, files in os.walk("."):
        for name in files:
            if not name.startswith("script_"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf8", errors="ignore") as f:
                    for idx, line in enumerate(f, 1):
                        if regex.search(line):
                            print("%s:%d:%s" % (path, idx, line.rstrip("\n")))
            except OSError:
                continue


if __name__ == "__main__":
    main()
