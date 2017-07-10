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
import subprocess
from operator import add
import gnuradio.gr.gr_threading as _threading

from gnuradio import fft
import gnuradio.filter as grfilter
from gnuradio import blocks
from gnuradio.filter import window
import ofdm_tools as of

class remote_client(gr.hier_block2):

    def __init__(self, fft_len, sample_rate, tune_freq, width, height):
        gr.hier_block2.__init__(self,
            "remote_client",
            gr.io_signature(0,0,0),
            gr.io_signature(0,0,0))
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

        #register message out to other blocks
        self.message_port_register_hier_in("pkt_in")
        #packet generator
        self.packet_receiver = of.chat_blocks.chat_receiver(callback=self.rx_callback)

        #####CONNECTIONS####
        #MSG output
        self.msg_connect(self, "pkt_in", self.packet_receiver, "in")

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

    def rx_callback(self, payload):
        fft_data = np.fromstring (payload, np.float32)
        ascii_data = self._ascii_plotter.make_plot(fft_data)
        print ascii_data