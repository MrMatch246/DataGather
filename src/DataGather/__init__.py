#!/usr/bin/env python3
import os
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


def unstrip_debs(binary: str, dbgsym: str,output_dir :str) -> None:
    bin_p = Path("bin")
    dbg_p = Path("dbg")
    extract_deb(binary, bin_p)
    extract_deb(dbgsym, dbg_p)

    temp_path = Path("../../data/temp")
    if not temp_path.exists():
        mkdir(temp_path)

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
            res = run(["eu-unstrip", str(bin), str(dbg), "-o", str(temp_path / bin.name)], check=True)

    rmtree(bin_p)
    rmtree(dbg_p)
    create_sample_structure(str(temp_path), output_dir)
    rmtree(temp_path)



def create_sample_structure(input_folder_path: str, output_folder_path: str):

    if not os.path.exists(output_folder_path):
        os.mkdir(output_folder_path)
        os.mkdir(os.path.join(output_folder_path, "stripped"))
        os.mkdir(os.path.join(output_folder_path, "original"))
        os.mkdir(os.path.join(output_folder_path, "no_propagation"))
        os.system(f"cp {input_folder_path}/* {output_folder_path}/original")
        os.system(f"cp {input_folder_path}/* {output_folder_path}/stripped")
        os.system(f"cp {input_folder_path}/* {output_folder_path}/no_propagation")

        for binary in os.listdir(os.path.join(output_folder_path, "stripped")):
            binary_path = os.path.join(output_folder_path, 'stripped', binary)
            os.system(f"strip {binary_path}")


        for binary in os.listdir(os.path.join(output_folder_path, "no_propagation")):
            binary_path = os.path.join(output_folder_path, 'no_propagation', binary)
            os.system(f"strip {binary_path}")
            os.system(f"mv {binary_path} {binary_path}_no_propagation")

        for binary in os.listdir(os.path.join(output_folder_path, "original")):
            binary_path = os.path.join(output_folder_path, 'original', binary)
            os.system(f"mv {binary_path} {binary_path}_original")


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('binary_package')
    parser.add_argument('dbgsym_package')
    parser.add_argument('output_dir',default="unstripped" ,nargs='?')

    args = parser.parse_args()
    unstrip_debs(args.binary_package, args.dbgsym_package, args.output_dir)


if __name__ == "__main__":
    main()
