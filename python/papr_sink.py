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



class papr_sink(gr.sync_block):
	"""
	compute PAPR as a sink block
	"""
	def __init__(self, size):
		gr.sync_block.__init__(self,
			name="papr_sink",
			in_sig=[(np.complex64, size)],
			out_sig=None)
		self.papr = 0
		self.vect_size = size
		self.vct_data = [0, 0]

	def work(self, input_items, output_items):
		in0 = input_items[0][:]
		self.vct_data = in0[0]
		return len(in0)

	def set_papr(self, measure):
		meanSquareValue = np.vdot(measure,np.transpose(measure))/len(measure)
		peakValue = max(measure*np.conjugate(measure))
		paprSymbol = peakValue/meanSquareValue
		self.papr = paprSymbol.real

	def level(self):
		self.set_papr(self.vct_data)
		return self.papr

	def set_size(self, size):
		self.vect_size = size

	def size(self):
		return self.vect_size
