<img src="docs/assets/ninetysix_1.png" alt="logo" width="250"/>

# ninetysix
A general package for annotating, processing, and visualizing 96-well* plate data.

(*_n_-well, really.)

## Purpose
`ninetysix` provides a method of combining well-value data pairs and efficiently adding additional information (e.g., controls, well conditions) and processing and visualizing the results.

This primarily works via the `Plate` class, but visualization tools are available for `pandas DataFrame` objects as well through `ninetysix.viz`.

Visit the [`ninetysix` GitHub Pages site](https://palmhjell.github.io/ninetysix/) for detailed and interactive examples.

## Install
```
pip install ninetysix
```
Although `jupyter lab` is not a strict dependency for `ninetysix`, much of the visualization functionality benefits from being run in a notebook. If your `jupyter lab` and other packages are up to date, the above `pip` install should suffice. If you have issues, the following conda environment should work:
```
# Create the environment with python and jupyterlab installed
conda create -n ns_env python jupyterlab

# Activate the environment
conda activate ns_env

# Install ninetysix and its dependencies
pip install ninetysix

# Open jupyter lab
jupyter lab
```

## Features
### `ninetysix.Plate`
The heart of this package, a `Plate` object contains three major groups to describe a well:

`locations`, `annotations`, and `values`,

which are always arrayed in that order.

#### `Plate` performs value-oriented operations
The 'most important' (or perhaps 'most relevant') `value` is set as the right-most column in the data, which is automatically used in downstream processing and visualization unless explicitly overwritten, thus saving time needing to specify what data to use during exploratory data analysis.

New columns are assumed to be generic `annotations`, but can be moved to `locations` or `values` as desired to streamline your processing and analysis (see **Examples** below).

#### `Plate` uses the flexibility of the `pandas DataFrame`
`Plate` objects have nearly all methods available to a `DataFrame` (e.g., `merge`), but will return a `Plate` object when possible.

```python
>>> import ninetysix as ns
>>> import pandas as pd

>>> # Create Plate
>>> plate = ns.Plate('example_data.csv')

>>> # Create DataFrame with only row A and column 'plate'
>>> df = pd.DataFrame({
...     'well': [f'A{i}' for i in range(1, 13)],
...     'plate': 1
... })

>>> # Call `pd.merge` from Plate
>>> merged_plate = plate.merge(df)

>>> # Returned object is a Plate
>>> type(merged_plate)

ninetysix.plate.Plate
```
This new plate object will retain the same `locations`, `annotations`, and `values` attributes.

### `ninetysix.parsers.well_regex`
Dictionaries with key-value pairs that represent a single well and information about it are a powerful way to add information to a plate, but writing 96 key-value pairs is cumbersome. To alleviate this, `ninetysix` provides `well_regex` in the `parsers` module, which accepts well keys written in a simple regex form and expands them.

```python
>>> from ninetysix.parsers import well_regex

>>> well_info = {
...     '[A-C]10': 'control',
...     '[A,H][1,12]': 'empty',
... }

>>> well_regex(well_info)

{'A10': 'control',
 'B10': 'control',
 'C10': 'control',
 'A1': 'empty',
 'A12': 'empty',
 'H1': 'empty',
 'H12': 'empty'}
```

### `ninetysix.viz`
Quick access to scatter charts, plate heatmaps, and aggregated charts are available for both `Plate` and `DataFrame` objects, leveraging the information encoded in these objects to generate annotated visualizations.

These plots are based on the `holoviews` (http://holoviews.org/) package with the `bokeh` backend. The chart outputs of `viz` can be further tuned using the tools provided in these packages.

Plotting functions are available directly as `Plate` methods for an efficient workflow:

<img src="docs/assets/full_workup.png" alt="ex0" width="600"/>