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

class clipper(gr.sync_block):
	"""
	forces a clipping to input signal
	"""
	def __init__(self, clip_fact):
		gr.sync_block.__init__(
			self,
			name="clipper",
			in_sig=[np.complex64],
			out_sig=[np.complex64],
		)
		self.clip_fact = clip_fact

	def work(self, input_items, output_items):
		real = np.real(input_items[0])
		imag = np.imag(input_items[0])

		output_items[0][:] = (map(complex, np.clip(real, -self.clip_fact, self.clip_fact), np.clip(imag, -self.clip_fact, self.clip_fact)))
		return len(output_items[0])

	def set_clip_fact(self, clip_fact):
		self.clip_fact = clip_fact

	def get_clip_fact(self):
		return self.clip_fact
