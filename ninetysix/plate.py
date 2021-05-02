"""
Plate
------
Primary functionality of ninetysix, providing the a class for the
rapid analysis and visualization of ninety-six* well plate assays.

*Not actually restricted to 96 wells, pretty much anything goes.
"""

import numpy as np
import pandas as pd

from .parsers import pad, _infer_padding, well_regex
from .util import check_inputs, check_annotations, check_df_col
from .util._plate_attrs import _set_viz_attrs, _set_pandas_attrs


class Plate():
    """A pandas DataFrame-centric, well-value oriented container for
    structuring, annotating, and analyzing 96-well* plate data.

    (*Contrary to the package name, can be more or less than 96 wells.)

    Supports assignment of well conditions during and after object
    instantiation to result in the construction of condition-assigned,
    well-value pairs. Well column remains at 0 index, working value
    column remains -1 index to support rapid, implicit visualization of
    pertinent well-value data.

    Parameters:
    -----------
    data: dict, DataFrame, Iterable (list of length-two lists), or path
        Given a dict or DataFrame, the data must contain a key/column
        name that identifies 'well' (case-insentivie). The value of 
        interest can be assigned a name in the final DataFrame via
        `value_name` kwarg. Passing in an Iterable assumes tuples of
        `(well, value)` ordering and assigns as such. Passing a string
        will assume a path to a pandas-readable csv or excel file, using
        the default settings. If more control over the import of this
        file is needed, import to a pandas DataFrame first, then pass
        this to `data`.
    value_name: string or list
        Specification or assignment of value name(s). If given as a
        list, the last entry is used as the primary working value.
    annotate: nested dictionary or template excel file
        Maps wells to conditions in new columns of a tidy DataFrame. The
        outermost keys give the name of the resulting column. The inner
        keys are the wells corresponding to a given condition/value.
        Inner keys support simply regex specification of well, such as
        '[A-C,E]2' for 'A2', 'B2', 'C2', 'E2'. (Or 'A02', etc., which is
        inferred from the initial construction.) Inner keys can also be
        one of (default, standard, else, other), and the value of this
        key will be assigned to all other non-specified wells (else they
        get a value of `None`). Also takes a specific excel spreadsheet
        format; see the annotate_wells() method or  parsers.well_regex() function for more details.
    zero_padding: bool, default None
        Whether or not the wells are (or should be) zero-padded, e.g.,
        A1 or A01. If None, determines this from what's given. If True
        or False, will update the wells to match this state.
    case: str method, default str.lower
        Assigns the case of auto-generated DataFrame columns.
    pandas_attrs: bool, default True
        Whether or not to assign pandas attributes and methods directly
        to Plate object rather than only being accessible via the
        underlying Plate.df attribute. If it fails due to an import
        error, the attribute becomes a message (Failed due to import
        error).

    Examples:
    ---------
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
    >>> ns.Plate(data=input_dict, value_name='area')
        well    row    column      RT    area
    0   'A1'    'A'         1    0.42       1
    1   'A2'    'A'         2    0.41     0.5

    # Force capitalized and with zero-padding
    >>> input_dict = {
    ...     'well': ['A01', 'A02'],
    ...     'Area': [1, 0.5],
    ...     'R.T.': [0.42, 0.41],
    ... }
    >>> ns.Plate(data=input_dict, value_name='Area', case=str.title)
        Well     Row   Column      R.T.     Area
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
    ...         'A1': 'experiment',
    ...         'A2': 'negative',
    ...     }
    ... }
    >>> ns.Plate(data=input_dict, value_name='area', annotate=controls)
        well    row   column      RT       controls    area
    0   'A1'    'A'        1    0.42   'experiment'       1
    1   'A2'    'A'        2    0.41     'negative'     0.5
    """

    def __init__(
        self,
        data=None,
        value_name=None,
        annotate=None,
        zero_padding=None,
        case=None,
        # fill_plate=False,
        # n_wells=96,
        pandas_attrs=True,
    ):

