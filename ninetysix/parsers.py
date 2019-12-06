from itertools import product


def well_regex(input_dict, padded=False):
    """Parses simple regex-like syntax for
    well keys in an assignment dictionary.
    """
    # Set up the new dict
    parsed_dict = input_dict.copy()

    # Deal with zero-padding in well
    def pad(col, padded=padded):
        if padded:
            if len(col) == 1:
                col = '0'+col
        return col

    rows = list('ABCDEFGH')
    cols = [pad(str(i)) for i in range(1, 13)]

    for column in parsed_dict.keys():
        working_dict = parsed_dict[column]
        for assignment, value in working_dict.items():
            
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
                        hyphen_split = [pad(val) for val in col_set.split('-')]
                        
                        # Append range to list
                        if len(hyphen_split) > 1:
                            col_range = cols[cols.index(hyphen_split[0]):cols.index(hyphen_split[1])+1]
                            matching_cols += col_range
                        
                        # Else append single value to list
                        else:
                            matching_cols += hyphen_split

                else:
                    matching_cols = assignment[-1]

                wells = [''.join(well)
                    for well in product(matching_rows, matching_cols)]

                parsed_dict[column] = {
                    well: value for well in wells
                }

            # Non-regex
            else:
                parsed_dict[column][assignment] = value

    return parsed_dict