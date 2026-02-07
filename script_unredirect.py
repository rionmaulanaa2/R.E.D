#!/usr/bin/env python3
import argparse
import zlib
import sys
import rotor_compat


def _reverse_bytes(data: bytes) -> bytes:
    buf = bytearray(data)
    buf.reverse()
    limit = min(128, len(buf))
    for i in range(limit):
        buf[i] ^= 154
    return bytes(buf)


def unnpk(data: bytes) -> bytes:
    asdf_dn = "j2h56ogodh3se"
    asdf_dt = "=dziaq."
    asdf_df = "|os=5v7!\"-234"
    asdf_tm = asdf_dn * 4 + (asdf_dt + asdf_dn + asdf_df) * 5 + "!" + "#" + asdf_dt * 7 + asdf_df * 2 + "*" + "&" + "'"
    rotor = rotor_compat.newrotor(asdf_tm)
    data = _reverse_bytes(data)
    data = zlib.compress(data)
    data = rotor.encrypt(data)
    return data


def main():
    parser = argparse.ArgumentParser(description="unnpk tool")
    parser.add_argument("INPUT_NAME", help="input file")
    args = parser.parse_args()
    input_file = args.INPUT_NAME
    data = unnpk(open(input_file, "rb").read())
    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    main()
