# ninetysix
A general package for tidying, annotating, and analyzing 96-well plate data.

### Note: This is a work in progress, and not yet ready for major release or use. 

A few functionalities (the `Plate()` class, generally, and `parsers.well_regex()`) are functional and usable, but not to their full extent. An intial release and push to PyPI will be made once all basic functionality is included.

## Purpose
`ninetysix` provides a method of combining well-value data pairs and efficiently adding additional information (controls, conditions) and processing and visualizing the results, writing out complete and informative experimental results as `.csv` files and plots.

## Technical overview
`ninetysix`'s main functionality is the `Plate` class.

### Data input
The `Plate` class minimally takes data in the form of ordered well-value pairs and returns a `pandas DataFrame`. The data can be passed as two separate arrays using the keyword arguments (kwarg) `wells=` and `values=`, or passed as an ordered `numpy.ndarray` or an array of well-value tuples with the kwarg `data=`. The name of the value can be specified with the kwarg `values=`. The `data` kwarg also takes `pandas DataFrame`s with minimally the columns `well` and `value`, or value as a named column specified by either being the last column index (`df.columns[-1]`) or via the `values=` kwarg. Other columns will be returned in the final output and mostly ignored until further analysis. Additionally, `row` and `column` columns will be returned in the final tidy `DataFrame` for downstream analysis.

### Annotation via `assign_wells` kwarg or method.
You can quickly annotate the exact condition of each well in one of two primary ways:

#### Nested dictionary:
Passing a nested dictionary to `assign_wells` will perform a flexible dictionary mapping that uses the outermost keys to create a new column with that key's name and the corresponding inner dictionary to annotate the wells with a corresponding value. Keys in the inner dictionaries are the wells used to assign the condition while the values are the condition values that are returned in within the `DataFrame`.  The keys support simple `regex`, such as `'[A-E][1-2]'` to specify `['A1', 'A2', 'B1', ..., 'E1', 'E2']`, or `'[A,C-E]1'` to specify (`['A1', 'C1', 'D1', 'E1']`), and combinations thereof.

(Coming soon: setting a default value so as to not have to specify all wells.)

#### Excel mapping file:
(Coming soon.)
The takes an excel spreadsheet that has been set up and filled out as shown in the `mapping.xlsx` file in `templates/`. Within a well, a condition can be specified as `name, value` and is expected to be of respective types `str, float/int`. For example, a simple condition might be `reactant, concentration` and defined as `indole (mM), 20` within a subset of wells. All wells that match this condition will then be annotated with this information in the returned `DataFrame`.

### `Plate` methods/support classes
#### Processing
(Coming soon.)
Numerous methods are available to process the data such that a new value column is returns that may better represent the results of your experiment. These can be seen in the examples.

#### Visualization
(Coming soon.)
Many visualizations are provided, such as heatmap-type plots, general ranking/retention of function plots, bar/line plots with the datapoints overlaid for replicates, all with the ability to encode different columns in your data set by some other dimension (e.g., by color, or shape). This relies on [`Holoviews`](http://holoviews.org/)/[`bokeh`](https://docs.bokeh.org/en/latest/) and for all intents and purposes is a wrapper for `Holoviews` streamlined for this form of data. If a form of visualization is not available in this package, you may consider either raising an issue to ask for it or learning `Holoviews` and creating the visualization yourself, as this will be more flexible.