import numpy as np
import pandas as pd

import pandas_flavor as pf

from functools import wraps

from .checkers import check_inputs, check_assignments
from .parsers import pad, well_regex


class Plate():
    """A pandas DataFrame-centric, well-value oriented container for
    structuring, annotating, and analyzing 96-well plate data.

    Supports assignment of well conditions during and after object
    instantiation to result in the contruction of condition-assigned,
    well-value pairs. Well column remains at 0 index, working value
    column remains -1 index to support rapid, implicit visualization of
    pertinent well/value data.

    Parameters
    ----------
    data : dict, DataFrame, or Iterable (list of length-two lists)
        Given a dict or DataFrame, the data must contain a key/column
        name that identifies 'well' (case-insentivie). The value of interest 
        can be assigned a name in the final DataFrame via 'values'
        or 'value_name' kwarg. Passing in an Iterable assumes (well, value)
        ordering and assigns as such. Must be None is wells is not None.
    wells : array-like object
        A list of wells. Must correspond in-place with list of values passed
        in the 'values' kwarg. Must be None if data is not None.
    values : string or array-like object
        If list of values, must correspond in place to the list passed in
        the 'wells' kwarg.
        If string, assumed to specify the name of the data value's key/column
        in a dict or DataFrame, or assigns this string to the Plate column
        resulting from the second entry in each (well-value) pair. Equivalently
        assigned with 'value_name' kwarg.
    value_name : string
        Non-ambiguous specification or assignment of value name.
    assign_wells : nested dictionary or template excel file
        Maps wells to conditions in new columns of a tidy DataFrame. The
        outermost keys give the name of the resulting column. The inner
        keys are the wells corresponding to a given condition/value.
        Inner keys support simply regex specification of well, such as
        '[A-C,E]2' for 'A2', 'B2', 'C2', 'E2'. (Or 'A02', etc., which is
        inferred from the initial construction.) Also takes a specific
        excel spreadsheet format; see the assign_wells() method or 
        parsers.well_regex() function for more details.
    lowercase : bool
        Whether or not auto-generated columns (such as 'row' and 'column'
        from 'well') should be lowercase. Initially assumed from case of
        'well' column, but priority goes to this argument. False gives
        capitalized values.
    zero_padded : bool, default None
        Whether or not the wells are (or should be) zero-padded, e.g., A1
        or A01. If None, determines this from what's given. If True or False,
        will update the wells to match this state.
    pandas_attrs : bool, default True
        Whether or not to assign pandas attributes and methods directly to
        Plate object rather than only being accessible via the underlying
        Plate.df attribute.

    Examples
    --------
    Constructing a Plate object with 'data':

    # With an Iterable
    >>> input = zip(['A1', 'A2'], [1, 0.5])
    >>> ns.Plate(data=input, value_name='area')
        well    row    column     area
    0   'A1'    'A'         1        1
    1   'A2'    'A'         2      0.5

    # With a dictionary (or DataFrame)
    >>> input_dict = {
    ...     'well': ['A1', 'A2'],
    ...     'area': [1, 0.5],
    ...     'RT': [0.42, 0.41],
    ... }
    >>> ns.Plate(data=input_dict, values='area')
        well    row    column      RT    area
    0   'A1'    'A'         1    0.42       1
    1   'A2'    'A'         2    0.41     0.5

    # Force capitalized and with zero-padding
    >>> input_dict = {
    ...     'well': ['A01', 'A02'],
    ...     'Area': [1, 0.5],
    ...     'RT': [0.42, 0.41],
    ... }
    >>> ns.Plate(data=input_dict, values='Area', lowercase=False)
        Well     Row   Column      RT     Area
    0   'A01'    'A'        1    0.42        1
    1   'A02'    'A'        2    0.41      0.5

    # Assign wells
    >>> input_dict = {
    ...     'well': ['A1', 'A2'],
    ...     'area': [1, 0.5],
    ...     'RT': [0.42, 0.41],
    ... }
    >>> controls = {
    ...     'controls': {
    ...         'A1': 'Experiment',
    ...         'A2': 'Negative',
    ...     }
    ... }
    >>> ns.Plate(data=input_dict, values='area', assign_wells=controls)
        well    row   column      RT       controls    area
    0   'A1'    'A'        1    0.42   'Experiment'       1
    1   'A2'    'A'        2    0.41     'Negative'     0.5
    """

    def __init__(
        self,
        data=None,
        wells=None,
        values=None,
        value_name=None,
        assign_wells=None,
        lowercase=None,
        zero_padding=None,
        pandas_attrs=True,
    ):

        # Initial setup
        self._data = data
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

            # Determine if zero-padded
            self._zero_padding = zero_padding

            # Make dataframe
            self.df = self._make_df()
            if self._pandas_attrs:
                _make_pandas_attrs(self)

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

    # Make sure data is not a generator
    @property
    def data(self):
        """Makes sure data is not zip, since it's called multiple times"""
        if isinstance(self._data, type(zip())):
            self._data = list(self._data)
        return self._data

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
            self._well_list = self.wells.copy()
        elif ((type(self.data) != type(pd.DataFrame())) and
              (type(self.data) != dict)):
            self._well_lowercase = True
            self._well_list = list(zip(*self.data)).copy()[0]
        else:
            if type(self.data) == type(pd.DataFrame()):
                cols = self.data.columns
            if type(self.data) == dict:
                cols = self.data.keys()
            well = [col for col in cols if col.lower() == 'well'][0]
            case = well[0]
            self._well_lowercase = True if case == case.lower() else False
            self._well_list = self.data[well].copy()
        return self._well_lowercase

    def _standardize_case(self, string):
        """Standardizes case of new columns based on self.case/well_case."""
        if self.lowercase is not None:
            lowercase = str.lower if self.lowercase else str.capitalize
        else:
            lowercase = self._well_lowercase
        
        case = str.lower if lowercase else str.capitalize
        
        return case(string)

    @property
    def zero_padding(self):
        """Determines if well inputs are zero-padded."""

        # If no explicit input, assume False and switch conditionally
        if self._zero_padding is None:
            
            self._zero_padding = False
        
            for well in self._well_list:

                # Check int conversion
                col = well[1:]
                if col != str(int(col)):
                    self._zero_padding = True

                # Check lengths
                if len(well) < 3:
                    self._zero_padding = False

        return self._zero_padding
    
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

        # Apply padding
        self._well_list = [well[0]+pad(well[1:], padded=self.zero_padding)
                for well in self._well_list]

        # Standardize 0 and -1 index for well and value
        del df[well_string]
        df.insert(0, well_string, self._well_list)

        if self.value_name is None:
            self._value_name = df.columns[-1]
        else:
            df = self._move_values(df)

        # Add rows and columns, if they don't exist
        col_check = [col for col in df.columns if col == 'row' or col == 'column']
        if not col_check:
            rows, cols = zip(*df[well_string].apply(
                lambda well: (well[0], int(well[1:]))
            ))

            for val, name in zip((cols, rows), ('column', 'row')):
                name = self._standardize_case(name)
                df.insert(1, name, val)

        return df