###########################
# Initial set up
###########################

        # Work up and check data input
        self.data = data
        self._passed = check_inputs(self, value_name)

        # Assign case attribute
        self.case = case

        # First, get well string (self._well) and well list (self._wells)
        self._well, self._wells = self._get_well_info()

        # Assign and update zero padding (can update self._wells)
        self.zero_padding = zero_padding

        # Assign and update value name (can update self._well)
        self.value_name = value_name

        # Check and generate row and column info
        (self._row, self._rows, self._col, self._cols)\
                                        = self._generate_defaults()

        # Instantiate full Plate DataFrame
        self.df = self._init_df()

        # Add high-level attributes
        self._locations = [self._well, self._row, self._col]
        self._annotations = [
            col for col in self.df.columns
            if col not in [*self.locations, self.value_name]
        ]
        self._values = [self.value_name]

        # Pack into dictionary
        self.column_dict = self._update_column_dict()

        # Organize DataFrame(s)
        self.mi_df = self._init_mi_df()
        self._standardize_df()

        # Annotate
        if annotate is not None:
            self = self.annotate_wells(annotate)

        # Try to add pandas_attrs
        self._pandas_attrs = pandas_attrs
        if self._pandas_attrs:
            try:
                _set_pandas_attrs(self)
            except ImportError:
                self._pandas_attrs = 'Failed due to import error'

        # Set plotting attributes directly as methods
        _set_viz_attrs(self)

###########################
# Operator Overloads
###########################

    def __getitem__(self, key):
        """Overwritten to get from DataFrame attribute"""
        return self.df[key]

    def __setitem__(self, key, value):
        """Overwritten to set to DataFrame object, as annotation"""
        key = self._set_case(key)
        self.mi_df[('annotations', key)] = value
        if key not in self.annotations:
            self.annotations.append(key)
        self._standardize_df()

    def __delitem__(self, key):
        """Overwritten to prohibit deleting base locations and to update
        the location, annotation, and value attributes.
        """
        base_locs = ['well', 'row', 'column']
        if self._set_case(key) in base_locs:
            raise ValueError(
                'Cannot delete base locations (well, row, column).'
            )
        del self.df[key]
        for attr_list in (self.locations, self.annotations, self.values):
            if key in attr_list:
                attr_list.remove(key)
        self._standardize_df()

    def __len__(self):
        return len(self.df)

    def _repr_html_(self):
        """Sets HTML representation as DataFrame attribute"""
        return self.df._repr_html_()

################################
# Properties and support methods
################################

### Data
    @property
    def data(self):
        """Makes sure data is not zip, since it's called multiple times,
        and read in to pd.DataFrame if path or dict.
        """
        return self._data

    @data.setter
    def data(self, data):
        if isinstance(data, zip):
            data = list(data)
        if isinstance(data, str):
            extension = data.split('.')[-1]
            if extension == 'csv':
                data = pd.read_csv(data)
            if extension in ('xls', 'xlsx'):
                engine = 'openpyxl' if extension == 'xlsx' else 'xlrd'
                data = pd.read_excel(data, engine=engine)
        if isinstance(data, dict):
            data = pd.DataFrame(data)
        self._data = data

### Casing
    @property
    def case(self):
        """Highest priority case-setter for new columns."""
        return self._case

    @case.setter
    def case(self, case):
        self._case = case

        cases = (str.lower, str.title, str.capitalize, str.upper, None)
        if case not in cases:
            raise ValueError(
                'Only string-class case types are allowed, or None. '
                'Choose one of [str.lower, str.title, str.capitalize, '
                'str.upper, None].'
            )

        self._standardize_df()

    def _set_case(self, string):
        """For actually setting the case."""
        # If case is enforced with Plate.case
        if self.case is not None and string is not None:
            string = self.case(string)
        return string

### Zero padding of well
    @property
    def zero_padding(self):
        """Determines if well inputs are zero-padded."""
        return self._zero_padding

    @zero_padding.setter
    def zero_padding(self, padding):
        self._zero_padding = padding

        # If no explicit input, assume False and switch conditionally
        if padding is None:
            self._zero_padding = False
            padded = [True for well in self._wells if _infer_padding(well)]

            if padded:
                self._zero_padding = True
                self._wells = [pad(well) for well in self._wells]

        self._standardize_df()

### Value name
    @property
    def value_name(self):
        """Sets value name from `value_name`, or sets to 'value',
        unless obtained from the final column of a DataFrame.
        """
        return self._value_name

    @value_name.setter
    def value_name(self, value_name):
        self._value_name = self._set_case(value_name)
        if self._value_name is None:
            # Auto generate value_name
            if isinstance(self.data, pd.DataFrame):
                self._value_name = self.data.columns[-1]
            else:
                self._value_name = self._set_case('value')
        
        # Standardize case if not auto-generated
        elif not isinstance(self.data, pd.DataFrame):
                # If you get here, this will override the case of 'well'
                for method in (str.lower, str.upper, str.capitalize, str.title):
                    if method(self._value_name) == self._value_name: 
                            self._value_name = method(self._value_name)
                            self._well = method(self._well)

        self._standardize_df()

