import numpy as np
import pandas as pd


def check_inputs(Plate):
	"""Checks that all inputs are provided correctly.

	Returns True if all tests pass.
	"""
	
	# Well-value pairs
	if Plate.wells:

		if Plate.values is None:
			raise ValueError(
				"kwarg 'values' must be specified if 'wells' is not None."
			)

		if len(Plate.wells) != len(Plate.values):
			raise ValueError(
				"Arrays for 'wells' and 'values' are not the same length."
			)

		# Check that all wells are string values
		bad_types = [type(well) for well in Plate.wells if type(well) != str]

		if bad_types:
			raise TypeError(
				f"Well values must be of type string, found: {set(bad_types)}"
			)
	
	# Data (list of lists/tuples or DataFrame/dict)
	if Plate.data is not None:

		if Plate.wells is not None:
			raise ValueError(
				"kwarg 'wells' cannot be specified if 'data' is not None."
			)

		if Plate.values:
			if type(Plate.values) is not str:
				raise TypeError(
					"kwarg 'values' must take a string argument "\
					"(name of the value) if 'data' is not None."
				)

		df = None
		if type(Plate.data) == type(pd.DataFrame()):
			df = Plate.data
		elif type(Plate.data) == dict:
			df = pd.DataFrame(Plate.data)

		if df is not None:
			well_cols = [col for col in df.columns if col.lower() == 'well']
			if 'well' not in well_cols:
				raise ValueError(
					"No 'well' value found in your DataFrame columns."
				)
			if len(well_cols) != 1:
				raise ValueError(
					"Multiple 'well' columns detected in your data."
				)

			well_col = well_cols[0]
			bad_types = [type(well) for well in df[well_col] if type(well) != str]

			if bad_types:
				raise TypeError(
					f"Well values must be of type string, found: {set(bad_types)}"
				)

			if Plate.value_name:
				if Plate.value_name not in df.columns:
					raise ValueError(
						f"'{Plate.value_name}' not present in your data, "\
						f"options are: {list(df.columns)}"
					)

	return True