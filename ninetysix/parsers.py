"""
Tools for parsing and regularizing data found in Plate objects.
"""

from itertools import product


def _infer_casing(string):
    """Guesses the case of a string."""
    # Acceptable cases
    cases = ['lower', 'title', 'capitalize', 'upper']

    found_cases = [case for case in cases
                   if getattr(str, case)(string) == string]

    return found_cases

def _infer_padding(well):
    """Guesses if a well is padded (A01) or not (A1). Returns False
    if it cannot be guessed (on double-digit column).
    """
    # Assume False
    padded = False

    row = well[0]
    str_col = well[1:]
    int_col = str(int(str_col))

    # Return True is str form != int form
    if len(str_col) != len(int_col):
        padded = True

    return padded

def pad(well, padded=True):
    """Converts to or from zero-padded column names
    (e.g., A1 <-> A01)
    """
    # Get row and column
    row = well[0]
    col = well[1:]

    # Convert to int then to str (gives non-padded)
    col = str(int(col))

    # Pad
    if padded:
        if len(col) == 1:
            col = '0'+col

    well = row+col
    
    return well

def well_regex(input_dict, padded=None):
    """Parses simple regex-like syntax for well keys in a
    dictionary and expands it. Accepts up to 396-well plate
    nomenclature (A–P, 1–24). If no regex-like structure is
    detected, will return the same dictionary.

    Parameters
    ----------
    input_dict : dictionary
        A dictionary potentially containing keys of the form
        '[A-E][1-10]', which would expand to 50 keys of the form
        'A1', 'A2', ... , 'E9', 'E10', each with the same value as
        the original key.
    padded : bool, default None
        Whether or not to zero pad the wells, i.e., return keys of
        the form 'A01', 'A02', ... , 'E09', 'E10'. Will occur
        regardless of the regex key form (both '[A-E][1-10]' and
        '[A-E][01-10]' will return A1 if padded=False, else A01.
        If None, infers padding from inputs if possible. 
    """
    # Set up the new dict
    parsed_dict = input_dict.copy()

    # Acceptable values to search
    rows = list('ABCDEFGHJLMNOP')
    cols = [str(i) for i in range(1, 25)]

    # Set up a dictionary that can change during the loop
    working_dict = parsed_dict.copy()
    for assignment in working_dict.keys():

        # Pop the assignment and store
        value = parsed_dict.pop(assignment)
        
        # If regex-ed
        if '[' in assignment:

            # Determine if rows, columns, or both are regex-ed
            row = True if assignment[0] == '[' else False
            col = True if assignment[-1] == ']' else False
            
            if row:
                matching_rows = []
                
                # Get the row regex contents
                row_vals = assignment[1:assignment.find(']')]
                
                # Iterate through each group, if given
                comma_split = row_vals.split(',')
                for row_set in comma_split:
                    
                    # Get the range
                    hyphen_split = row_set.split('-')
                    
                    # Append range to list
                    if len(hyphen_split) > 1:
                        row_range = rows[rows.index(hyphen_split[0]):rows.index(hyphen_split[1])+1]
                        matching_rows += row_range
                        
                    # Else append single value to list
                    else:
                        matching_rows += hyphen_split

            else:
                matching_rows = assignment[0]
                
            if col:
                matching_cols = []
                
                # Get the column regex contents
                col_vals = assignment[assignment.rfind('[')+1:-1]
                
                # Iterate through each group, if given
                comma_split = col_vals.split(',')
                for col_set in comma_split:
                    
                    # Get the range
                    hyphen_split = [val for val in col_set.split('-')]
                    
                    # Append range to list
                    if len(hyphen_split) > 1:
                        padding = set([_infer_padding(('_'+val))
                                    for val in hyphen_split
                                    if int(val) < 10])

                        if len(padding) > 1:
                            raise ValueError(
                            f'Inconsistent zero padding in "{col_vals}"; '\
                            'use the same form for best results.'
                        )

                        if all(padding):
                            cols = [pad('_'+col)[1:] for col in cols]

                        start = cols.index(hyphen_split[0])
                        end = cols.index(hyphen_split[1])+1

                        col_range = cols[start:end]
                        matching_cols += col_range
                    
                    # Else append single value to list
                    else:
                        matching_cols += hyphen_split

            else:
                if row:
                    col_start = assignment.find(']')
                else:
                    col_start = 0
                
                matching_cols = [assignment[col_start+1:]]

            wells = [''.join(well)
                for well in product(matching_rows, matching_cols)]

        # Non-regex
        else:
            wells = [assignment]
        
        for well in wells:
            parsed_dict[well] = value

    # Infer padding
    if padded is None:
        padded = [True for well in parsed_dict
                   if _infer_padding(well)]
    # Pad
    if padded:
        padded_dict = parsed_dict.copy()
        for well in parsed_dict:
            value = padded_dict.pop(well)
            try:
                padded_dict[pad(well)] = value
            except ValueError:
                padded_dict[well] = value
    
        parsed_dict = padded_dict

    return parsed_dict
