import numpy as np
import pandas as pd

from .parsers import pad, _infer_padding, well_regex
from .util import check_inputs, check_annotations, check_df_col
from .util._pandas_attrs import _make_pandas_attrs


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
    annotate : nested dictionary or template excel file
        Maps wells to conditions in new columns of a tidy DataFrame. The
        outermost keys give the name of the resulting column. The inner
        keys are the wells corresponding to a given condition/value.
        Inner keys support simply regex specification of well, such as
        '[A-C,E]2' for 'A2', 'B2', 'C2', 'E2'. (Or 'A02', etc., which is
        inferred from the initial construction.) Inner keys can also be one
        of (default, standard, else, other), and the value of this key will
        be assigned to all other non-specified wells (else they get a value
        of `None`). Also takes a specific excel spreadsheet format; see the
        annotate_wells() method or  parsers.well_regex() function for more
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
    >>> ns.Plate(data=input_dict, values='area', annotate=controls)
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
        annotate=None,
        lowercase=None,
        zero_padding=None,
        # fill_plate=False,
        # n_wells=96,
        pandas_attrs=True,
    ):

###########################
# Initial set up
###########################

        self._data = data
        self.wells = wells
        self.values = values
        self._value_name = value_name
        self._init_annotations = annotate
        self._passed = check_inputs(self)
        self._pandas_attrs = pandas_attrs
        
        # For easier unit testing: do only when passing
        if self._passed:
            # Determine case
            self._lowercase = lowercase
            self._well_lowercase = self._get_well_case()

            # Three highest-level indexes, updated as needed
            self._locations = [self._standardize_case(loc)
                              for loc in ('row', 'column')]
            self._annotations = []
            self._values = [self.value_name]

            # Determine if zero-padded
            self._zero_padding = zero_padding

            # Make DataFrame(s)
            self.df = self._make_df()
            self.mi_df = self._multi_index_df()
            self._standardize_df()

            # Try to add pandas_attrs
            if self._pandas_attrs:
                try:
                    _make_pandas_attrs(self)
                except ImportError:
                    self._pandas_attrs = 'Failed due to import error'

###########################
# Operator Overloads
###########################

    def __getitem__(self, key):
        return self.df[key]

    def __setitem__(self, key, value):
        self.df[key] = value
        if key not in self._annotations:
            self._annotations.append(key)
        self._standardize_df()

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
        if isinstance(self._data, zip):
            self._data = list(self._data)
        if isinstance(self._data, dict):
            self._data = pd.DataFrame(self._data)
        if isinstance(self._data, str):
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
                if isinstance(self.data, pd.DataFrame):
                    self._value_name = self.data.columns[-1]
                else:
                    self._value_name = 'value'
            elif isinstance(self.values, str):
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
        elif not isinstance(self.data, pd.DataFrame):
            self._well_lowercase = True
            self._well_list = list(zip(*self.data)).copy()[0]
        else:
            if isinstance(self.data, pd.DataFrame):
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
            padded = [True for well in self._well_list if _infer_padding(well)]

            if padded:
                self._zero_padding = True

        return self._zero_padding

