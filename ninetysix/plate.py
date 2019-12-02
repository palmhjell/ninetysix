import numpy as np
import pandas as pd

from .checkers import check_inputs


class Plate():

	def __init__(
		self,
		data=None,
		wells=None,
		values=None,
		value_name=None,
		assign_wells=None,
	):

		# Initial setup
		self.data = data
		self.wells = wells
		self.values = values
		self._value_name = value_name
		self._passed = check_inputs(self)
		
		# For easier unit testing: make dataframe only when passing
		if self._passed:
			self.df = self._make_df()

		if assign_wells is not None:
			self.assign_wells(assign_wells)

	def _repr_html_(self):
		return self.df._repr_html_()

	@property
	def value_name(self):
		if (self._value_name is None) & (type(self.values) == str):
			self._value_name = self.values
		return self._value_name
	
	def _make_df(self):
		if type(self.data) == type(pd.DataFrame()):
			df = self.data
		elif type(self.data) == dict:
			df = pd.DataFrame(self.data)
		elif type(self.values) == str:
			df = pd.DataFrame(data=self.data, columns=['well', self.value_name])
		else:
			if self.wells is not None:
				data = zip(self.wells, self.values)
			else:
				data = self.data
			if self.value_name is None:
				df = pd.DataFrame(data=data, columns=['well', 'value'])
			else:
				df = pd.DataFrame(data=data, columns=['well', self.value_name])

		# Inefficiently(?) move to -1 index
		if self.value_name:
			values = df[self.value_name]
			del df[self.value_name]
			df[self.value_name] = values

		return df

	def assign_wells(self, assignment):
		"""
		"""
		pass

