import numpy as np
import pandas as pd

from .checkers import check_inputs, check_assignments, check_df_col
from .parsers import pad, well_regex
from .pandas_attrs import _make_pandas_attrs


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
    data : dict, DataFrame, Iterable (list of length-two lists), or path
        Given a dict or DataFrame, the data must contain a key/column
        name that identifies 'well' (case-insentivie). The value of interest 
        can be assigned a name in the final DataFrame via 'values'
        or 'value_name' kwarg. Passing in an Iterable assumes (well, value)
        ordering and assigns as such. Passing a string will assume a path
        to a pandas-readable csv or excel file, using the default settings.
        If more control over the import of this file is needed, import to a
        pandas DataFrame first, then pass this to 'data'. Must be None is wells is not None.
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
    assignments : nested dictionary or template excel file
        Maps wells to conditions in new columns of a tidy DataFrame. The
        outermost keys give the name of the resulting column. The inner
        keys are the wells corresponding to a given condition/value.
        Inner keys support simply regex specification of well, such as
        '[A-C,E]2' for 'A2', 'B2', 'C2', 'E2'. (Or 'A02', etc., which is
        inferred from the initial construction.) Inner keys can also be one
        of (default, standard, else, other), and the value of this key will
        be assigned to all other non-specified wells (else they get a value
        of `None`). Also takes a specific excel spreadsheet format; see the
        assign_wells() method or  parsers.well_regex() function for more
        details.
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
        Plate.df attribute. If it fails due to an import error, a message
        (Failed due to import error) replaces the bool.

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
    >>> ns.Plate(data=input_dict, values='area', assignments=controls)
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
        assignments=None,
        lowercase=None,
        zero_padding=None,
        pandas_attrs=True,
    ):


###########################
# Initial set up
###########################

        self._data = data
        self.wells = wells
        self.values = values
        self._value_name = value_name
        self._init_assignments = assignments
        self._passed = check_inputs(self)
        self._pandas_attrs = pandas_attrs
        
        # For easier unit testing: do only when passing
        if self._passed:
            # Determine case
            self._lowercase = lowercase
            self._well_lowercase = self._get_well_case()

            # Determine if zero-padded
            self._zero_padding = zero_padding

            # Make DataFrame
            self.df = self._make_df()

            # Try to add pandas_attrs
            if self._pandas_attrs:
                try:
                    _make_pandas_attrs(self)
                except ImportError:
                    self._pandas_attrs = 'Failed due to import error'

            # Annotate
            if self._init_assignments is not None:
                check_assignments(self, self._init_assignments)
                self.assign_wells(self._init_assignments, inplace=True)


###########################
# Operator Overloads
###########################

    def __getitem__(self, key):
        return self.df[key]

    def __setitem__(self, key, value):
        self.df[key] = value

    def __copy__(self):
        copied = type(self)()
        copied.__dict__.update(self.__dict__)
        return copied

    def _repr_html_(self):
        return self.df._repr_html_()


###########################
# Properties and support methods
###########################

    @property
    def data(self):
        """Makes sure data is not zip, since it's called multiple times,
        and read in to pd.DataFrame if dict or path.
        """
        if isinstance(self._data, type(zip())):
            self._data = list(self._data)
        if type(self._data) == dict:
            self._data = pd.DataFrame(self._data)
        if type(self._data) == str:
            extension = self._data.split('.')[-1]
            if extension == 'csv':
                self._data = pd.read_csv(self._data)
            if extension in ('xls', 'xlsx'):
                engine = 'openpyxl' if extension == 'xlsx' else 'xlrd'
                self._data = pd.read_excel(self._data, engine=engine)
        return self._data

    @property
    def value_name(self):
        """Sets value name from 'value_name', 'values', or sets to 'value',
        unless obtained from the final column of a DataFrame.
        """
        if self._value_name is None:
            if self.values is None:
                if type(self.data) == type(pd.DataFrame()):
                    self._value_name = self.data.columns[-1]
                else:
                    self._value_name = 'value'
            elif type(self.values) == str:
                self._value_name = self.values
            elif self.data is None:
                self._value_name = 'value'
        return self._value_name

    @value_name.setter
    def value_name(self, value):
        self._value_name = value

    @property
    def lowercase(self):
        """Highest priority case-setter for new columns."""
        return self._lowercase

    def _get_well_case(self):
        """After self._passing is True, determines well case."""
        if self.data is None:
            self._well_lowercase = True
            self._well_list = self.wells.copy()
        elif type(self.data) != type(pd.DataFrame()):
            self._well_lowercase = True
            self._well_list = list(zip(*self.data)).copy()[0]
        else:
            if type(self.data) == type(pd.DataFrame()):
                cols = self.data.columns
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


###########################
# DataFrame construction
###########################
    
    def _make_df(self):
        """Given passing inputs, sets up the initial DataFrame."""
        # Use given case
        well_string = self._standardize_case('well')

        if type(self.data) == type(pd.DataFrame()):
            df = self.data
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

        # Standardize layout
        self._standardize_df(df)

        return df

    def _standardize_df(self, df=None):
        """Moves 'well', 'row', 'column' to 0, 1, 2 and 'value' to -1 index"""
        if df is not None:
            self.df = df

        # Use given case
        well_string = self._standardize_case('well')

        # Standardize 0 index for well
        del self.df[well_string]
        self.df.insert(0, well_string, self._well_list)

        # Add rows and columns to 1 and 2 index
        col_check = [col for col in self.df.columns if col ==
                     'row' or col == 'column']

        rows, cols = zip(*self.df[well_string].apply(
            lambda well: (well[0], int(well[1:]))
        ))

        for val, name in zip((cols, rows), ('column', 'row')):
            name = self._standardize_case(name)
            if col_check:
                del self.df[name]
            self.df.insert(1, name, val)

        # Move values to -1 index
        values = self.df[self.value_name]
        del self.df[self.value_name]
        self.df[self.value_name] = values
        
        return self.df


