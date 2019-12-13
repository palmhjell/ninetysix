import ninetysix as ns

import pytest


# Well regex
def test_well_regex_comma_row():
    assignment_dict = {
        '[A,C]1': 1
    }

    desired_dict = {
        'A1': 1,
        'C1': 1,
    }

    output_dict = ns.parsers.well_regex(assignment_dict)

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

    output_dict = ns.parsers.well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_comma_col():
    assignment_dict = {
        'A[1,2]': 1
    }

    desired_dict = {
        'A1': 1,
        'A2': 1,
    }

    output_dict = ns.parsers.well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_hyphen_col():
    assignment_dict = {
        'A[1-3]': 1
    }

    desired_dict = {
        'A1': 1,
        'A2': 1,
        'A3': 1,
    }

    output_dict = ns.parsers.well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_comma_col_padded():
    assignment_dict = {
        'A[1,2]': 1
    }

    desired_dict = {
        'A01': 1,
        'A02': 1,
    }

    output_dict = ns.parsers.well_regex(assignment_dict, padded=True)

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

    output_dict = ns.parsers.well_regex(assignment_dict, padded=True)

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

    output_dict = ns.parsers.well_regex(assignment_dict)

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

    output_dict = ns.parsers.well_regex(assignment_dict, padded=True)

    assert output_dict == desired_dict