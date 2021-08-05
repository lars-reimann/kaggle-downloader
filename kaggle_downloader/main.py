import argparse
import json
import os
from io import TextIOWrapper
from pathlib import Path
from typing import TextIO

import kaggle.rest
import nbformat
from nbconvert import PythonExporter

from .kaggle_downloader import KaggleDownloader


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download kernels from Kaggle.")
    subparsers = parser.add_subparsers(dest="command")

    # competition-refs command
    competition_refs_parser = subparsers.add_parser(
        "competition-refs", help="Fetch competition references."
    )
    competition_refs_parser.add_argument(
        "-o", "--out", help="Output file.", type=Path, required=True
    )

    # kernel-refs command
    kernel_refs_parser = subparsers.add_parser(
        "kernel-refs",
        help="Fetch kernel references for a list of competition references.",
    )
    kernel_refs_parser.add_argument(
        "-c",
        "--competitions",
        help="JSON file with list of competitions.",
        type=argparse.FileType("r"),
        required=True,
    )
    kernel_refs_parser.add_argument(
        "-e",
        "--exclude",
        help="JSON file with list of competitions to exclude. Gets updated with competitions as they are processed.",
        type=Path,
        required=True,
    )
    kernel_refs_parser.add_argument(
        "-o", "--out", help="Output directory.", type=Path, required=True
    )

    # kernels command
    kernels_parser = subparsers.add_parser(
        "kernels", help="Fetch kernels for a list of kernel references."
    )
    kernels_parser.add_argument(
        "-k",
        "--kernels",
        help="Directory with JSON files containing a list of kernels",
        type=Path,
        required=True,
    )
    kernels_parser.add_argument(
        "-e",
        "--exclude",
        help="JSON file with list of kernel to exclude. Gets updated with kernels as they are processed.",
        type=Path,
        required=True,
    )
    kernels_parser.add_argument(
        "-o", "--out", help="Output directory.", type=Path, required=True
    )

    return parser.parse_args()


def export_competition_refs(out_file: Path):
    downloader = KaggleDownloader()

    out_file.parent.mkdir(parents=True, exist_ok=True)

    with out_file.open("w") as f:
        _write_lines(f, downloader.fetch_competition_refs())


def export_kernel_refs(comp_file: TextIOWrapper, exclude_file: Path, out_dir: Path):
    downloader = KaggleDownloader()

    # Load competition refs
    with comp_file:
        competition_refs = _read_lines(comp_file)

    # Load excluded competition refs
    try:
        with exclude_file.open("r") as f:
            excluded_refs = _read_lines(f)
    except FileNotFoundError:
        excluded_refs = []

    # Write kernel refs
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    relevant_refs = set(competition_refs) - set(excluded_refs)
    for index, competition_ref in enumerate(relevant_refs):
        try:
            print(
                f"Working on competition {competition_ref} ({index + 1}/{len(relevant_refs)})"
            )

            kernel_refs = downloader.fetch_kernel_refs(competition_ref)

            if len(kernel_refs) > 0:
                with out_dir.joinpath(f"{competition_ref}.txt").open("w") as f:
                    _write_lines(f, kernel_refs)
            else:
                print("Skipping (no associated kernels)")

        except kaggle.rest.ApiException as e:
            if e.status == 403:
                print("Skipping (forbidden)")
            elif e.status == 404:
                print("Skipping (not found)")
            else:
                print(e)
                continue  # we don't exclude the package since the Kaggle endpoint might just be temporarily unavailable

        excluded_refs.append(competition_ref)
        with exclude_file.open("a") as f:
            f.write(f"{competition_ref}\n")


def export_kernels(kernel_dir: Path, exclude_file: Path, out_dir: Path):
    client = KaggleDownloader()

    # Load kernel refs
    kernel_refs = _list_all_kernel_refs(kernel_dir)

    # Load excluded kernel refs
    try:
        with exclude_file.open("r") as f:
            excluded_refs = _read_lines(f)
    except FileNotFoundError:
        excluded_refs = []

    # Write notebooks
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    relevant_refs = set(kernel_refs) - set(excluded_refs)
    for index, kernel_ref in enumerate(relevant_refs):
        try:
            print(f"Working on kernel {kernel_ref} ({index + 1}/{len(relevant_refs)})")

            result = client.fetch_notebook(kernel_ref)

            metadata = result.get("metadata")
            blob = result.get("blob")

            if metadata is None:
                print("Skipping (missing metadata)")
            elif metadata.get("language") != "python":
                print(f"Skipping (kernel language {metadata.get('language')})")
            elif (
                metadata.get("kernelType") != "script"
                and metadata.get("kernelType") != "notebook"
            ):
                print(f"Skipping (kernel type {metadata.get('kernelType')})")
            elif blob is None or blob.get("source") is None:
                print("Skipping (missing source)")
            elif blob.get("source") == "":
                print("Skipping (empty source)")
            else:

                # Export metadata
                with open(
                    out_dir.joinpath(f"{kernel_ref.replace('/', '$$$')}.meta.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(metadata, f, indent=4)

                # Export Python code
                source = blob.get("source")
                if metadata.get("kernelType") == "script":
                    with open(
                        out_dir.joinpath(f"{kernel_ref.replace('/', '$$$')}.py"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(source)
                elif metadata.get("kernelType") == "notebook":
                    with open(
                        out_dir.joinpath(f"{kernel_ref.replace('/', '$$$')}.py"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        nb = nbformat.reads(str(source), nbformat.NO_CONVERT)
                        python, _ = PythonExporter().from_notebook_node(nb)
                        f.writelines(python)
        except kaggle.rest.ApiException as e:
            if e.status == 403:
                print("Skipping (forbidden)")
            elif e.status == 404:
                print("Skipping (not found)")
            else:
                print(e)
                continue  # we don't exclude the package since the Kaggle endpoint might just be temporarily unavailable
        except (
            nbformat.validator.NotebookValidationError,
            nbformat.reader.NotJSONError,
        ):
            print("Skipping (invalid notebook)")
        except Exception as e:
            print(e)
            continue  # we don't exclude the package before investigating the issue further

        excluded_refs.append(kernel_ref)
        with exclude_file.open("a") as f:
            f.write(f"{kernel_ref}\n")


def _write_lines(f: TextIO, lines: list[str]) -> None:
    f.writelines(f"{it}\n" for it in lines)


def _read_lines(f: TextIO) -> list[str]:
    return [it.strip() for it in f.readlines() if it != ""]


def _list_all_kernel_refs(kernel_dir: Path) -> list[str]:
    result: list[str] = []

    _, _, kernel_files = next(os.walk(kernel_dir))
    for file in kernel_files:
        with open(kernel_dir.joinpath(file), "r") as f:
            try:
                result += _read_lines(f)
            except FileNotFoundError:
                print(f"Could not read {file}.")

    return result


def main() -> None:
    args = get_args()

    if args.command == "competition-refs":
        export_competition_refs(args.out)
    elif args.command == "kernel-refs":
        export_kernel_refs(args.competitions, args.exclude, args.out)
    elif args.command == "kernels":
        export_kernels(args.kernels, args.exclude, args.out)
