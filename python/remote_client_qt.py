#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2017 germanocapela gmail com.
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
# 
# This block intends to be used with local_worker from gr-ofdm_tools
# 
#
import pyqt
import struct
from pyqt.plotter_base import *
import zlib
import numpy as np

class remote_client_qt(plotter_base):
    def __init__(self, tune_freq, sample_rate, show_axes, precision, hold_max, label="", *args):
        plotter_base.__init__(self, blkname="remote_client_qt", label=label, *args)
        self.message_port_register_in(pmt.intern("pdus"));
        self.set_msg_handler(pmt.intern("pdus"), self.handler);
        self.sample_rate = sample_rate
        self.tune_freq = tune_freq
        self.show_axes = show_axes
        if precision:
            self.data_type = np.float32
        else:
            self.data_type = np.int8

        if show_axes:
            self.toggle_axes()

        self.hold_max = hold_max

        self.strt = True
        self.reasembled_frame = ''
        self.max_fft_data = np.array([])

        # set up curves
        curve = Qwt.QwtPlotCurve("MAX");
        curve.attach(self);
        self.curves.append(curve);
        curve.setPen( Qt.QPen(Qt.Qt.blue) );

        curve = Qwt.QwtPlotCurve("PSD");
        curve.attach(self);
        self.curves.append(curve);
        curve.setPen( Qt.QPen(Qt.Qt.green) );

        self.curve_data = [([],[]), ([],[])];

    def set_reset_max(self, reset_max):
        self.strt = True
        self.set_hold_max(True)

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.alignScales()

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq
        self.alignScales()

    def get_tune_freq(self):
        return self.tune_freq

    def get_sample_rate(self):
        return self.sample_rate

    def set_show_axes(self, show_axes):
        self.show_axes = show_axes
        self.toggle_axes()

    def set_precision(self, precision):
        if precision:
            self.data_type = np.float32
            print '-->Remote: 32bit FFT in use (more bandwidth and precision)'
        else:
            self.data_type = np.int8
            print '-->Remote: 8bit FFT in use (less bandwidth and precision)'

    def set_hold_max(self, hold_max):
        self.hold_max = hold_max
        print '<>', self.hold_max

    def handler(self, msg_pmt):
        #meta = pmt.to_python(pmt.car(msg_pmt))

        # Collect message, convert to Python format:
        msg = pmt.cdr(msg_pmt)
        # Convert to string:
        msg_str = "".join([chr(x) for x in pmt.u8vector_elements(msg)])
        n_frags = struct.unpack('!B', msg_str[0])[0] #obtain number of fragments
        frag_id = struct.unpack('!B', msg_str[1])[0] #obtain fragment number
        msg_str = msg_str[2:] #grab fft data

        if n_frags == 1: #single fragment
            try:
                fft_data = np.fromstring(msg_str, self.data_type)
                #fmt = "<%df" % (len(msg_str) // 4)
                #fft_data = struct.unpack(fmt, msg_str)

                if len(self.max_fft_data) != len(fft_data):
                    self.max_fft_data = fft_data

                if self.strt:
                    self.max_fft_data = fft_data
                    self.strt = False

                # pass data
                axis = self.sample_rate/2*np.linspace(-1, 1, len(fft_data)) + self.tune_freq
                self.max_fft_data = np.maximum(self.max_fft_data, fft_data)
                self.curve_data[0] = (axis/1e6, fft_data);
                if self.hold_max:
                    self.curve_data[1] = (axis/1e6, self.max_fft_data);
                # trigger update
                self.emit(QtCore.SIGNAL("updatePlot(int)"), 0)

            except:
                print '-->Remote: error reassembling data(1)'

        else: #multiple fragments situation
            self.reasembled_frame += msg_str
            if frag_id == n_frags - 1: #final fragment
                try:
                    fft_data = np.fromstring(self.reasembled_frame, self.data_type)
                    #fmt = "<%df" % (len(self.reasembled_frame) // 4)
                    #fft_data = struct.unpack(fmt, self.reasembled_frame)

                    if len(self.max_fft_data) != len(fft_data):
                        self.max_fft_data = fft_data

                    if self.strt:
                        self.max_fft_data = fft_data
                        self.strt = False

                    # pass data
                    axis = self.sample_rate/2*np.linspace(-1, 1, len(fft_data)) + self.tune_freq
                    self.max_fft_data = np.maximum(self.max_fft_data, fft_data)
                    self.curve_data[1] = (axis/1e6, fft_data);
                    if self.hold_max:
                        self.curve_data[0] = (axis/1e6, self.max_fft_data);
                    # trigger update
                    self.emit(QtCore.SIGNAL("updatePlot(int)"), 0)

                    self.reasembled_frame = ''
                except:
                    print '-->Remote: error reassembling data(2)'
            else:
                pass
