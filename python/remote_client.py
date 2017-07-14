#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2017 Germano Capela at gmail.com
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


import numpy as np, time, math, os
from gnuradio import gr
import ofdm_tools as of
import pmt

class remote_client(gr.sync_block):

    def __init__(self, fft_len, sample_rate, tune_freq, width, height):
        gr.sync_block.__init__(self, "remote_client", [], [])
        self.fft_len = fft_len
        self.sample_rate = sample_rate
        self.tune_freq = tune_freq
        if width == 0 and height == 0:
            rows, columns = os.popen('stty size', 'r').read().split()
            self.height = int(rows)-5
            self.width = int(columns)/2-10
        else:
            self.height = height
            self.width = width

        self.message_port_register_in(pmt.intern("pdus"));
        self.set_msg_handler(pmt.intern("pdus"), self.handler);

        ####ASCII PLOTTER####
        self._ascii_plotter = of.ascii_plotter(self.width, self.height, self.tune_freq, self.sample_rate, self.fft_len)

    def set_width(self, width):
        self._ascii_plotter.width = width
        self._ascii_plotter.updateWindow()

    def set_height(self, height):
        self._ascii_plotter.height = height
        self._ascii_plotter.updateWindow()

    def set_sample_rate(self, sample_rate):
        self._ascii_plotter.sample_rate = sample_rate
        self._ascii_plotter.updateWindow()

    def set_tune_freq(self, tune_freq):
        self._ascii_plotter.tune_freq = tune_freq
        self._ascii_plotter.updateWindow()

    def get_tune_freq(self):
        return self.tune_freq

    def get_sample_rate(self):
        return self.sample_rate

    def handler(self, msg_pmt):

        meta = pmt.to_python(pmt.car(msg_pmt))
        # Collect message, convert to Python format:
        msg = pmt.cdr(msg_pmt)
        # Convert to string:
        msg_str = "".join([chr(x) for x in pmt.u8vector_elements(msg)])

        fft_data = np.fromstring(msg_str, np.float32)

        ascii_data = self._ascii_plotter.make_plot(fft_data)
        print ascii_data 