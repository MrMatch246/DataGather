#!/usr/bin/env python3

from argparse import ArgumentParser
from shutil import unpack_archive, rmtree
from subprocess import run
from pathlib import Path
from os import mkdir


def extract_deb(filename: str, target: str) -> None:
    data_file = Path("data.tar.xz")
    run(["ar", "x", filename, str(data_file)], check=True)
    unpack_archive(data_file, extract_dir=target)
    data_file.unlink()


def unstrip_debs(binary: str, dbgsym: str) -> None:
    bin_p = Path("bin")
    dbg_p = Path("dbg")
    extract_deb(binary, bin_p)
    extract_deb(dbgsym, dbg_p)

    out_p = Path("unstripped")
    if not out_p.exists():
        mkdir(out_p)

    for bin in bin_p.glob("usr/bin/*"):
        if bin.is_file():
            # find debug hash
            res = run(["eu-unstrip", "-n", "-e", str(bin)], capture_output=True, text=True)
            if not str(bin) in res.stdout:
                # bin is probably not an ELF executable
                print(f"no build hash for {str(bin)}, skipping")
                continue

            # construct name
            hash = res.stdout.split()[1].split('@')[0]
            prefix = hash[0:2]
            dbg_file = hash[2:] + ".debug"
            del(hash)

            # actually unstrip
            dbg = dbg_p / "usr/lib/debug/.build-id" / prefix / dbg_file
            assert(dbg.exists())
            res = run(["eu-unstrip", str(bin), str(dbg), "-o", str(out_p / bin.name)], check=True)

    rmtree(bin_p)
    rmtree(dbg_p)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('binary_package')
    parser.add_argument('dbgsym_package')

    args = parser.parse_args()
    unstrip_debs(args.binary_package, args.dbgsym_package)


if __name__ == "__main__":
    main()
