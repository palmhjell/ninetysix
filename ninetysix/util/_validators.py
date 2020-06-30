import numpy as np
import pandas as pd

from ..parsers import well_regex, pad


def check_inputs(Plate):
    """Checks that all inputs are provided correctly.

    Returns True if all tests pass.
    """
    
    # Well-value pairs
    if Plate.wells:

        if Plate.values is None:
            raise ValueError(
                "kwarg 'values' must be specified if 'wells' is not None."
            )

        if len(Plate.wells) != len(Plate.values):
            raise ValueError(
                "Arrays for 'wells' and 'values' are not the same length."
            )

        # Check that all wells are string values
        bad_types = [type(well) for well in Plate.wells if type(well) != str]

        if bad_types:
            raise TypeError(
                f"Well values must be of type string, found: {set(bad_types)}"
            )
    
    # Data (list of lists/tuples or DataFrame/dict)
    if Plate.data is not None:

        if Plate.wells is not None:
            raise ValueError(
                "kwarg 'wells' cannot be specified if 'data' is not None."
            )

        if Plate.values:
            if type(Plate.values) is not str:
                raise TypeError(
                    "kwarg 'values' must take a string argument "\
                    "(name of the value) if 'data' is not None."
                )

        df = None
        if type(Plate.data) == type(pd.DataFrame()):
            df = Plate.data

        if df is not None:
            well_cols = [col for col in df.columns if col.lower() == 'well']
            if 'well' not in well_cols:
                raise ValueError(
                    "No 'well' value found in your DataFrame columns."
                )
            if len(well_cols) != 1:
                raise ValueError(
                    "Multiple 'well' columns detected in your data."
                )

            well_col = well_cols[0]
            if (Plate.value_name is None) & (well_col == df.columns[-1]):
                raise ValueError(
                    "Your final column is assumed to be your value column,"
                    "but found column related to well."
                )

            bad_types = [type(well) for well in df[well_col] if type(well) != str]

            if bad_types:
                raise TypeError(
                    f"Well values must be of type string, found: {set(bad_types)}"
                )

            if ((Plate.value_name is not None) &
                (Plate.value_name not in df.columns)):
                raise ValueError(
                    f"'{Plate.value_name}' not present in your data, "\
                    f"options are: {list(df.columns)}"
                )

    return True

def check_annotations(Plate, annotations):
    """Checks that all annotations are specified correctly,
    especially in the context of the Plate input.

    Returns annotation type if all tests pass.
    """
    if isinstance(annotations, dict):

        # Check keys
        acceptable_kwargs = ('default', 'standard', 'else', 'other')
        rows = list('ABCDEFGHIJKLMNOP')
        cols = [str(i) for i in range(1, 25)]
        acceptable_wells = [row+col for row in rows for col in cols]
        acceptable_wells += [pad(row+col) for row in rows for col in cols]
        acceptable_wells = set(acceptable_wells)
        
        for column in annotations.keys():
            working_annotations = well_regex(annotations[column],
                                             padded=Plate.zero_padding)
            
            nonwell_keys = set(working_annotations.keys()) - acceptable_wells
            
            if len(nonwell_keys) == 0:
                continue

            if len(nonwell_keys) > 1:
                raise ValueError(
                    f"Multiple non-well keys found in '{column}' dict. "\
                    f'Provide only one of {acceptable_kwargs}.'
                )

            # Check identified key as default key
            default_key = list(nonwell_keys)[0]

            if default_key.lower() not in acceptable_kwargs:
                raise ValueError(
                    f"Non-well key ('{default_key}') found in '{column}' dict "\
                    f'that does not match acceptable default arguments '
                    f'({acceptable_kwargs}).'
                )
        # Assign type if passes
        annotation_type = dict
    
    elif isinstance(annotations, str):

        # TODO(check stuff)
        
        # Assign type if passes
        annotation_type = 'excel'

    else:
        raise NotImplementedError(
            'Only dictionary and excel-based mapping annotations are '
            'currently supported.'
        )

    return annotation_type

def check_df_col(Plate, column, name=None):
    """Checks for the presence of a column (or columns) in a tidy
    DataFrame with an informative error message. Passes silently,
    otherwise raises error.
    """
    if name is None:
        error_message = f"The value '{column}' is not present in any of your data's columns."
    else:
        error_message = f"Your {name} '{column}' is not present in any of your data's columns."
    error_message += "\nYou may be looking for:\n  " + \
        str(list(Plate.df.columns))

    if column not in Plate.df.columns:
        raise ValueError(error_message)
