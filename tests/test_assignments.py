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

    assignments = {
        'condition' : {
            'A1': 1
        }
    }

    desired_df = pd.DataFrame({
        'well': ['A1'],
        'condition': [1],
        'value': [1]
    })

    output_df = ns.Plate(data=df, assign_wells=assignments).df

    pass # assert output_df.equals(desired_df)

# Dicts with regex-like wells
def test_regex_dict():
    df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'value': [1, 2],
    })

    assignments = {
        'condition' : {
            'A[1-2]': 1
        }
    }

    desired_df = pd.DataFrame({
        'well': ['A1', 'A2'],
        'condition': [1, 1],
        'value': [1, 2]
    })

    output_df = ns.Plate(data=df, assign_wells=assignments).df

    pass # assert output_df.equals(desired_df)