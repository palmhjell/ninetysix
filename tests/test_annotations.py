import numpy as np
import pandas as pd

import ninetysix as ns

import pytest


# Dictionary
def test_simple_dict():
    df = pd.DataFrame({
        'well': ['A1'],
        'value': [1],
    })

    annotations = {
        'condition': {
            'A1': 1
        }
    }

    desired_df = pd.DataFrame({
        'well': ['A1'],
        'row': ['A'],
        'column': [1],
        'condition': [1],
        'value': [1]
    })

    output_df = ns.Plate(data=df, annotate=annotations).df

    assert output_df.equals(desired_df)

# Dicts with regex-like wells
def test_regex_dict():
    df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'value': [1, 2],
    })

    annotations = {
        'condition': {
            'A[1-2]': 1
        }
    }

    desired_df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'row': ['A', 'A'],
        'column': [1, 2],
        'condition': [1, 1],
        'value': [1, 2]
    })

    output_df = ns.Plate(data=df, annotate=annotations).df

    assert output_df.equals(desired_df)

def test_regex_dict_infer_padding():
    df = pd.DataFrame({
        'well': ['A01', 'A02'],
        'value': [1, 2],
    })

    annotations = {
        'condition': {
            'A[1-2]': 1
        }
    }

    desired_df = pd.DataFrame({
        'well': ['A01', 'A02'],
        'row': ['A', 'A'],
        'column': [1, 2],
        'condition': [1, 1],
        'value': [1, 2]
    })

    output_df = ns.Plate(data=df, annotate=annotations).df

    assert output_df.equals(desired_df)

def test_assign_in_post():
    df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'value': [1, 2],
    })

    annotations = {
        'condition': {
            'A[1-2]': 1
        }
    }

    desired_df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'row': ['A', 'A'],
        'column': [1, 2],
        'condition': [1, 1],
        'value': [1, 2]
    })

    plate = ns.Plate(data=df)

    plate = plate.annotate_wells(annotations)

    assert plate.df.equals(desired_df)
