# kaggle-downloader

A wrapper around the Kaggle CLI to download multiple kernels at once.

## Installation

1. Grab the latest release of [Python](https://www.python.org/downloads/release).
2. Install this tool with `pip install kaggle-downloader`.
3. Follow the steps from the [Kaggle API documentation](https://github.com/Kaggle/kaggle-api#api-credentials) to create an API token. We never access this directly but let the official Kaggle API take care of authentication.

## Usage

```text
usage: kaggle-downloader [-h] {competition-refs,kernel-refs,kernels} ...

Download kernels from Kaggle.

positional arguments:
  {competition-refs,kernel-refs,kernels}
    competition-refs    Fetch competition references.
    kernel-refs         Fetch kernel references for a list of competition references.
    kernels             Fetch kernels for a list of kernel references.

optional arguments:
  -h, --help            show this help message and exit
```

Getting to the actual kernels takes three steps:
1. Get a list of references to competitions:
    ```text
    usage: kaggle-downloader competition-refs [-h] -o OUT

    optional arguments:
      -h, --help         show this help message and exit
      -o OUT, --out OUT  Output file.
    ```
2. Get a list of references to kernels:
    ```text
    usage: kaggle-downloader kernel-refs [-h] -c COMPETITIONS -e EXCLUDE -o OUT

    optional arguments:
      -h, --help            show this help message and exit
      -c COMPETITIONS, --competitions COMPETITIONS
                            File with list of competitions references.
      -e EXCLUDE, --exclude EXCLUDE
                            File with list of competitions references to exclude. Gets updated with competitions as they are processed.
      -o OUT, --out OUT     Output directory.
    ```
3. Get kernels themselves:
    ```text
    usage: kaggle-downloader kernels [-h] -k KERNELS -e EXCLUDE -o OUT

    optional arguments:
      -h, --help            show this help message and exit
      -k KERNELS, --kernels KERNELS
                            Directory with files containing a list of kernel references.
      -e EXCLUDE, --exclude EXCLUDE
                            File with list of kernel references to exclude. Gets updated with kernels as they are processed.
      -o OUT, --out OUT     Output directory.

    ```


### Example usage

```bash
# Step 1:
kaggle-downloader competition-refs -o data/competition-refs.txt

# Step 2:
kaggle-downloader kernel-refs -c data/competition-refs.txt -e data/excluded-competition-refs.txt -o data/kernel-refs

# Step 3:
kaggle-downloader kernels -k data/kernel-refs -e data/excluded-kernel-refs.txt -o data/kernels
```

## For developers

1. Grab the latest release of [Python](https://www.python.org/downloads/release).
2. Install [poetry](https://python-poetry.org/).
3. Run `poetry install` in the root of the repository.
4. Set the Python interpreter in your IDE to the virtual environment that was created.
