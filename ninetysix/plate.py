"""
Plate
------
Primary functionality of ninetysix, providing the a class for the
rapid analysis and visualization of ninety-six* well plate assays.

*Not actually restricted to 96 wells, pretty much anything goes.
"""

import numpy as np
import pandas as pd

from .parsers import well_regex, pad, _infer_padding, _infer_casing
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
        case=None,
        zero_padding=None,
        annotate=None,
        # fill_plate=False,
        # n_wells=96,
        pandas_attrs=True,
    ):

###########################
# Initial set up
###########################
#         
        # Assign attributes
        self._data = data
        self._value_name = value_name
        self._zero_padding = zero_padding
        self._case = case

        # Convert data into initial DataFrame-like object
        self.data = data

        # Check that all inputs are acceptable
        self._passed = check_inputs(self)

        # Get information and regularize the dataframe
        self.df, self._well, self._row, self._col = self._generate_df()

        # Try to add pandas_attrs
        self._pandas_attrs = pandas_attrs
        if self._pandas_attrs:
            try:
                _set_pandas_attrs(self)
            except ImportError:
                self._pandas_attrs = 'Failed due to import error'

        # Add high-level attributes
        self._locations = [self._well, self._row, self._col]
        self._annotations = [
            col for col in self.df.columns
            if col not in [*self.locations, self.value_name]
        ]
        self._values = [self.value_name]

        # Pack into dictionary
        self._column_dict = {
            'locations': self.locations,
            'annotations': self.annotations,
            'values': self.values
        }

        # Organize DataFrame
        self.mi_df = self._generate_mi_df()
        self.zero_padding = zero_padding
        self.case = case

        # Annotate
        if annotate is not None:
            # Cannot reassign self in init, so need to be clever
            self.mi_df = self.annotate_wells(annotate).mi_df
            self.column_dict = self.annotate_wells(annotate).column_dict

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
            self.annotations = [*self.annotations, key]

    def __delitem__(self, key):
        """Overwritten to prohibit deleting base locations and to update
        the location, annotation, and value attributes.
        """
        base_locs = [self._well, self._row, self._col]
        if key in base_locs:
            raise ValueError(
                'Cannot delete base locations (well, row, column).'
            )
        del self.df[key]
        for attr in ('locations', 'annotations', 'values'):
            attr_list = getattr(self, attr)
            if key in attr_list:
                attr_list.remove(key)
                del self.mi_df[(attr, key)]

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
        and read in to initial pd.DataFrame.
        """
        return self._data

    @data.setter
    def data(self, data):
        # Possible well-value pair types
        wv_pair_types = (zip, list, tuple, np.ndarray)
        if isinstance(data, wv_pair_types):
            data = pd.DataFrame(
                list(data),
                columns=['well', None]
            )
        if isinstance(data, str):
            extension = data.split('.')[-1]
            if extension == 'csv':
                data = pd.read_csv(data)
            if extension in ('xls', 'xlsx'):
                engine = 'openpyxl' if extension == 'xlsx' else 'xlrd'
                data = pd.read_excel(data, engine=engine)
        if isinstance(data, dict):
            data = pd.DataFrame(data)
        if not isinstance(data, pd.DataFrame):
            raise NotImplementedError(
                'Data format not supported.'
            )
        self._data = data

### Casing
    @property
    def case(self):
        """Highest priority case-setter for new columns."""
        return self._case

    @case.setter
    def case(self, case):
        self._case = case
        if isinstance(case, str) and case is not None:
            case = getattr(str, case)
        
        cases = [str.lower, str.title, str.capitalize, str.upper, None]
        if case not in cases:
            raise ValueError(
                'Only string-class case types are allowed, or None. '
                'Choose one of [str.lower, str.title, str.capitalize, '
                'str.upper, None].'
            )
        
        # Update cases in plate attributes
        if case is not None:
            new_column_dict = {
                key: [case(col) for col in value]
                for key, value in self.column_dict.items()
            }
        
            # Update column dict
            self._column_dict = new_column_dict
            
            # Update casing in order, since that does not change
            columns = [(k1, case(k2)) for (k1, k2) in self.mi_df.columns]
            self._well = case(self._well)
            self.mi_df.columns = pd.MultiIndex.from_tuples(columns)
            self.mi_df.index.name = self._well
            
            # Reset dataframe
            self.df = self._from_midf()

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
        wells = self.df[self._well]

        # If no explicit input, assume False and switch conditionally
        if padding is None:
            self._zero_padding = False
            padded = [True for well in wells if _infer_padding(well)]

            if padded:
                self._zero_padding = True

        self.mi_df.index = wells.apply(pad, padded=self.zero_padding)
        self.df = self._from_midf()

### Value name
    @property
    def value_name(self):
        """Sets value name from `value_name`, or sets to 'value',
        unless obtained from the final column of a DataFrame.
        """
        return self._value_name

    @value_name.setter
    def value_name(self, value_name):
        self._value_name = value_name
        # Rearrange data
        values = self._values
        try:
            values.remove(value_name)
        except ValueError:
            pass
        values.append(value_name)
        self.values = values

### Primary descriptors
    @property
    def locations(self):
        """Each column in the data that specifies location information"""
        return self._locations

    @locations.setter
    def locations(self, locations):        
        # Ensure base locations are still there, and well is first
        base_locs = [self._well, self._row, self._col]
        for base_loc in base_locs:
            if base_loc not in locations:
                if base_loc == self._well:
                    locations = [self._well, *locations]
                else:
                    locations.append(base_loc)
        
        self._locations = locations
        
        # Remove if found in annotations
        ann_check = set(self.locations) & set(self.annotations)
        if ann_check:
            self._annotations = [ann for ann in self._annotations
                                 if ann not in ann_check]
        
        # Same for values
        val_check = set(self.locations) & set(self.values)
        if val_check:
            self._values = [val for val in self._values
                            if val not in val_check]
        
        # Reset column_dict to rearrange dataframe
        self.column_dict = {
            'locations': self.locations,
            'annotations': self.annotations,
            'values': self.values,
        }

    @property
    def annotations(self):
        """Each column in the data that specifies additional information"""
        return self._annotations

    @annotations.setter
    def annotations(self, annotations):
        self._annotations = annotations
        
        # Remove if found in locations
        loc_check = set(self.annotations) & set(self.locations)
        if loc_check:
            self._locations = [loc for loc in self._locations
                                 if loc not in loc_check]
        
        # Same for values
        val_check = set(self.annotations) & set(self.values)
        if val_check:
            self._values = [val for val in self._values
                            if val not in val_check]
        
        # Reset column dict to rearrange dataframe
        self.column_dict = {
            'locations': self.locations,
            'annotations': self.annotations,
            'values': self.values,
        }

    @property
    def values(self):
        """Each column in the data that specifies value information"""
        return self._values

    @values.setter
    def values(self, values):
        # Check that there is at least one value
        if not values:
            raise ValueError(
               'Plate must contain at least one value.'
            )
        
        self._values = values
        
        # Remove if found in locations
        loc_check = set(self.values) & set(self.locations)
        if loc_check:
            self._locations = [loc for loc in self._locations
                                 if loc not in loc_check]
        
        # Same for annotations
        ann_check = set(self.values) & set(self.annotations)
        if ann_check:
            self._annotations = [ann for ann in self._annotations
                                 if ann not in ann_check]
        
        # Reset column dict to rearrange dataframe
        self.column_dict = {
            'locations': self.locations,
            'annotations': self.annotations,
            'values': self.values,
        }

        # Update value name
        self._value_name = self.values[-1]

    @property
    def column_dict(self):
        return self._column_dict

    @column_dict.setter
    def column_dict(self, column_dict):
        self._column_dict = column_dict

        # Confirm values list still has members
        if not column_dict['values']:
            # If not, reset it and raise error
            old_values = list(self.mi_df.xs('values', axis=1).columns)
            column_dict['values'] = old_values
            for attr_list in (self.locations, self.annotations):
                for val in old_values:
                    if val in attr_list:
                        attr_list.remove(val)
            raise ValueError(
                'Plate must contain at least one value.'
            )
        # Ensure base locations are still there
        locs = column_dict['locations']
        base_locs = [self._well, self._row, self._col]
        for base_loc in base_locs:
            if base_loc not in locs:
                if base_loc == self._well:
                    locs = [self._well, *locs]
                else:
                    locs.append(base_loc)
      
        column_dict['locations'] = locs

        # Re-arrange DataFrame
        # Get current multi-index df dict
        mi_df = self.mi_df.reset_index(col_level=1, col_fill='locations')
        mi_dict = mi_df.to_dict()
       
        # Re-arrange columns
        new_dict = {}
        # Iterate through key pairs
        for key1, value in column_dict.items():
            for key2 in value:
                try:
                    # Grab data from same key pair
                    series = mi_dict[(key1, key2)]
                except KeyError:
                    # If attribute key has changed, grab data from df
                    series = self.df[key2]
                # Store in dictionary
                new_dict[(key1, key2)] = series
     
        # Assign as new mi_df and sort
        self.mi_df = pd.DataFrame(new_dict)
        self.mi_df = self.mi_df.sort_values(
            by=[('locations', loc) for loc in self.locations[1:]]
        ).reset_index(drop=True)
        self.mi_df = self.mi_df.set_index(('locations', self._well))
        self.mi_df.index.name = self._well

        # Reset dataframe
        self.df = self._from_midf()

        # Set each grouping
        self._locations = self.column_dict['locations']
        self._annotations = self.column_dict['annotations']
        self._values = self.column_dict['values']

###########################
# DataFrame construction
###########################
    def _generate_df(self):
        """Parses the column names in the initial DataFrame. Returns the
        strings found for 'well', and 'value_name'. Everything is
        assumed to work in this function (i.e, no checks performmed)
        since this only runs after check_inputs(Plate) is run.
        """
        self.df = self.data.copy()
        column_names = list(self.df.columns)

        # Deal with simple data first
        if column_names[-1] is None:
            if self.value_name is None:
                self._value_name = self._set_case('value')

            if self._case is None:
                # Check casing on value_name
                cases = _infer_casing(self.value_name)

                # Assign case for well string (self._well)
                if not cases:
                    cases.append('lower')
                case = getattr(str, cases[0])
                
                self._well = case('well')

            else:
                # If case is enforced, enforce it
                case = self._set_case
                self._value_name = case(self.value_name)
            
            # Apply to generated column names
            self._well = case('well')
            self._row = case('row')
            self._col = case('column')

            # Update data
            column_names[0] = self._well
            column_names[-1] = self.value_name
            self.df.columns = column_names

        # Now deal with any generic DataFrame
        if self.value_name is None:
            self._value_name = column_names[-1]
        else:
            # Move value_name to end of dataframe
            vals = self.df[self.value_name].values
            del self.df[self.value_name]
            self.df[self.value_name] = vals

        # Determine well string
        self._well = [col for col in column_names if col.lower() == 'well'][0]

        # Move well to front
        vals = self.df[self._well].values
        del self.df[self._well]
        self.df.insert(0, self._well, vals)

        # Generate row and column info
        row = [col for col in self.df.columns if col.lower() == 'row']
        col = [col for col in self.df.columns if col.lower() == 'column']

        if not row:
            # Keep earlier string, if it was made
            try:
                row.append(self._row)
            except AttributeError:
                row.append('row')
        if not col:
            # Keep earlier string, if it was made
            try:
                col.append(self._col)
            except AttributeError:
                col.append('column')
        self._row = self._set_case(row[0])
        self._col = self._set_case(col[0])
        try:
            del self.df[self._row]
            del self.df[self._col]
        except KeyError:
            pass

        # Generate row and column data
        rows = [well[0] for well in self.df[self._well]]
        cols = [int(well[1:]) for well in self.df[self._well]]

        # Add in correct order
        self.df.insert(1, self._col, cols)
        self.df.insert(1, self._row, rows)

        return self.df, self._well, self._row, self._col

    def _generate_mi_df(self):
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

    def _from_midf(self):
        """Create df from mi df"""
        self.df = self.mi_df.copy()
        self.df = self.df.reset_index(col_level=1)
        self.df.columns = self.df.columns.droplevel(0)
        return self.df

###########################
# Plate methods
###########################

    def set_as_location(self, loc, idx=-1):
        """Sets a column as a location"""
        plate = self.copy()

        # Check column
        check_df_col(plate.df, loc, 'location')

        # Allow idx arg to rearrange instead of fail by removing loc if present
        if loc in plate.locations:
            plate.locations.remove(loc)

        # Set up new locations attribute
        locs = plate._locations
        
        if idx == -1:
            locs.append(loc)
        else:
            idx += 1
            locs = [
                *locs[:idx],
                loc,
                *locs[idx:]
            ]

        plate.locations = locs

        return plate

    def set_as_value(self, new_values=None, value_name=None):
        """Sets columns in the Plate DataFrame as values.
        
        Parameters:
        -----------
        new_values: str or list of str
            A list of column names to be set as values.
        value_name: str
            Which value should be set as the main (-1 index) value.
        """
        plate = self.copy()

        if set(plate.values) & set(new_values):
            raise ValueError(
                'Cannot set current values as new values.'
            )
        # Set as list
        if new_values is not None:
            if not isinstance(new_values, list):
                new_values = [new_values]
                values = new_values + plate.values

        # Update plate.value_name
        if value_name is not None:
            values.remove(value_name)
            values.append(value_name)
        else:
            value_name = values[-1]

        # Move main value to end of vals list
        if value_name not in [*plate.values, *values]:
            raise ValueError(
                f"'{value_name}' not found in list of values. Pick one of "\
                f"{plate.values} or pass new_values='{value_name}'."
            )
      
        plate.values = values

        return plate
      
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
        plate = self.copy()
        
        # Check that everything passes, return type.
        annotation_type = check_annotations(self, annotations)

        if annotation_type == dict:
            # Unpack dictionary and assign
            for column in annotations.keys():

                working_annotations = well_regex(annotations[column],
                                                 padded=plate.zero_padding)

                # Check for default
                default = None
                acceptable_kwargs = ('default', 'standard', 'else', 'other')
                for key in working_annotations.keys():
                    if key.lower() in acceptable_kwargs:
                        default = working_annotations[key]

                # Make new columns
                key = ('annotations', column)
                plate.mi_df[key] = plate.mi_df.index.map(working_annotations.get)
                plate.mi_df[key] = plate.mi_df[key].replace({None: default})

            new_annotations = [col for col in annotations.keys()
                               if col not in plate.annotations]
            
            plate.annotations = [*plate.annotations, *new_annotations]

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
            wells = [f'{row}{column}'
                     for (row, column) in zip(df_map['row'], df_map['column'])]
            df_map['well'] = [pad(well, plate.zero_padding) for well in wells]

            # Drop columns that are *entirely* nans
            df_map = df_map.dropna(axis='columns', how='all')

            # Switch to None
            df_map = df_map.replace({np.nan: None})

            # Standardize case and merge
            df_map.columns = [plate._set_case(col)
                             for col in df_map.columns]

            mergers = [plate._set_case(col)
                      for col in ['well', 'column', 'row']]

            plate.df = plate.df.merge(df_map, on=mergers)

            # Update annotations
            new_annotations = [col for col in df_map
                               if col not in mergers
                               and col not in plate.annotations]
           
            plate.annotations = [*plate.annotations, *new_annotations]

        return plate


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
        explicitly scale from 0 to 1 'zero=True'. Alternatively, scales
        relative to a specific assignment of a condition column, i.e. to 'Standard' within the condition 'Controls' can be set to a value
        of 1 via the kwarg `to='Controls=Standard'`. Additionally can
        assign a lower 0 value in the same way.

        Parameters:
        -----------
        value: str or list of str, default None
            Name of column to normalize, default being value_name.
        to: str, default None
            Which group to set as the normal (1) value. If None, the max
            value for each column in `value` is set to 1 and all other
            values are scaled to this. If a condition is passed, e.g.,
            `to='Controls=Standard'`, the mean of the wells labeled
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
        plate = self.copy()

        # Determine how to update the value
        # TODO: does this need a warning for True when type(value) == list?
        if isinstance(value, list) and isinstance(update_value, str):
            if update_value not in value:
                raise ValueError(
                    f"Given update value '{update_value}' not found in list of values to be normalized."
                )

        # Get value list ready
        if value is None:
            value = plate.value_name
        if not isinstance(value, list):
            values = [value]
        else:
            values = value

        # Set up groups
        if not isinstance(groupby, (tuple, list)):
            groupby = [groupby]

        for group in groupby:
            check_df_col(plate.df, group, name='groupby')

        # Group or create fake groupby object
        unique_dfs = (plate.df.groupby(groupby) if groupby != [None]
                      else [(None, plate.df.copy())])

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

            # After adding normalized values, store in df_list
            df_list.append(sub_df)

        # Merge dataframes from groupby
        mergers = [plate._well,
                   *[elem for elem in groupby if elem is not None]]
        full_df = plate.df[mergers].merge(
            pd.concat(df_list), on=mergers
        )
        
        # Add each new value
        for value in values:
            norm_string = f'{prefix}{value}'
            plate.mi_df[('values', norm_string)] = full_df[norm_string].values
            
            # Update plate.values list
            if norm_string not in plate.values:
                val_idx = plate.values.index(value)

                # Add norm value to the left of value
                plate.values = [
                    *plate.values[:val_idx],
                    norm_string,
                    *plate.values[val_idx:]
                ]
        
        # Clean up
        plate.df = plate._from_midf()
        if update_value:
            if isinstance(update_value, str):
                update_string = f'{prefix}{update_value}'
            else:
                update_string = norm_string
            
            plate.value_name = update_string
            plate.values.remove(update_string)
            plate.values = [*plate.values, update_string]

        return plate
  