######## Plate-specific methods ########

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
            
            # Unpack dictionary and assign
            for column in assignments.keys():
                working_assignments = well_regex(assignments[column],
                                                 padded=self.zero_padding)

                # Make new columns
                wells = self.df[self._standardize_case('well')]
                self.df[column] = wells.map(working_assignments.get)

        self._move_values()

        return self

# For placing pandas attributes/functions on Plate
# rather only being accessible via Plate.df.
# pandas_flavor (pf) helps return pd.DataFrame output as Plate
@pf.register_dataframe_method
def as_plate(df):
    """Adds a method .as_plate() to wrap DataFrame as Plate"""
    return Plate(df)

def _get_pandas_attrs(Plate, attr_name):
    """Creates wrappers for pandas functions to Plate.df"""
    
    attr = getattr(pd.DataFrame, attr_name)
    if callable(attr):
        @wraps(attr)
        def wrapper(*args, **kwargs):
            
            # head and tail are not used as new Plates; return pd obj is fine
            if attr_name in ('head', 'tail'):
                output = attr(Plate.df, *args, **kwargs)

            # .as_plate() method returns DataFrame back as Plate object
            else:
                output = attr(Plate.df, *args, **kwargs).as_plate()
            return output
        attr_pair = (attr_name, wrapper)
    
    else:
        attr = getattr(Plate.df, attr_name)
        attr_pair = (attr_name, attr)

    return attr_pair

def _make_pandas_attrs(Plate):
    """Assigns pandas attributes/methods to Plate from Plate.df"""
    
    _pd_attrs = dir(pd.DataFrame)
    _pd_deprecated = ['as_blocks', 'blocks', 'ftypes', 'is_copy', 'ix']
    
    for attr_name in _pd_attrs:
        if (attr_name in _pd_deprecated) or (attr_name[0] == '_'):
            continue
        attr_pair = _get_pandas_attrs(Plate, attr_name)
        setattr(Plate, *attr_pair)





