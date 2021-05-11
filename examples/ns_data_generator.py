"""
Generates well-value datasets to use for visualization examples.
"""

import numpy as np
import pandas as pd
import ninetysix as ns

ROWS = list('ABCDEFGH')
COLS = [i for i in range(1, 13)]
WELLS = [f'{row}{col}' for row in ROWS for col in COLS]

def generate_plate_data(
    standard=(30, 1),
    negative=(3, 0.5),
    experiment=(20, 6),
    annotated=False,
    multi_val=False,
    seed=8675309,
):
    """Assumes standards in wells [A-D]10, negatives
    in wells [E-H]10.
    """
    np.random.seed(seed)
    standard_vals = list(np.random.normal(*standard, size=4))
    negative_vals = list(np.random.normal(*negative, size=4))
    
    
    
    values = [np.nan for _ in WELLS]
    for i, well in enumerate(WELLS):
        if well in ['A10', 'B10', 'C10', 'D10']:
            values[i] = standard_vals.pop()
        elif well in ['E10', 'F10', 'G10', 'H10']:
            values[i] = negative_vals.pop()
        else:
            values[i] = np.random.normal(*experiment)
            
    df = pd.DataFrame(zip(WELLS, values), columns=['well', 'value'])
    
    if annotated:
        annotations = {
            'controls': {
                '[A-D]10': 'standard',
                '[E-H]10': 'negative',
            },
        }
        df = ns.Plate(df, annotate=annotations).df
    
    if multi_val:
        vals = df['value'].copy()
        vals = vals.apply(lambda x: x+np.random.normal(0, 1))
        vals = vals.apply(lambda x: x*np.random.normal(1, 0.1))
        vals = vals*10
        df['value_1'] = df['value']
        del df['value']
        df['value_2'] = vals
    
    return df

def generate_condition_plate(seed=8675301):
    """Generates a plate with replicate conditions
    in each well
    """
    condition_1 = {
        '[A,E][1-4]': 1,
        '[A,E][5-8]': 2,
        '[A,E][9-12]': 3,
        '[B,F][1-4]': 4,
        '[B,F][5-8]': 5,
        '[B,F][9-12]': 6,
        '[C,G][1-4]': 7,
        '[C,G][5-8]': 8,
        '[C,G][9-12]': 9,
        '[D,H][1-4]': 10,
        '[D,H][5-8]':11,
        '[D,H][9-12]': 12,
    }
    condition_2 = {
        '[A-D][1-12]': True,
        '[E-H][1-12]': False,
    }
    
    data = []
    # For each condition 1
    for condition in condition_1:
        wells = list(ns.parsers.well_regex({condition: None}))
        # Pick 4 good ones, 4 bad ones (condition 2)
        i = condition_1[condition]
        values = [
            *np.random.normal(i*2, i*0.1, size=4),
            *np.random.normal(i, i*0.3, size=4)
        ]
        data += list(zip(wells, values))
        
    df = ns.Plate(pd.DataFrame(data, columns=['well', 'value'])).df.sort_values(['row', 'column'])
    del df['row']
    del df['column']
    
    return df
