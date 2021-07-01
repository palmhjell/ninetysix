"""
Standard functions for general data.

These are added to Plate and other classes with default arguments.
"""

import numpy as np
import pandas as pd
from .parsers import _parse_data_obj
from .util import check_df_col


def normalize(
    obj,
    value=None,
    to=None,
    zero=None,
    groupby=None,
    # devs=False,
    prefix='normalized_',
):
    """Flexible scaling and translation of annotated data to help
    normalize and compare different experiments. Use `value` to choose
    the data to be normalized. Set `zero` to True to use the minimum
    of the data as an explicit 0 value (e.g., no negative values), or
    assign an annotation in a different column to be set to zero. The
    max of the data is set to 1, unless given an annotation to set to a
    value of 1. See kwargs below for more details.

    Parameters:
    -----------
    obj: ns.Plate or pd.DataFrame object
        If DataFrame and `value = None`, the final column is used as the
        value.
    value: str or list of str, default None
        Name of column(s) to normalize. If no argument is given, uses
        value_name for Plate objects or the right-most column for 
        DataFrames.
    to: str, default None
        Which group to set as the normal (1) value, following the form
        of the string '{column}={group}'.
    zero: str or bool, default None
        Which group to set as the zero value (if str) or to use the min
        of the data as zero (if False). If str, follows the same form as
        `to`, '{column}={group}'.
    groupby: str, default None
        Name of a column that contains group information, if multiple
        independent normalizations should be performed.
    prefix: str, default 'normalized_'
        Prefix used for the normalized column name(s).

    Examples:
    ---------
    # Normalize a single data column with no arguments
    >>> df = pd.DataFrame({
    ... 'condition': [1, 1, 1, 1, 2, 2, 2, 2],
    ... 'value': [0.98, 1.02, 1.07, 0.95, 0.33, 0.20, 0.25, 0.27]
    ... })
    >>> ns.normalize(df)
        condition    value    normalized_value
    0   1            0.98     0.915888
    1   1            1.02     0.953271 
    2   1            1.07     1.000000
    3   1            0.95     0.887850
    4   2            0.33     0.308411
    5   2            0.20     0.18916
    6   2            0.25     0.233645
    7   2            0.27     0.252336

    # Condition 1 is a positive control, condition 2 is a negative.
    >>> ns.normalize(
    ...     df,
    ...     to='condition=1',
    ...     zero='condition=2',
    ... )
        condition    value    normalized_value
    0   1            0.98     0.966330
    1   1            1.02     1.020202 
    2   1            1.07     1.087542
    3   1            0.95     0.925926
    4   2            0.33     0.090909
    5   2            0.20    -0.084175
    6   2            0.25    -0.016835
    7   2            0.27     0.010101
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(obj)

    # Get value list ready
    if value is None:
        value = auto_value
    if not isinstance(value, list):
        values = [value]
    else:
        values = value

    # Set up groups
    if not isinstance(groupby, (tuple, list)):
        groupby = [groupby]

    for group in groupby:
        check_df_col(df, group, name='groupby')

    # Group or create fake groupby object
    unique_dfs = (df.groupby(groupby) if groupby != [None]
                    else [(None, df.copy())])

    df_list = []
    # Iterate through each dataframe group
    for name, sub_df in unique_dfs:

        sub_df = sub_df.copy()

        # Iterate through each value
        for value in values:
            check_df_col(sub_df, value, name='value')

            norm_string = f'{prefix}{value}'

            # Set the zero val
            if zero == True:
                zero_val = sub_df[value].min()
            elif isinstance(zero, str):
                split = zero.split('=')
                if len(split) != 2:
                    raise ValueError(
                        f"'zero' value specified incorrectly, must be of the "\
                        "form '{column}={group}'."
                    )

                col, val = split

                # Check that col in columns
                check_df_col(sub_df, col, name='column')

                # Check that the given value is found in the column
                if val not in [str(i) for i in sub_df[col]]:
                    raise ValueError(
                        f"The value '{val}' is not a value in the column '{col}'."
                    )
                subset = [val == str(i) for i in sub_df[col]]
                zero_val = sub_df[subset][value].mean()
            elif zero is None or zero == False:
                zero_val = 0
            else:
                raise TypeError(
                    f"Type of 'zero' argument is incorrectly specified. Must be bool or string.")

            sub_df[norm_string] = sub_df[value] - zero_val

            # Set the one val
            if to is None:
                one_val = sub_df[norm_string].max()
            elif isinstance(to, str):
                split = to.split('=')
                if len(split) != 2:
                    raise ValueError(
                        f"'to' value specified incorrectly, must be of the "\
                        "form '{column}={value}'."
                    )

                col, val = split

                # Check that col in columns
                check_df_col(sub_df, col, name='column')

                # Check that the given value is found in the column
                if val not in [str(i) for i in sub_df[col]]:
                    raise ValueError(
                        f"The value '{val}' is not a value in the column '{col}'."
                    )
                subset = [val == str(i) for i in sub_df[col]]
                one_val = sub_df[subset][norm_string].mean()
            else:
                raise TypeError(
                    f"Type of 'to' argument is incorrectly specified. Must be bool or string.")

            sub_df[norm_string] = sub_df[norm_string] / one_val

        # After adding normalized values, store in df_list
        df_list.append(sub_df)

    # Once finished, concat together
    # Note: the index is preserved, and returns the data in the same
    # order as the input, even with groupby.
    return_df = pd.concat(df_list)

    return return_df