###########################
# DataFrame construction
###########################
    
    def _make_df(self):
        """Given passing inputs, sets up the initial DataFrame."""
        # Use given case
        well_string = self._standardize_case('well')

        if isinstance(self.data, pd.DataFrame):
            self.df = self.data
        elif isinstance(self.values, str):
            self.df = pd.DataFrame(data=self.data, columns=[well_string, self.value_name])
        else:
            if self.wells is not None:
                data = zip(self.wells, self.values)
            else:
                data = self.data
            self.df = pd.DataFrame(data=data, columns=[well_string, self.value_name])

        # Apply padding
        self._well_list = [pad(well, padded=self.zero_padding)
                for well in self._well_list]

        self.df[well_string] = self._well_list

        # Add row and column if not already there
        col_check = [col for col in self.df.columns if col in ('row', 'column')]

        rows, cols = zip(*self.df[well_string].apply(
            lambda well: (well[0], int(well[1:]))
        ))

        for val, name in zip((rows, cols), ('row', 'column')):
            name = self._standardize_case(name)
            if name in self.df.columns:
                del self.df[name]
            self.df.insert(1, name, val)

        # Annotate
        if self._init_annotations is not None:
            self = self.annotate_wells(self._init_annotations)

        return self.df

    def _multi_index_df(self):
        """Sets up a multi-index DataFrame, for easier arraying and
        slicing of data."""
        mi_df = self.df.copy()

        # Well as index
        mi_df = mi_df.set_index(self._standardize_case('well'))

        # Set up multi-index columns
        locs = [(self._standardize_case('Location'), loc)
               for loc in self._locations]
        annotations = [(self._standardize_case('Annotations'), ann)
                      for ann in self._annotations]
        vals = [(self._standardize_case('Values'), val)
               for val in self._values]

        # Assign other column names to annotations
        mains = [*self._locations, *self._annotations, *self._values]
        mains = [self._standardize_case('well'), *mains]
        annotations += [(self._standardize_case('Annotations'), col)
               for col in self.df.columns if col not in mains]

        # Create the multi-index
        mi_cols = pd.MultiIndex.from_tuples([*locs, *annotations, *vals])

        # Rename columns and move data appropriately
        mi_df.columns = mi_cols
        for col in mi_df.columns:
            mi_df[col] = self.df[col[:][1]].values

        return mi_df

    def _standardize_df(self):
        """Sets up columns as locations, annotations, values, with the
        order as well, row, column, other locs, annotations, other
        values, main value_name.

        Acts inplace, returns nothing. Done at the end of most methods.
        """
        # Update multi-index df
        self.mi_df = self._multi_index_df()

        # Flatten
        _df = self.mi_df.copy()
        _df.columns = _df.columns.droplevel(0)
        _df = _df.reset_index()
        self.df = _df.copy()

