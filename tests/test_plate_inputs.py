import numpy as np
import pandas as pd
import os

import ninetysix as ns

import pytest


# General set up
def test_value_name():
    df = pd.DataFrame({
        'well': ['A1'],
        'test': [1],
    })

    value_name = ns.Plate(data=df, value_name='test').value_name
    assert value_name == 'test'

def test_values_to_value_name():
    df = pd.DataFrame({
        'well': ['A1'],
        'test': [1],
    })

    value_name = ns.Plate(data=df, values='test').value_name
    assert value_name == 'test'

def test_nonstring_value():
    df = pd.DataFrame({
        'well': ['A1'],
        'test': [1],
    })

    with pytest.raises(TypeError):
        ns.Plate(data=df, values=4)

def test_auto_padding():

    # Auto-detect (lack of) padding
    df = pd.DataFrame({
        'well': ['A1'],
        'test': [1],
    })

    padded = ns.Plate(data=df, value_name='test').zero_padding

    assert not padded

    # Auto-detect padding
    df = pd.DataFrame({
        'well': ['A01'],
        'test': [1],
    })

    padded = ns.Plate(data=df, value_name='test').zero_padding

    assert padded

def test_explicit_padding():

    # Update to padded
    df = pd.DataFrame({
        'well': ['A1'],
        'test': [1],
    })

    output_df = ns.Plate(data=df, value_name='test', zero_padding=True).df

    desired_df = pd.DataFrame({
        'well': ['A01'],
        'row': ['A'],
        'column': [1],
        'test': [1],
    })

    assert output_df.equals(desired_df)

    # Update to un-padded
    df = pd.DataFrame({
        'well': ['A01'],
        'test': [1],
    })

    output_df = ns.Plate(data=df, value_name='test', zero_padding=False).df

    desired_df = pd.DataFrame({
        'well': ['A1'],
        'row': ['A'],
        'column': [1],
        'test': [1],
    })

    assert output_df.equals(desired_df)


# Well-value pair inputs
def test_two_lists():
    wells = ['A1', 'A2']
    values = [1, 2]

    assert ns.Plate(wells=wells, values=values)._passed

def test_nonstring_well():
    wells = ['A1', 2]
    values = [1, 2]

    with pytest.raises(TypeError):
        ns.Plate(wells=wells, values=values)

def test_tuple_of_tuples():
    wells = ('A1', 'A2')
    values = (1, 2)
    data = zip(wells, values)

    assert ns.Plate(data=data)._passed

def test_tuple_of_tuples_with_name():
    wells = ('A1', 'A2')
    values = (1, 2)

    assert ns.Plate(data=zip(wells, values), values='test')._passed
    assert ns.Plate(data=zip(wells, values), value_name='test')._passed

    output_df = ns.Plate(data=zip(wells, values), value_name='test').df
    desired_df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'row': ['A', 'A'],
        'column': [1, 2],
        'test': [1, 2],
    })

    assert output_df.equals(desired_df)

def test_tuple_of_tuples_with_value_list():
    wells = ('A1', 'A2')
    values = (1, 2)
    data = zip(wells, values)

    with pytest.raises(TypeError):
        ns.Plate(data=data, values=values)


# DataFrame/dict/path inputs
def test_simple_df():
    df = pd.DataFrame({
        'well': ['A1'],
        'value': [1],
    })

    assert ns.Plate(data=df)._passed
    assert ns.Plate(data=df).value_name == 'value'

def test_simple_dict():
    data = {
        'well': ['A1'],
        'value': [1],
    }

    assert ns.Plate(data=data)._passed
    assert ns.Plate(data=data).value_name == 'value'

def test_df_no_well():
    df = pd.DataFrame({
        'while': ['A1'],
        'value': [1],
    })

    with pytest.raises(ValueError):
        ns.Plate(data=df)

def test_df_too_many_well():
    df = pd.DataFrame({
        'well': ['A1'],
        'Well': ['A2'],
        'value': [1],
    })

    with pytest.raises(ValueError):
        ns.Plate(data=df)

def test_df_nonstring_well():
    df = pd.DataFrame({
        'well': ['A1', 2],
        'value': [1, 2],
    })

    with pytest.raises(TypeError):
        ns.Plate(data=df)

def test_df_with_value():
    df = pd.DataFrame({
        'well': ['A1'],
        'RT': [0.4],
        'area': [1],
    })

    assert ns.Plate(data=df, values='area')._passed

def test_df_move_value():
    input_df = pd.DataFrame({
        'well': ['A1'],
        'area': [1],
        'RT': [0.4],
    })

    desired_df = pd.DataFrame({
        'well': ['A1'],
        'row': ['A'],
        'column': [1],
        'RT': [0.4],
        'area': [1],
    })

    output_df = ns.Plate(data=input_df, values='area').df

    assert output_df.equals(desired_df)

def test_read_csv():

    df = pd.DataFrame({
        'well': ['A'+str(col) for col in range(1, 13)],
        'test': [1]*12,
    })

    temp = ns.Plate(data=df, value_name='test').to_csv('temp.csv')

    plate = ns.Plate('temp.csv')

    os.remove('temp.csv')

def test_read_excel():

    df = pd.DataFrame({
        'well': ['A'+str(col) for col in range(1, 13)],
        'test': [1]*12,
    })

    ns.Plate(data=df, value_name='test').to_excel('temp.xlsx')

    plate = ns.Plate('temp.xlsx')

    os.remove('temp.xlsx')
