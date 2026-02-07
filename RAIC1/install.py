#!/usr/bin/env python3
import argparse
import os
import shutil


def main():
    parser = argparse.ArgumentParser(description="Move script into Android app data dir")
    parser.add_argument("script", help="script file to move")
    parser.add_argument("subdir", help="subdir name")
    args = parser.parse_args()

    base = "/sdcard/Android/data/com.netease.g93na/files/netease/smc"
    week_dir = os.path.join(base, "script_week", args.subdir)
    patch_dir = os.path.join(base, "script_patch", args.subdir)

    target_dir = week_dir if os.path.isdir(week_dir) else patch_dir
    os.makedirs(target_dir, exist_ok=True)
    shutil.move(args.script, os.path.join(target_dir, os.path.basename(args.script)))


if __name__ == "__main__":
    main()
