#!/usr/bin/env python3
import os
from argparse import ArgumentParser
from shutil import unpack_archive, rmtree
from subprocess import run
from pathlib import Path
from os import mkdir, _exit
from urllib import request, error


def extract_deb(deb_file: Path, target: Path) -> None:
    data_file = Path("data.tar.xz")
    run(["ar", "x", deb_file, str(data_file)], check=True)
    unpack_archive(data_file, extract_dir=target)
    data_file.unlink()


def unstrip_debs(binary: Path, dbgsym: Path, output_dir: str) -> None:
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
            res = run(["eu-unstrip", "-n", "-e", str(bin)],
                      capture_output=True, text=True)
            if str(bin) not in res.stdout:
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
            run(["eu-unstrip", str(bin), str(dbg), "-o", str(temp_path / bin.name)],
                check=True)

    rmtree(bin_p)
    rmtree(dbg_p)
    create_sample_structure(str(temp_path), output_dir)
    rmtree(temp_path)


def download_pkg(name: str) -> tuple[Path, Path]:
    # this only works if local system is target OS :/
    # run(["apt-get", "download", name], check=True)
    # run(["apt-get", "download", name + "-dbg"], check=True)

    # super quick and dirty apt download ^^
    repo_url = "http://ftp.de.debian.org/debian/pool/main/"
    name_comp = name.split("_")
    basename = name_comp[0].split("-")[0].removeprefix("lib")
    
    url_dir = repo_url + basename[0] + "/" + basename + "/"
    name_comp[0] += "-dbg"
    dbg_name = "_".join(name_comp)
    
    # print(f"downloading from: {url_dir + name}")
    # if the base package download fails, it's probably due to the string hackery above
    request.urlretrieve(url_dir + name, filename=name)
    try:
        request.urlretrieve(url_dir + dbg_name, filename=dbg_name)
    except error.HTTPError:
        print(f"Debugging symbols not found, exiting. ({dbg_name})")
        _exit(1)

    return(Path(name), Path(dbg_name))


def create_sample_structure(input_folder_path: str, output_folder_path: str) -> None:

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
    parser = ArgumentParser(description=
        "Downloads Debian packages, extracts binaries and adds debugging symbols.")
    parser.add_argument("package", help=
        "The full name of the debian package to be retrieved, including '.deb'.")
    parser.add_argument('output_dir',default="unstripped" ,nargs='?')

    args = parser.parse_args()
    binary, dbgsym = download_pkg(args.package)
    unstrip_debs(binary, dbgsym, args.output_dir)


if __name__ == "__main__":
    main()
