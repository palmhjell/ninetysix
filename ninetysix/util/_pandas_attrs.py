import pandas as pd
import pandas_flavor as pf
from functools import wraps

import ninetysix as ns

# For placing pandas attributes/functions on Plate
# rather only being accessible via Plate.df.
# pandas_flavor (pf) helps return pd.DataFrame output as Plate
@pf.register_dataframe_method
def as_plate(df, value):
    """Adds a method .as_plate() to wrap pd.DataFrame as ns.Plate"""
    return ns.Plate(df, value_name=value)

def _get_pandas_attrs(Plate, attr_name):
    """Creates wrappers for pandas functions to Plate.df"""
    attr = getattr(pd.DataFrame, attr_name)
    if callable(attr):
        @wraps(attr)
        def wrapper(*args, **kwargs):
            
            # head and tail are not used as new Plates; return pd obj is fine
            if attr_name in ('head', 'tail'):
                output = attr(Plate.df, *args, **kwargs)

            # Default to index=False
            elif attr_name in ('to_csv', 'to_excel'):
                if 'index' in kwargs:
                    index = kwargs.pop('index')
                else:
                    index = False
                output = attr(Plate.df, index=index, *args, **kwargs)

            # .as_plate() method returns DataFrame back as Plate object
            else:
                output = attr(Plate.df, *args, **kwargs).as_plate(Plate.value_name)
            
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
