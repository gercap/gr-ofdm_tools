#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2017 <+YOU OR YOUR COMPANY+>.
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

from gnuradio import analog
from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes


class clipper(gr.hier_block2):

    def __init__(self, clipping_factor):
        gr.hier_block2.__init__(
            self, "Clipper",
            gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
            gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
        )

        ##################################################
        # Variables
        ##################################################
        self.clipping_factor = clipping_factor

        ##################################################
        # Blocks
        ##################################################
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.analog_rail_ff_re = analog.rail_ff(-clipping_factor, clipping_factor)
        self.analog_rail_ff_im = analog.rail_ff(-clipping_factor, clipping_factor)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_rail_ff_im, 0), (self.blocks_float_to_complex_0, 1))
        self.connect((self.analog_rail_ff_re, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_complex_to_float_0, 1), (self.analog_rail_ff_im, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.analog_rail_ff_re, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self, 0))
        self.connect((self, 0), (self.blocks_complex_to_float_0, 0))

    def get_clipping_factor(self):
        return self.clipping_factor

    def set_clipping_factor(self, clipping_factor):
        self.clipping_factor = clipping_factor
        self.analog_rail_ff_re.set_lo(-self.clipping_factor)
        self.analog_rail_ff_re.set_hi(self.clipping_factor)
        self.analog_rail_ff_im.set_lo(-self.clipping_factor)
        self.analog_rail_ff_im.set_hi(self.clipping_factor)