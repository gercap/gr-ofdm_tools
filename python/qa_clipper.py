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

from gnuradio import gr, gr_unittest
from gnuradio import blocks
from clipper import clipper #import python block
import numpy as np
import ofdm_tools_swig as ofdm_tools #import c++ / swig block to be used under python code

class qa_clipper (gr_unittest.TestCase):

	def setUp (self):
		self.tb = gr.top_block ()

	def tearDown (self):
		self.tb = None

	def test_001_clipper (self):
		clip_fact = 1
		src_data = (2, -2, -0.5, 0.5, clip_fact, -clip_fact)
		expected_result = (1, -1, -0.5, 0.5, clip_fact, -clip_fact)
		src = blocks.vector_source_c (src_data)
		clip = clipper (clip_fact)
		dst = blocks.vector_sink_c ()
		self.tb.connect (src, clip)
		self.tb.connect (clip, dst)
		self.tb.run ()
		result_data = dst.data ()
		self.assertFloatTuplesAlmostEqual (expected_result, result_data, 6)

	def test_002_clipper_cc (self):
		clip_fact = 0.5
		src_data = (2+2j, -2-2j, -0.5+0.5j, 0.5, 3-3j, -1)
		expected_result = (0.5+0.5j, -0.5-0.5j, -0.5+0.5j, 0.5, 0.5-0.5j, -0.5)
		src = blocks.vector_source_c (src_data)
		clip = ofdm_tools.clipper_cc (clip_fact)
		dst = blocks.vector_sink_c ()
		self.tb.connect (src, clip)
		self.tb.connect (clip, dst)
		self.tb.run ()
		result_data = dst.data ()
		self.assertFloatTuplesAlmostEqual (expected_result, result_data, 6)

if __name__ == '__main__':
	gr_unittest.main ()
