#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 Germano Capela.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import numpy as np
from gnuradio import gr
import time

def calc_papr(measure):
	meanSquareValue = np.vdot(measure,np.transpose(measure))/len(measure)
	peakValue = max(measure*np.conjugate(measure))
	paprSymbol = peakValue/meanSquareValue
	return paprSymbol.real

class papr_sink(gr.sync_block):
	"""
	docstring for block papr_sink
	"""
	def __init__(self, size):
		gr.sync_block.__init__(self,
			name="papr_sink",
			in_sig=[(np.complex64, size)],
			out_sig=None)
		self.papr = 0
		self.vect_size = size

	def work(self, input_items, output_items):
		in0 = input_items[0][:]
		for el in in0: self.set_papr(calc_papr(el))
		return 0

	def set_papr(self, papr):
		self.papr = papr

	def level(self):
		return self.papr

	def set_size(self, size):
		self.vect_size = size

	def size(self):
		return self.vect_size
