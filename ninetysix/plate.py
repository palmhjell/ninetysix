import numpy as np
import pandas as pd

from functools import wraps

from .checkers import check_inputs, check_assignments
from .parsers import well_regex


class Plate():
    """Need a comprehensive docstring here.
    """

    def __init__(
        self,
        data=None,
        wells=None,
        values=None,
        value_name=None,
        assign_wells=None,
        lowercase=None,
        pandas_attrs=True,
    ):

        # Initial setup
        self.data = data
        self.wells = wells
        self.values = values
        self._value_name = value_name
        self._passed = check_inputs(self)
        self._pandas_attrs = pandas_attrs
        
        # For easier unit testing: do only when passing
        if self._passed:
            # Determine case
            self._lowercase = lowercase
            self._well_lowercase = self._get_well_case()

            # Make dataframe
            self.df = self._make_df()
            if self._pandas_attrs:
                _make_pandas_attrs(self)

        # Determine if zero-padded
        self._zero_padded = self._get_zero_padding()

        # Annotate
        if assign_wells is not None:
            self.assignments = assign_wells
            self._assignment_pass = check_assignments(self)
            self.assign_wells()

    def __getitem__(self, key):
        return self.df[key]

    def __setitem__(self, key, value):
        self.df[key] = value

    def _repr_html_(self):
        return self.df._repr_html_()

    # Values
    @property
    def value_name(self):
        """Sets value name from 'value_name', 'values', or sets to 'value'."""
        if (self._value_name is None) & (type(self.values) == str):
            self._value_name = self.values
        elif self._value_name is None:
            self._value_name = 'value'
        return self._value_name

    def _move_values(self, df=None):
        """Moves values to -1 index"""
        if df is None:
            df = self.df
        values = df[self.value_name]
        del df[self.value_name]
        df[self.value_name] = values
        return df

    # Cases
    @property
    def lowercase(self):
        """Highest priority case-setter for new columns."""
        return self._lowercase

    def _get_well_case(self):
        """After self._passing is True, determines well case."""
        if self.data is None:
            self._well_lowercase = True
        elif ((type(self.data) != type(pd.DataFrame())) and
              (type(self.data) != dict)):
            self._well_lowercase = True
        else:
            if type(self.data) == type(pd.DataFrame()):
                cols = self.data.columns
            if type(self.data) == dict:
                cols = self.data.keys()
            well = [col for col in cols if col.lower() == 'well'][0]
            case = well[0]
            self._well_lowercase = True if case == case.lower() else False
        return self._well_lowercase

    def _standardize_case(self, string):
        """Standardizes case of new columns based on self.case/well_case."""
        if self.lowercase is not None:
            lowercase = str.lower if self.lowercase else str.capitalize
        else:
            lowercase = self._well_lowercase
        
        case = str.lower if lowercase else str.capitalize
        
        return case(string)
    
    def _make_df(self):
        """Given passing inputs, sets up the initial DataFrame."""
        # Use given case
        well_string = self._standardize_case('well')

        if type(self.data) == type(pd.DataFrame()):
            df = self.data
        elif type(self.data) == dict:
            df = pd.DataFrame(self.data)
        elif type(self.values) == str:
            df = pd.DataFrame(data=self.data, columns=[well_string, self.value_name])
        else:
            if self.wells is not None:
                data = zip(self.wells, self.values)
            else:
                data = self.data
            df = pd.DataFrame(data=data, columns=[well_string, self.value_name])

        # Standardize 0 and -1 index for well and value
        wells = df[well_string]
        del df[well_string]
        df.insert(0, well_string, wells)

        if self.value_name is None:
            self._value_name = df.columns[-1]
        else:
            df = self._move_values(df)

        # Add rows and columns
        rows, cols = zip(*df[well_string].apply(
            lambda well: (well[0], int(well[1:]))
        ))

        for val, name in zip((cols, rows), ('column', 'row')):
            name = self._standardize_case(name)
            df.insert(1, name, val)

        return df

    def _get_zero_padding(self):
        """Determines if well inputs are zero-padded."""
        # Assume False, switch conditionally
        padded = False
        well_col = self._standardize_case('well')
        wells = self.df[well_col]
        
        for well in wells:

            # Check int conversion
            col = well[1:]
            if col != str(int(col)):
                padded = True

            # Check lengths
            if len(well) < 3:
                padded = False

        return padded

    def assign_wells(self, assignments=None):
        """Takes either a nested dictionary or standardized excel
        spreadsheet (see ninetysix/templates) to assign new columns
        in the output DataFrame that provide addition information 
        about the contents or conditions of each well in the Plate.
        """
        if assignments is None:
            assignments = self.assignments

        assignment_type = type(assignments)
        if assignment_type == dict:
            # Unpack dictionary
            assignments = well_regex(assignments, padded=self._zero_padded)

            # Make new columns
            for column in assignments.keys():
                wells = self.df[self._standardize_case('well')]
                self.df[column] = wells.map(assignments[column].get)

        self._move_values()

        return self

def _get_pandas_attrs(Plate, attr_name):
    """Creates wrappers for pandas functions to Plate.df"""
    attr = getattr(pd.DataFrame, attr_name)
    if callable(attr):
        @wraps(attr)
        def wrapper(*args, **kwargs):
            return attr(Plate.df, *args, **kwargs)
        attr_pair = (attr_name, wrapper)
    else:
        attr = getattr(Plate.df, attr_name)
        attr_pair = (attr_name, attr)

    return attr_pair

def _make_pandas_attrs(Plate):
    """Assigns pandas attributes/methods to Plate from Plate.df."""
    _pd_attrs = dir(pd.DataFrame)
    _pd_deprecated = ['as_blocks', 'blocks', 'ftypes', 'is_copy', 'ix']
    for attr_name in _pd_attrs:
        if (attr_name in _pd_deprecated) or (attr_name[0] == '_'):
            continue
        attr_pair = _get_pandas_attrs(Plate, attr_name)
        setattr(Plate, *attr_pair)





