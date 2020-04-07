import numpy as np
import pandas as pd
import os

import ninetysix as ns

import pytest

# Simple df for all cases
df = pd.DataFrame({
    'well': ['A'+str(col) for col in range(1, 13)],
    'test': [1]*12,
})

# Check that it builds
def test_pandas_attrs_general():
    plate = ns.Plate(data=df, value_name='test')

    assert plate._pandas_attrs
    assert list(plate.columns) == ['well', 'row', 'column', 'test']

    plate = ns.Plate(data=df, value_name='test', pandas_attrs=False)

    assert not plate._pandas_attrs
    with pytest.raises(AttributeError):
        plate.columns

# Test that (most) pd.DataFrame methods return a ns.Plate object
def test_return_plate():
    plate = ns.Plate(data=df, value_name='test')
    new_obj = plate.sort_values('well')

    assert type(new_obj) == type(plate)

# Test that plate.to_csv() ignores index
def test_to_csv():
    plate = ns.Plate(data=df, value_name='test')
    
    plate.to_csv('temp.csv')
    plate_cols = list(pd.read_csv('temp.csv').columns)

    plate.to_csv('temp.csv', index=True)
    plate_true_cols = list(pd.read_csv('temp.csv').columns)
    
    plate.df.to_csv('temp.csv')
    df_cols = list(pd.read_csv('temp.csv').columns)

    os.remove('temp.csv')

    assert plate_cols == ['well', 'row', 'column', 'test']
    assert df_cols == ['Unnamed: 0', 'well', 'row', 'column', 'test']
    assert plate_true_cols == df_cols
