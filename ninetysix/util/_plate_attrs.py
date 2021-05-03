from functools import wraps

import pandas as pd
try:
    import pandas_flavor as pf
except ImportError:
    pf = None

import ninetysix as ns

# For placing viz plot methods on Plate
def _get_viz_attr(Plate, plot):
    attr = getattr(ns.viz, plot)
    @wraps(attr)
    def wrapper(*args, **kwargs):
        return attr(Plate, *args, **kwargs)

    return plot, wrapper

def _set_viz_attrs(Plate):
    plots = [func for func in dir(ns.viz) if 'plot_' in func]
    for plot in plots:
        attr_pair = _get_viz_attr(Plate, plot)
        setattr(Plate, *attr_pair)


# For placing pandas attributes/functions on Plate
# rather only being accessible via Plate.df.
# pandas_flavor (pf) helps return pd.DataFrame output as Plate
if pf is not None:
    @pf.register_dataframe_method
    def as_plate(df, locations, values):
        """Adds a method .as_plate() to wrap pd.DataFrame as ns.Plate"""
        # Create plate object with correct value_name
        plate = ns.Plate(df, value_name=values[-1])

        # Add locations
        plate.locations = locations

        # Add values
        plate.values = values
        
        return plate

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
                    output = attr(Plate.df, *args, **kwargs).as_plate(
                        Plate.locations, Plate.values
                    )
                
                return output
            
            attr_pair = (attr_name, wrapper)
        
        else:
            attr = getattr(Plate.df, attr_name)
            attr_pair = (attr_name, attr)

        return attr_pair

    def _set_pandas_attrs(Plate):
        """Assigns pandas attributes/methods to Plate from Plate.df"""
        _pd_attrs = dir(pd.DataFrame)
        _pd_deprecated = ['as_blocks', 'blocks', 'ftypes', 'is_copy', 'ix']
        _ns_incompat = ['values']
        ignore = [*_pd_deprecated, *_ns_incompat]
        
        for attr_name in _pd_attrs:
            if (attr_name in ignore) or (attr_name[0] == '_'):
                continue
            attr_pair = _get_pandas_attrs(Plate, attr_name)
            setattr(Plate, *attr_pair)
