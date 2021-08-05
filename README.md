## Fetching competitions

```shell
python main.py competitions -o data/competitions.json
```

## Fetching kernels

```shell
python main.py kernels -c data/competitions.json -e data/excluded_competitions.json -o data/kernels
```

## Fetching notebooks

```shell
python main.py notebooks -k data/kernels -e data/excluded_kernels.json -o "D:\Kaggle Kernels"
```

# Convert notebook to Python

jupyter nbconvert --to script [YOUR_NOTEBOOK].ipynb

jupyter nbconvert --to script \*.ipynb (converts everything)

# Analyze callgraph

pycg --product sklearn test.py
(does product do anything?)
