import pandas as pd

from ..parsers import well_regex, pad


def check_inputs(Plate):
    """Checks that all inputs are provided correctly.

    Returns True if all tests pass.
    """
    df = None
    if isinstance(Plate.data, pd.DataFrame):
        df = Plate.data

    if df is not None:
        message = 'column'

    elif isinstance(Plate.data, dict):
        df = pd.DataFrame(Plate.data)
        message = 'key'

    elif isinstance(Plate.data, list):
        df = pd.DataFrame(
            data=Plate.data,
            columns=['well', Plate.value_name]
        )

    well_cols = [col for col in df.columns if str(col).lower() == 'well']
    if 'well' not in [well.lower() for well in well_cols]:
        raise ValueError(
            f"No 'well' value found in your {message}s."
        )
    if len(well_cols) != 1:
        raise ValueError(
            "Multiple 'well' columns detected in your data."
        )

    well_col = well_cols[0]
    if (Plate.value_name is None) & (well_col == df.columns[-1]):
        raise ValueError(
            "Your final {message} is assumed to be your value {message},"
            "but found {message} related to well."
        )

    bad_types = [type(well) for well in df[well_col]
                 if not isinstance(well, str)]

    if bad_types:
        raise TypeError(
            f"Well values must be of type string, found: {set(bad_types)}"
        )

    if Plate.value_name is not None:
        if df.columns[-1] is not None and Plate.value_name not in df.columns:
            raise ValueError(
                f"'{Plate.value_name}' not present in your data, "\
                f"options are: {list(df.columns)}"
            )

    # TODO: Add row and column check?

    return True


def check_annotations(Plate, annotations):
    """Checks that all annotations are specified correctly,
    especially in the context of the Plate input.

    Returns annotation type if all tests pass.
    """
    if isinstance(annotations, dict):
        # Check for nested dict
        for column in annotations:
            if not isinstance(annotations[column], dict):
                raise ValueError(
                    "Annotations should be a nested dictionary, following the"\
                    " form {new_column_name: {wells: annotation}}. Your "\
                    "input did not contain a nested dictionary."
                )

        # Check keys
        acceptable_kwargs = ('default', 'standard', 'else', 'other')
        rows = list('ABCDEFGHIJKLMNOP')
        cols = [str(i) for i in range(1, 25)]
        acceptable_wells = [row+col for row in rows for col in cols]
        acceptable_wells += [pad(row+col) for row in rows for col in cols]
        acceptable_wells = set(acceptable_wells)
        
        for column in annotations:
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


def check_df_col(df, column, name=None):
    """Checks for the presence of a column (or columns) in a tidy
    DataFrame with an informative error message. Passes silently,
    otherwise raises error.
    """
    if column is None:
        return
    
    if name is None:
        error_message = f"The value '{column}' is not present in any of your data's columns."
    else:
        error_message = f"Your {name} '{column}' is not present in any of your data's columns."
    error_message += "\nYou may be looking for:\n  " + \
        str(list(df.columns))

    if column not in df.columns:
        raise ValueError(error_message)
