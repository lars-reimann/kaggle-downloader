import argparse
import json
import os
from io import TextIOWrapper
from pathlib import Path

import kaggle.rest
import nbformat
from nbconvert import PythonExporter

from kaggle_downloader import KaggleDownloader


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch data from Kaggle."
    )
    subparsers = parser.add_subparsers(dest="command")

    # competitions command
    competitions_parser = subparsers.add_parser(
        "competitions",
        help="Fetch competitions."
    )
    competitions_parser.add_argument(
        "-o", "--out",
        help="Output file.",
        type=Path,
        required=True)

    # kernels command
    kernels_parser = subparsers.add_parser(
        "kernels",
        help="Fetch kernels for a list of competitions."
    )
    kernels_parser.add_argument(
        "-c", "--competitions",
        help="JSON file with list of competitions.",
        type=argparse.FileType("r"),
        required=True
    )
    kernels_parser.add_argument(
        "-e", "--exclude",
        help="JSON file with list of competitions to exclude. Gets updated with competitions as they are processed.",
        type=argparse.FileType("r"),
        required=True
    )
    kernels_parser.add_argument(
        "-o", "--out",
        help="Output directory.",
        type=Path,
        required=True
    )

    # notebooks command
    notebooks_parser = subparsers.add_parser(
        "notebooks",
        help="Fetch notebooks for a list of kernels."
    )
    notebooks_parser.add_argument(
        "-k", "--kernels",
        help="Directory with JSON files containing a list of kernels",
        type=Path,
        required=True
    )
    notebooks_parser.add_argument(
        "-e", "--exclude",
        help="JSON file with list of kernel to exclude. Gets updated with kernels as they are processed.",
        type=argparse.FileType("r"),
        required=True
    )
    notebooks_parser.add_argument(
        "-o", "--out",
        help="Output directory.",
        type=Path,
        required=True
    )

    return parser.parse_args()


def export_competitions(out_file: Path):
    client = KaggleDownloader()

    out_file.parent.mkdir(parents=True, exist_ok=True)

    with out_file.open("w") as f:
        json.dump(client.fetch_competition_refs(), f, indent=4)


def export_kernels(comp_file: TextIOWrapper, exclude_file: TextIOWrapper, out_dir: Path):
    client = KaggleDownloader()

    # Load competition refs
    with comp_file:
        competition_refs: list[str] = json.load(comp_file)

    # Load excluded competition refs
    with exclude_file:
        try:
            excluded_refs: list[str] = json.load(exclude_file)
        except json.decoder.JSONDecodeError:
            excluded_refs: list[str] = []

    # Write kernel refs
    out_dir.mkdir(parents=True, exist_ok=True)

    relevant_refs = set(competition_refs) - set(excluded_refs)
    for index, competition_ref in enumerate(relevant_refs):
        print(f"Working on competition {competition_ref} ({index + 1}/{len(relevant_refs)})")

        kernel_refs = client.fetch_kernel_refs(competition_ref)

        if len(kernel_refs) > 0:
            with out_dir.joinpath(f"{competition_ref}.json").open("w") as f:
                json.dump(kernel_refs, f, indent=4)

        excluded_refs.append(competition_ref)
        with open(exclude_file.name, "w") as f:
            json.dump(excluded_refs, f, indent=4)


def export_notebooks(kernel_dir: Path, exclude_file: TextIOWrapper, out_dir: Path):
    client = KaggleDownloader()

    # Load kernel refs
    kernel_refs = _list_all_kernel_refs(kernel_dir)

    # Load excluded kernel refs
    with exclude_file:
        try:
            excluded_refs: list[str] = json.load(exclude_file)
        except json.decoder.JSONDecodeError:
            excluded_refs: list[str] = []

    # Write notebooks
    out_dir.mkdir(parents=True, exist_ok=True)

    relevant_refs = set(kernel_refs) - set(excluded_refs)
    for index, kernel_ref in enumerate(relevant_refs):

        try:
            print(
                f"Working on kernel {kernel_ref} ({index + 1}/{len(relevant_refs)})"
            )

            result = client.fetch_notebook(kernel_ref)

            metadata = result.get("metadata")
            blob = result.get("blob")

            if metadata is None:
                print("Skipping (missing metadata)")
            elif metadata.get("language") != "python":
                print(f"Skipping (kernel language {metadata.get('language')})")
            elif metadata.get("kernelType") != "script" and metadata.get("kernelType") != "notebook":
                print(f"Skipping (kernel type {metadata.get('kernelType')})")
            elif blob is None or blob.get("source") is None:
                print("Skipping (missing source)")
            else:

                # Export metadata
                with open(out_dir.joinpath(f"{kernel_ref.replace('/', '$$$')}.meta.json"), "w+", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=4)

                # Export Python code
                source = blob.get("source")
                if metadata.get("kernelType") == "script":
                    with open(out_dir.joinpath(f"{kernel_ref.replace('/', '$$$')}.py"), "w+", encoding="utf-8") as f:
                        f.write(source)
                elif metadata.get("kernelType") == "notebook":
                    with open(out_dir.joinpath(f"{kernel_ref.replace('/', '$$$')}.py"), "w+", encoding="utf-8") as f:
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
        except nbformat.validator.NotebookValidationError:
            print("Skipping (invalid notebook)")
        except nbformat.reader.NotJSONError:
            print("Skipping (invalid notebook)")
        except Exception as e:
            print(e)
            continue  # we don't exclude the package before investigating the issue further

        excluded_refs.append(kernel_ref)
        with open(exclude_file.name, "w") as f:
            json.dump(excluded_refs, f, indent=4)


def _list_all_kernel_refs(kernel_dir: Path) -> list[str]:
    result = []

    _, _, kernel_files = next(os.walk(kernel_dir))
    for file in kernel_files:
        with open(kernel_dir.joinpath(file), "r") as f:
            try:
                result += json.load(f)
            except json.decoder.JSONDecodeError:
                print(f"Could not read {file}.")

    return result


if __name__ == "__main__":
    args = get_args()

    if args.command == "competitions":
        export_competitions(args.out)
    elif args.command == "kernels":
        export_kernels(args.competitions, args.exclude, args.out)
    elif args.command == "notebooks":
        export_notebooks(args.kernels, args.exclude, args.out)