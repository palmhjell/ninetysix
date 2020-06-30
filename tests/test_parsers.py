import ninetysix as ns
from ninetysix.parsers import pad, _infer_padding, well_regex

import pytest

# Padding
def test_pad():
    well = 'A1'
    padded = pad(well)
    assert padded == 'A01'

    well = 'A01'
    padded = pad(well)
    assert padded == 'A01'
    assert well == padded

    well = 'A10'
    padded = pad(well)
    assert padded == 'A10'

    well = 'A10'
    padded = pad(well)
    assert padded == 'A10'
    assert well == padded

def test_unpad():
    well = 'A1'
    padded = pad(well, padded=False)
    assert padded == 'A1'
    assert well == padded

    well = 'A01'
    padded = pad(well, padded=False)
    assert padded == 'A1'

    well = 'A10'
    padded = pad(well, padded=False)
    assert padded == 'A10'
    assert well == padded

    well = 'A10'
    padded = pad(well, padded=False)
    assert padded == 'A10'

def test_infer_padding():
    wells = ['A1', 'A01', 'A10']
    padded = [False, True, False]

    for well, pad in zip(wells, padded):
        assert _infer_padding(well) == pad

# Well regex
def test_well_regex_comma_row():
    assignment_dict = {
        '[A,C]1': 1,
        '[A,C]10': 1,
    }

    desired_dict = {
        'A1': 1,
        'C1': 1,
        'A10': 1,
        'C10': 1,
    }

    output_dict = well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_hyphen_row():
    assignment_dict = {
        '[A-C]1': 1
    }

    desired_dict = {
        'A1': 1,
        'B1': 1,
        'C1': 1,
    }

    output_dict = well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_comma_col():
    assignment_dict = {
        'A[1,2]': 1
    }

    desired_dict = {
        'A1': 1,
        'A2': 1,
    }

    output_dict = well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_hyphen_col():
    assignment_dict = {
        'A[9-11]': 1
    }

    desired_dict = {
        'A9': 1,
        'A10': 1,
        'A11': 1,
    }

    output_dict = well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_comma_col_padded():
    assignment_dict = {
        'A[1,2]': 1
    }

    desired_dict = {
        'A01': 1,
        'A02': 1,
    }

    output_dict = well_regex(assignment_dict, padded=True)

    assert output_dict == desired_dict

def test_well_regex_hyphen_col_padde():
    assignment_dict = {
        'A[1-3]': 1
    }

    desired_dict = {
        'A01': 1,
        'A02': 1,
        'A03': 1,
    }

    output_dict = well_regex(assignment_dict, padded=True)

    assert output_dict == desired_dict

def test_well_regex_multiline():
    assignment_dict = {
        '[A-C]1': 1,
        '[D,F][1-3]': 2,
        'G12': 3,
    }

    desired_dict = {
        'A1': 1,
        'B1': 1,
        'C1': 1,
        'D1': 2,
        'D2': 2,
        'D3': 2,
        'F1': 2,
        'F2': 2,
        'F3': 2,
        'G12': 3
    }

    output_dict = well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_multiline_padded():
    assignment_dict = {
        '[A-C]1': 1,
        '[D,F][1-3]': 2,
        'G12': 3,
    }

    desired_dict = {
        'A01': 1,
        'B01': 1,
        'C01': 1,
        'D01': 2,
        'D02': 2,
        'D03': 2,
        'F01': 2,
        'F02': 2,
        'F03': 2,
        'G12': 3,
    }

    output_dict = well_regex(assignment_dict, padded=True)

    assert output_dict == desired_dict