###########################
# Plate-specific methods
###########################

    def assign_wells(self, assignments, inplace=False):
        """Takes either a nested dictionary or standardized excel
        spreadsheet (see ninetysix/templates) to assign new columns
        in the output DataFrame that provide additional information 
        about the contents or conditions of each well in the Plate.

        Parameters
        ----------
        assignments : nested dictionary or excel sheet
            A mapping that assigns conditions to wells. For a nested
            dictionary, the outer key(s) will be the name of the condition
            which results in a new DataFrame column for each condition
            and each inner dictionary should contain key-value pairs
            where the keys either a well/regex-like well (e.g., A1 or
            [A-C]1) or a default ('default', 'standard', 'else', 'other')
            and the values are the value of the specific well
            for that condition. For an excel sheet, it should be from
            a template (https://github.com/palmhjell/ninetysix/templates).
        inplace : bool, default False
            Whether to return a new object or act on the object in place.
        """
        if not inplace:
            self = self.copy()

        check_assignments(self, assignments)

        if type(assignments) == dict:
            # Unpack dictionary and assign
            for column in assignments.keys():
                working_assignments = well_regex(assignments[column],
                                                 padded=self.zero_padding)

                # Check for default
                default = None
                acceptable_kwargs = ('default', 'standard', 'else', 'other')
                for key in working_assignments.keys():
                    if key.lower() in acceptable_kwargs:
                        default = working_assignments[key]

                # Make new columns
                wells = self.df[self._standardize_case('well')]
                self.df[column] = wells.map(working_assignments.get)
                self.df[column] = self.df[column].replace({None: default})

        else:
            print('Non-dict functionality is not yet supported.')

        self._standardize_df()
        
        if not inplace:
            return self


    def normalize(
        self,
        value=None,
        to=None,
        zero=None,
        # devs=False,
        update_value=None,
        inplace=False,
    ):
        """Normalizes the value column to give the max a value of 1,
        returning a new column named 'normalized_[value]'. Accepts
        different value kwargs and can explicitly scale from 0 to 1
        'zero=True'. Alternatively, scales relative to a specific
        assignment of a condition column, i.e. to 'Standard' within
        the condition 'Controls' can be set to a value of 1.
        Additionally can assign a lower 0 value in the same way.
        """

        if not inplace:
            self = self.copy()

        # Determine how to update the value
        ### TODO: does this need a warning for True when type(value) == list?
        if update_value is None and type(value) != list:
            update_value = True
        if type(update_value) == str:
            if update_value not in value:
                raise ValueError(
                    f"Given update value '{update_value}' not found in list of values to be normalized."
                )
        else:
            update_value = False

        # Get value list ready
        if not value:
            value = self.value_name
        if type(value) != list:
            values = [value]
        else:
            values = value

        # Iterate through each value
        for value in values:
            check_df_col(self, value, name='value')

            norm_string = f'normalized_{value}'

            # Set the zero val
            if zero == True:
                zero_val = self.df[value].min()
            elif type(zero) == str:
                split = zero.split('=')
                if len(split) != 2:
                    raise ValueError(
                        f"'zero' value specified incorrectly, must be of the form '[column_name]=[value_name]'."
                    )

                col, val = split

                # Check that col in columns
                check_df_col(self, col, name='column')

                # Check that the given value is found in the column
                if val not in [str(i) for i in self.df[col]]:
                    raise ValueError(
                        f"The value '{val}' is not a value in the column '{col}'."
                    )
                subset = [val == str(i) for i in self.df[col]]
                zero_val = self.df[subset][value].mean()
            elif zero == None or zero == False:
                zero_val = 0
            else:
                raise TypeError(
                    f"Type of 'zero' argument is incorrectly specified. Must be bool or string.")

            self.df[norm_string] = self.df[value] - zero_val

            # Set the one val
            if not to:
                one_val = self.df[norm_string].max()
            elif type(to) == str:
                split = to.split('=')
                if len(split) != 2:
                    raise ValueError(
                        f"'to' value specified incorrectly, must be of the form '[column_name]=[value_name]'."
                    )
                
                col, val = split
                
                # Check that col in columns
                check_df_col(self, col, name='column')

                # Check that the given value is found in the column
                if val not in [str(i) for i in self.df[col]]:
                    raise ValueError(
                        f"The value '{val}' is not a value in the column '{col}'."
                    )
                subset = [val == str(i) for i in self.df[col]]
                one_val = self.df[subset][norm_string].mean()
            else:
                raise TypeError(f"Type of 'to' argument is incorrectly specified. Must be bool or string.")

            self.df[norm_string] = self.df[norm_string] / one_val

        # Clean up
        if update_value:
            if type(update_value) == str:
                update_string = f'normalized_{update_value}'
            else:
                update_string = norm_string
            self._value_name = update_string

        self._standardize_df()

        if not inplace:
            return self
