import numpy as np
import pandas as pd

from .checkers import check_inputs, check_assignments
from .parsers import well_regex


class Plate():

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

        if assign_wells is not None:
            self.assignments = assign_wells
            self._assignment_pass = check_assignments(self)
            self.assign_wells()

    def _repr_html_(self):
        return self.df._repr_html_()

    @property
    def value_name(self):
        if (self._value_name is None) & (type(self.values) == str):
            self._value_name = self.values
        return self._value_name
    
    def _make_df(self):
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
            values = df[self.value_name]
            del df[self.value_name]
            df[self.value_name] = values

        return df

    def assign_wells(self):
        """Takes either a dictionary or standardized excel spreadsheet
        (see ninetysix/templates) to assign new columns in the output
        DataFrame that provide addition information about the contents
        or conditions of each well in the Plate.
        """
        assignment_type = type(self.assignments)
        if assignment_type == dict:

            for column in self.assignments.keys():
                working_assignments = self.assignments[column]
        pass

