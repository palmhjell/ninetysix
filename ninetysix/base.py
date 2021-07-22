"""
Standard functions for general data.

Many of these are added to Plate and other classes as methods with
default arguments.
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
    ...     'condition': [1, 1, 1, 1, 2, 2, 2, 2],
    ...     'value': [0.98, 1.02, 1.07, 0.95, 0.33, 0.20, 0.25, 0.27]
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


def aggregate_replicates(
    obj,
    variable=None,
    value=None,
    groupby=None,
    prefix='mean_',
):
    """Checks for the presence of replicates in the values of a dataset,
    given some experimental conditions. Returns True if the number of
    rows assigned to the given aggregation columns (variable+groupby)
    is greater than 1, indicating that replicates were performed.
    
    Parameters:
    -----------
    obj: ns.Plate or pd.DataFrame object
        If DataFrame and `value = None`, the final column is used as the
        value.
    variable: str, default None
        Name of column of data frame for the independent variable,
        indicating a specific experimental condition.
    value: str or list of str, default None
        Name of column(s) to normalize. 
    value: str, default None
        Name of column of data frame for the dependent variable,
        indicating an experimental observation. If no argument is given,
        uses value_name for Plate objects or the right-most column for 
        DataFrames.
    groupby: str or list of str, default None
        Column name or list of column names that indicates how the
        data set should be split.
    prefix: str, default 'mean_'
        The prefix for the new column of aggreagated values, if
        replicates is True.
    
    Returns:
    --------
    replicates: bool
        True if replicates are present.
    df: pd.DataFrame
        The DataFrame containing averaged 'variable'+'groupby' values,
        if replicates is True. Otherwise returns the original DataFrame.
        The aggregated data is in a new column named '{prefix}{value}'.

    Examples:
    ---------
    # Try to aggregate with 8 different variables (just ID)
    # returns False, input df
    >>> df = pd.DataFrame({
    ...     'id': [1, 2, 3, 4, 5, 6, 7, 8],
    ...     'condition': [1, 1, 1, 1, 2, 2, 2, 2],
    ...     'value': [0.98, 1.02, 1.07, 0.95, 0.33, 0.20, 0.25, 0.27]
    ... })
    >>> ns.aggregate_replicates(df, variable='id')
    (False,
        id      condition    value
    0   1       1            0.98
    1   2       1            1.02
    2   3       1            1.07
    3   4       1            0.95
    4   5       2            0.33
    5   6       2            0.20
    6   7       2            0.25
    7   8       2            0.27)

    # Aggreagte on 'condition', which contains two groups
    # returns True, df iwth aggregated column
    >>> ns.aggregate_replicates(df, variable='condition')
    (True,
        id      condition    value    mean_value
    0   1       1            0.98     1.0050
    1   2       1            1.02     1.0050
    2   3       1            1.07     1.0050
    3   4       1            0.95     1.0050
    4   5       2            0.33     0.2625
    5   6       2            0.20     0.2625
    6   7       2            0.25     0.2625
    7   8       2            0.27     0.2625

    # Aggregate on two groups, just passing groupby
    # returns True, aggregated df
    >>> df = pd.DataFrame({
    ...     'condition_1': [1, 1, 1, 1, 2, 2, 2, 2],
    ...     'condition_2': [True, True, False, False]*2,
    ...     'value': [0.98, 1.02, 1.07, 0.95, 0.33, 0.20, 0.25, 0.27]
    ... })
    >>> ns.aggregate_replicates(
    ...     df,
    ...     groupby=['condition_1', 'condition_2]
    ... )
    (True,
        condition_1 condition_2    value    mean_value
    1   1           True           1.02     1.000
    0   1           True           0.98     1.000
    2   1           False          1.07     1.010
    3   1           False          0.95     1.0010
    4   2           True           0.33     0.265
    5   2           True           0.20     0.265
    6   2           False          0.25     0.260
    7   2           False          0.27     0.260
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(obj)

    # Get value list ready
    if value is None:
        value = auto_value
    
    # Unpack the experimental conditions into a single list of arguments
    if not isinstance(groupby, (list, tuple)):
        groupby = [groupby]
    args = [elem for elem in (variable, *groupby) if elem is not None]

    # Get row counts to determine if there are replicates
    grouped = df.groupby(args)[value]
    counts = grouped.count()
    replicates = bool([True for count in counts if count > 1])

    # Average the values and return
    if replicates:
        df_mean = grouped.mean().reset_index()
        df_mean.columns = list(df_mean.columns[:-1]) + [f'{prefix}{value}']
        df = df.merge(df_mean)

    return replicates, df