###########################
# Plate-specific methods
###########################

    def set_as_location(self, name, idx=-1):
        """Sets a column as a location"""
        check_df_col(self, name, 'name')
        try:
            self._annotations.remove(name)
        except ValueError:
            self._locations.remove(name)
        
        if idx == -1:
            self._locations.append(name)
        else:
            self._locations = [
                *self._locations[:idx],
                name,
                *self._locations[idx:]
            ]
        self._standardize_df()

        return self

    def set_values(self, new_values=None, value_name=None):
        """Sets columns in the Plate DataFrame as values.
        
        Parameters
        ----------
        new_values : str or list of str
            A list of column names to be set as values.
        value_name : str
            Which value should be set as the main (-1 index) value.
        """
        # Set as list
        if new_values is not None:
            if not isinstance(new_values, list):
                new_values = [new_values]

                # Check that the column exists
                for val in new_values:
                    check_df_col(self, val, 'value')
                    self._annotations.remove(val)

            # Add to self._values
            self._values += new_values

        # Update self.value_name
        if isinstance(value_name, str):
            check_df_col(self, value_name, 'value_name')
            self._value_name = value_name

        # Move main value to end of vals list
        self._values.remove(self.value_name)
        self._values.append(self.value_name)

        self._standardize_df()

        return self
        

    def annotate_wells(self, annotations):
        """Takes either a nested dictionary or standardized excel
        spreadsheet (see ninetysix/templates) to assign new columns
        in the output DataFrame that provide additional information 
        about the contents or conditions of each well in the Plate.

        Parameters
        ----------
        annotations : nested dictionary or excel sheet
            A mapping that assigns conditions to wells. For a nested
            dictionary, the outer key(s) will be the name of the condition
            which results in a new DataFrame column for each condition
            and each inner dictionary should contain key-value pairs
            where the keys either a well/regex-like well (e.g., A1 or
            [A-C]1) or a default ('default', 'standard', 'else', 'other')
            and the values are the value of the specific well
            for that condition. For an excel sheet, it should be from
            a template (https://github.com/palmhjell/ninetysix/templates).
        """
        # Check that everything passes, return type.
        annotation_type = check_annotations(self, annotations)

        if annotation_type == dict:
            # Unpack dictionary and assign
            for column in annotations.keys():
                working_annotations = well_regex(annotations[column],
                                                 padded=self.zero_padding)

                # Check for default
                default = None
                acceptable_kwargs = ('default', 'standard', 'else', 'other')
                for key in working_annotations.keys():
                    if key.lower() in acceptable_kwargs:
                        default = working_annotations[key]

                # Make new columns
                wells = self.df[self._standardize_case('well')]
                self.df[column] = wells.map(working_annotations.get)
                self.df[column] = self.df[column].replace({None: default})

            self._annotations += [col for col in annotations.keys()
                                 if col not in self._annotations]

        elif annotation_type == 'excel':

            # Read the mapping spreadsheet
            df_map = pd.read_excel(annotations, sheet_name=0, index_col=[1, 0])

            # Initialize lists (only 96-well right now)
            rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
            df_list = []

            # Iterate through each row index
            for row in rows:

                # Get tidy data from each row
                working_df = df_map.loc[row].T

                # Add which row it is
                working_df['Row'] = row

                # Add to list for later concat
                df_list.append(working_df)

            # Create a new DataFrame
            df_map = pd.concat(df_list, sort=True)

            # Get columns from index
            df_map.index.name = 'Column'
            df_map = df_map.reset_index()

            # Add Well column
            df_map['Well'] = pad(
                df_map['Row'] + df_map['Column'],
                self.zero_padding
            )

            # Drop columns that are *entirely* nans
            df_map = df_map.dropna(axis='columns', how='all')

            # Switch to None
            df_map = df_map.replace({np.nan: None})

            # Standardize case and merge
            df_map.columns = [self._standardize_case(col)
                             for col in df_map.columns]

            mergers = [self._standardize_case(col)
                      for col in ['Well', 'Column', 'Row']]

            self.df = self.df.merge(df_map, on=mergers)

            # Update annotations
            self._annotations += [col for col in df_map
                                 if col not in mergers
                                 and col not in self._annotations]

        self._standardize_df()

        return self


    def normalize(
        self,
        value=None,
        to=None,
        zero=None,
        # devs=False,
        update_value=None,
    ):
        """Normalizes the value column to give the max a value of 1,
        returning a new column named 'normalized_[value]'. Accepts
        different value kwargs and can explicitly scale from 0 to 1
        'zero=True'. Alternatively, scales relative to a specific
        assignment of a condition column, i.e. to 'Standard' within
        the condition 'Controls' can be set to a value of 1.
        Additionally can assign a lower 0 value in the same way.
        """
        # Determine how to update the value
        # TODO: does this need a warning for True when type(value) == list?
        if update_value is None and not isinstance(value, list):
            update_value = True
            if isinstance(update_value, str):
                if update_value not in value:
                    raise ValueError(
                        f"Given update value '{update_value}' not found in list of values to be normalized."
                    )
            else:
                update_value = False

        # Get value list ready
        if value is None:
            value = self.value_name
        if not isinstance(value, list):
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
            elif isinstance(zero, str):
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
            elif zero is None or zero == False:
                zero_val = 0
            else:
                raise TypeError(
                    f"Type of 'zero' argument is incorrectly specified. Must be bool or string.")

            self.df[norm_string] = self.df[value] - zero_val

            # Set the one val
            if to is None:
                one_val = self.df[norm_string].max()
            elif isinstance(to, str):
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

            # Update self._values list
            if norm_string not in self._values:
                self._values.append(norm_string)
        
        # Clean up
        if update_value:
            if isinstance(update_value, str):
                update_string = f'normalized_{update_value}'
            else:
                update_string = norm_string
            
            self._value_name = update_string

        self._standardize_df()

        return self
