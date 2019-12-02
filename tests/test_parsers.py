import ninetysix as ns

import pytest


# Well regex
def test_well_regex_row_comma():
    assignment_dict = {
        'condition': {
            '[A,C]1': 1
        }
    }

    desired_dict = {
        'condition': {
            'A1': 1,
            'C1': 1,
        }
    }

    output_dict = ns.parsers.well_regex(assignment_dict)

    assert output_dict == desired_dict

def test_well_regex_row_hyphen():
    assignment_dict = {
        'condition': {
            '[A-C]1': 1
        }
    }

    desired_dict = {
        'condition': {
            'A1': 1,
            'B1': 1,
            'C1': 1,
        }
    }

    output_dict = ns.parsers.well_regex(assignment_dict)

    assert output_dict == desired_dict
    

def test_well_regex_just_column():
    parser = ns.parsers.well_regex
    pass

def test_well_regex_both():
    parser = ns.parsers.well_regex
    pass