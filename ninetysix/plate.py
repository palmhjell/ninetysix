import numpy as np
import pandas as pd

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
    ):

        # Initial setup
        self.data = data
        self.wells = wells
        self.values = values
        self._value_name = value_name
        self._passed = check_inputs(self)
        
        # For easier unit testing: make dataframe only when passing
        if self._passed:
            self.df = self._make_df()

        self._well_name = self._get_well_name()

        if assign_wells is not None:
            self.assignments = assign_wells
            self._assignment_pass = check_assignments(self)
            self.assign_wells()

    def _repr_html_(self):
        return self.df._repr_html_()

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
    
    def _make_df(self):
        """Given passing inputs, sets up the initial DataFrame."""
        if type(self.data) == type(pd.DataFrame()):
            df = self.data
        elif type(self.data) == dict:
            df = pd.DataFrame(self.data)
        elif type(self.values) == str:
            df = pd.DataFrame(data=self.data, columns=['well', self.value_name])
        else:
            if self.wells is not None:
                data = zip(self.wells, self.values)
            else:
                data = self.data
            df = pd.DataFrame(data=data, columns=['well', self.value_name])
        
        # Standardize -1 index for value
        if self.value_name is None:
            self._value_name = df.columns[-1]
        else:
            df = self._move_values(df)

        return df

    def _get_well_name(self):
        """After self._passing is True, grabs the singular 'well' column."""
        well_cols = [col for col in self.df.columns if col.lower() == 'well']
        return well_cols[0]

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
            assignments = well_regex(assignments)

            # Make new columns
            for column in assignments.keys():
                wells = self.df[self._well_name]
                self.df[column] = wells.map(assignments[column].get)

        self._move_values()

        return self