### Primary descriptors
    @property
    def locations(self):
        """Each column in the data that specifies location information"""
        return self._locations

    @locations.setter
    def locations(self, locations):
        self._locations = locations
        self._update_column_dict()

    @locations.getter
    def locations(self):
        return self._locations

    @property
    def annotations(self):
        """Each column in the data that specifies additional information"""
        return self._annotations

    @annotations.setter
    def annotations(self, annotations):
        self._annotations = annotations
        self._update_column_dict()

    @annotations.getter
    def annotations(self):
        return self._annotations

    @property
    def values(self):
        """Each column in the data that specifies value information"""
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        self.value_name = values[-1]
        self._update_column_dict()

    @values.getter
    def values(self):
        return self._values


    @property
    def column_dict(self):
        return self._column_dict

    @column_dict.setter
    def column_dict(self, column_dict):
        self._column_dict = column_dict

### Instantiation methods
    def _get_well_info(self):
        """After data is validated, determines well string and stores
        list of wells as attributes.
        """
        # If self.data is not DataFrame (or initially dict)
        if not isinstance(self.data, pd.DataFrame):
            self._well = self._set_case('well')
            self._wells = list(zip(*self.data)).copy()[0]
        else:
            if isinstance(self.data, pd.DataFrame):
                cols = self.data.columns
            well_cols = [col for col in cols if col.lower() == 'well']
            self._well = well_cols[0]
            self._wells = self.data[well_cols[0]].copy()
            self._well = self._set_case(self._well)
        return self._well, self._wells

    def _generate_defaults(self):
        """Generates 'row' and 'column' info from well"""
        if isinstance(self.data, pd.DataFrame):
            # Check for these columns
            row = [col for col in self.data.columns if col.lower() == 'row']
            col = [col for col in self.data.columns if col.lower() == 'column']
            
            # These should not happen.......
            if len(row) > 1:
                raise ValueError(
                    'Found multiple columns in your DataFrame named "row".'
                )
            if len(col) > 1:
                raise ValueError(
                    'Found multiple columns in your DataFrame named "column".'
                )
            
            # If we found these columns, store them for _inti_df()
            if row:
                rows = self.data[row[0]]
                del self.data[row[0]]
                row = self._set_case(row[0])
            else:
                for method in (str.lower, str.upper, str.capitalize, str.title):
                    if method(self._value_name) == self._value_name: 
                        row = method('row')
                rows = [well[0] for well in self._wells]
            
            if col:
                cols = self.data[col[0]]
                del self.data[col[0]]
                col = self._set_case(col[0])
            else:
                for method in (str.lower, str.upper, str.capitalize, str.title):
                    if method(self._value_name) == self._value_name: 
                        col = method('column')
                cols = [int(well[1:]) for well in self._wells]

        else:
            # Standardize case to value_name
            for method in (str.lower, str.upper, str.capitalize, str.title):
               if method(self._value_name) == self._value_name: 
                    row = method('row')
                    column = method('column')
            row = self._set_case(row)
            rows = [well[0] for well in self._wells]
            col = self._set_case(column)
            cols = [int(well[1:]) for well in self._wells]

        return row, rows, col, cols

    def _update_column_dict(self):
        """Keeps track of multi-index indexes, updates as necessary.
        """
        col_dict_keys = ['locations', 'annotations', 'values']
        try:
            col_dict_vals = (self.locations, self.annotations, self.values)
        except AttributeError:
            return
        
        # Update attributes
        self._well = self._set_case(self._well)
        self.column_dict = {
            key: [self._set_case(val) for val in vals]
            for key, vals in zip(col_dict_keys, col_dict_vals)
        }
        self._locations = self.column_dict['locations']
        self._annotations = self.column_dict['annotations']
        self._values = self.column_dict['values']

        return self.column_dict

    def _remove_column(self, column):
        for attr_list in (self.locations, self.annotations, self.values):
            if column in attr_list:
                attr_list.remove(column)

