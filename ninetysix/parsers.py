from itertools import product

def pad(col, padded=True):
    """Converts to or from zero-padded column names
    (e.g., A1 <-> A01)
    """
    # Standardize to int, then back to str
    col = str(int(col))
    if padded:
        if len(col) == 1:
            col = '0'+col
    return col

def well_regex(input_dict, padded=False):
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
    padded : bool, default False
        Whether or not to zero pad the wells, i.e., return keys of
        the form 'A01', 'A02', ... , 'E09', 'E10'. Will occur
        regardless of the regex key form (both '[A-E][1-10]' and
        '[A-E][01-10]' will return A1 if padded=False, else A01.  
    """
    # Set up the new dict
    parsed_dict = input_dict.copy()

    # Deal with zero-padding in well
    rows = list('ABCDEFGHJLMNOP')
    cols = [pad(str(i), padded) for i in range(1, 25)]

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
                    
                    # Get the range (need to pad here)
                    hyphen_split = [pad(val, padded) for val in col_set.split('-')]
                    
                    # Append range to list
                    if len(hyphen_split) > 1:
                        col_range = cols[cols.index(hyphen_split[0]):cols.index(hyphen_split[1])+1]
                        matching_cols += col_range
                    
                    # Else append single value to list
                    else:
                        matching_cols += hyphen_split

            else:
                matching_cols = [pad(col, padded) for col in assignment[-1]]

            wells = [''.join(well)
                for well in product(matching_rows, matching_cols)]

        # Non-regex
        else:
            wells = [assignment]
        
        for well in wells:
            parsed_dict[well] = value

    return parsed_dict
