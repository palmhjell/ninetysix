# `ninetysix.templates`
## Nested dictionaries
### Example:
```python
assignments = {
    'controls': {
        'default': 'experiment',
        '[A-D]12': 'positive',
        'E12': 'blank',
        '[F-H]12': 'negative',
    }
}
```
This would return a new column named `controls` with values of `positive` for wells `A12, B12, C12, D12`, `blank` for well `E12`, and `negative` for wells `F12, G12, H12`. All other wells would be assigned `experiment`, the default value.

Note: this format supports assignment for 384-well plates as well (A1 through P24).

## Excel template
`assignment_mapping_template.xlsx` provides a template for assigning wells in a 96-well plate format.

Rename each column (e.g., all `column_1`s) to your condition and provide the value for each well. Empty wells will be given a value of `None`.

As given, up to three new condition columns can be provided, but if no values are given whatsoever for a column it will be dropped in the final output. You are not limited to only three; additional conditions can be added by inserting new rows in the template spreadsheet. You may also remove columns if this is more convenient for you. Indexing occurs relative to the provided `A, B, C, ... , H` indices and the space between them.