###########################
# DataFrame construction
###########################
    
    def _init_df(self):
        """Given passing inputs, sets up the initial DataFrame."""
        if isinstance(self.data, pd.DataFrame):
            self.df = self.data.copy()
            self.df.columns = [self._set_case(col) for col in self.df.columns]
        elif isinstance(self.data, list):
            self.df = pd.DataFrame(
                data=self.data,
                columns=[self._well, self.value_name]
            )

        # Add row and column info based on _generate_defaults
        self.df.insert(1, self._col, self._cols)
        self.df.insert(1, self._row, self._rows)

        return self.df


    def _init_mi_df(self):
        """Sets up a multi-index DataFrame, for easier arraying and
        slicing of data."""
        # Well as index
        mi_df = self.df.copy().set_index(self._well)

        # Set up multi-index columns
        tuples = []
        for key, value in self.column_dict.items():
            tuples += [(key, val) for val in value
                       if val != self._well]

        # Create the multi-index
        mi_cols = pd.MultiIndex.from_tuples(tuples)
        
        # Rename columns and move data appropriately
        mi_df.columns = mi_cols
        for col in mi_df.columns:
            mi_df[col] = self.df[col[:][1]].values

        return mi_df


    def _standardize_df(self):
        """Sets up columns as locations, annotations, values, with the
        order as well, row, column, other locs, annotations, other
        values, main value_name. Standardizes case and zero-padding.

        Acts inplace, returns nothing. Done at the end of most methods
        and setters.
        """
        # Exit if self.df has not been created yet
        try:
            self.df
        except AttributeError:
            return

        # Same if plate lists have not been created
        self.column_dict = self._update_column_dict()
        
        # Reset index in mi_df
        mi_df = self.mi_df.reset_index(col_level=1, col_fill='locations')

        # Get current multi-index df dict
        mi_dict = mi_df.to_dict()

        # Standardize casing for use in reordering
        mi_dict = {
            (key1, self._set_case(key2)): value
            for (key1, key2), value in mi_dict.items()
        }

        # Reorder
        new_dict = {}
        for key1, plate_list in self.column_dict.items():
            for key2 in plate_list:
                key_pair = (key1, key2)
                value = mi_dict[key_pair]
                new_dict[key_pair] = value

        # Assign as new mi_df
        self.mi_df = pd.DataFrame(new_dict)

        # Flatten
        _df = self.mi_df.copy()
        _df.columns = _df.columns.droplevel(0)
        self.df = _df.copy()

        # Update padding
        self._well = self._set_case(self._well)
        self._wells = [pad(well, padded=self.zero_padding)
                           for well in self._wells]
        self.df[self._well] = self._wells
        self.mi_df = self._init_mi_df()

###########################
# Plate-specific methods
###########################

    def set_as_location(self, name, idx=-1):
        """Sets a column as a location"""
        check_df_col(self.df, name, 'name')
        vals = self.df[name].values
        self._remove_column(name)
        self.mi_df[('locations', name)] = vals
        
        if idx == -1:
            self.locations.append(name)
        else:
            self.locations = [
                *self.locations[:idx],
                name,
                *self.locations[idx:]
            ]
        
        self._standardize_df()


    def set_as_values(self, new_values=None, value_name=None):
        """Sets columns in the Plate DataFrame as values.
        
        Parameters:
        -----------
        new_values: str or list of str
            A list of column names to be set as values.
        value_name: str
            Which value should be set as the main (-1 index) value.
        """
        # Set as list
        if new_values is not None:
            if not isinstance(new_values, list):
                new_values = [new_values]

                # Check that the column exists
                for val in new_values:
                    check_df_col(self.df, val, 'value')

                    # Place it in the plate
                    vals = self.df[val].values
                    self._remove_column(val)
                    self.mi_df[('values', val)] = vals

            # Add to self._values
            self.values += new_values

        # Update self.value_name
        if value_name is not None:
            check_df_col(self.df, value_name, 'value_name')
            self.value_name = value_name

        # Move main value to end of vals list
        if self.value_name not in self.values:
            raise ValueError(
                f"'{value_name}' not found in list of values. Pick one of "\
                f"{self.values} or pass new_values='{value_name}'."
            )
        self.values.remove(self.value_name)
        self.values.append(self.value_name)

        self._standardize_df()
        

    def annotate_wells(self, annotations):
        """Takes either a nested dictionary or standardized excel
        spreadsheet (see ninetysix/templates) to assign new columns
        in the output DataFrame that provide additional information 
        about the contents or conditions of each well in the Plate.

        Parameters:
        -----------
        annotations: nested dictionary or excel sheet
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
                wells = self.df[self._well]
                key = ('annotations', column)
                self.mi_df[key] = wells.map(working_annotations.get)
                self.mi_df[key] = self.mi_df[key].replace({None: default})

            self.annotations += [col for col in annotations.keys()
                                 if col not in self.annotations]

        elif annotation_type == 'excel':

            # Read the mapping spreadsheet
            df_map = pd.read_excel(annotations, sheet_name=0, index_col=[1, 0])

            # Initialize lists (only 96-well right now)
            rows = list('ABCDEFGH')
            df_list = []

            # Iterate through each row index
            for row in rows:

                # Get tidy data from each row
                working_df = df_map.loc[row].T

                # Add which row it is
                working_df['row'] = row

                # Add to list for later concat
                df_list.append(working_df)

            # Create a new DataFrame
            df_map = pd.concat(df_list, sort=True)

            # Get columns from index
            df_map.index.name = 'column'
            df_map = df_map.reset_index()

            # Add Well column
            df_map['well'] = pad(
                df_map['row'] + df_map['column'],
                self.zero_padding
            )

            # Drop columns that are *entirely* nans
            df_map = df_map.dropna(axis='columns', how='all')

            # Switch to None
            df_map = df_map.replace({np.nan: None})

            # Standardize case and merge
            df_map.columns = [self._set_case(col)
                             for col in df_map.columns]

            mergers = [self._set_case(col)
                      for col in ['well', 'column', 'row']]

            self.df = self.df.merge(df_map, on=mergers)

            # Update annotations
            self.annotations += [col for col in df_map
                                  if col not in mergers
                                  and col not in self.annotations]

        self._standardize_df()

        return self


    def normalize(
        self,
        value=None,
        to=None,
        zero=None,
        groupby=None,
        # devs=False,
        update_value=None,
        prefix='normalized_',
    ):
        """Normalizes the value column to give the max a value of 1,
        returning a new column named '[prefix][value]', e.g.,
        'normalized_value. Accepts different value kwargs and can
        explicitly scale from 0 to 1 'zero=True'. Alternatively, scales relative to a specific assignment of a condition column, i.e. to 'Standard' within the condition 'Controls' can be set to a value
        of 1 via the kwarg `to='Controls=Standard'`. Additionally can
        assign a lower 0 value in the same way.

        Parameters:
        -----------
        value: str or list of str, default None
            Name of column to normalize, default being value_name.
        to: str, default None
            Which group to set as the normal (1) value. If None, the max
            value for each column in `value` is set to 1 and all other
            values are scaled to this. If a condition is passed, e.g., `to='Controls=Standard'`, the mean of the wells labeled
            'Standard' in the column 'Controls' will be set to 1 for
            each value column.
        zero: str or bool, default None
            Whether or not to set the lowest value as an explicit zero
            (`zero=True`) or just to scale all values as is (`zero=
            False`), or to set the mean of a specific group as the zero
            value as in the `to` kwarg, e.g., `zero='Controls=Negative'`
            would set the  wells labeled 'Negative' in the column
            'Controls' to zero (this is useful when your 'zero'
            assay condition does not actually give values of zero).
        groupby: str, default None
            Whether to split the normalization across many groups in the
            column (or columns) specified in groupby, e.g., for each
            value in the column 'Plate'.
        update_value: str or bool, default None
            Whether or not (or what) to set as the new Plate value_name.
            If True and `value` is not a list, sets `value` to right-
            most column. If a string, sets that normalized value to the
            new `value_name`. If None or False, just adds a new value
            and leaves the old `value_name`. 
        prefix: str, default 'normalized_'
            What to add to the new column name to indicate that it has
            been normalized.
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

        # Set up groups
        if not isinstance(groupby, (tuple, list)):
            groupby = [groupby]

        for group in groupby:
            check_df_col(self.df, group, name='groupby')

        # Group or create fake groupby object
        unique_dfs = (self.df.groupby(groupby) if groupby != [None]
                      else [(None, self.df.copy())])

        df_list = []
        # Iterate through each dataframe
        for name, sub_df in unique_dfs:

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
                            f"'zero' value specified incorrectly, must be of the form 'column_name=value_name'."
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
                            f"'to' value specified incorrectly, must be of the form 'column_name=value_name'."
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
                    raise TypeError(f"Type of 'to' argument is incorrectly specified. Must be bool or string.")

                sub_df[norm_string] = sub_df[norm_string] / one_val

                # Update self._values list
                if norm_string not in self._values:
                    self._values.insert(-2, norm_string)

                # Store in df_list
                df_list.append(sub_df)

            # Add new column in correct order
            mergers = [self._well,
                       *[elem for elem in groupby if elem is not None]]
            _df = self.df[mergers].merge(
                pd.concat(df_list), on=mergers
            )
            
            self.mi_df[('values', norm_string)] = _df[norm_string]
        
        # Clean up
        if update_value:
            if isinstance(update_value, str):
                update_string = f'{prefix}{update_value}'
            else:
                update_string = norm_string
            
            self.value_name = update_string
            self._values.remove(update_string)
            self._values.append(update_string)

        self._standardize_df()

        return self
  
