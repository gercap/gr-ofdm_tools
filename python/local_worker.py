#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2017Germano Capela at gmail.com
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

import math
from gnuradio import gr
import subprocess
from operator import add
import gnuradio.gr.gr_threading as _threading

from gnuradio import fft
import gnuradio.filter as grfilter
from gnuradio import blocks
from gnuradio.filter import window
import ofdm_tools as of

class local_worker(gr.hier_block2):

    def __init__(self, fft_len, sample_rate, tune_freq, average, rate):
        gr.hier_block2.__init__(self,
            "ascii plot",
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
            gr.io_signature(0,0,0))
        self.fft_len = fft_len
        self.sample_rate = sample_rate
        self.average = average
        self.tune_freq = tune_freq
        self.rate = rate

        self.msgq = gr.msg_queue(2)

        #######BLOCKS#####
        self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
        self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
         max(1, int(self.sample_rate/self.fft_len/self.rate)))

        mywindow = window.blackmanharris(self.fft_len)
        self.fft = fft.fft_vcc(self.fft_len, True, (), True)

        self.c2mag2 = blocks.complex_to_mag_squared(self.fft_len)
        self.avg = grfilter.single_pole_iir_filter_ff(self.average, self.fft_len)
        self.log = blocks.nlog10_ff(10, self.fft_len,
                                -10*math.log10(self.fft_len)                # Adjust for number of bins
                                -10*math.log10(self.sample_rate))                # Adjust for sample rate

        self.sink = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq, True)

        #register message out to other blocks
        self.message_port_register_hier_out("pkt_out")
        #packet generator
        self.packet_generator = of.chat_blocks.chat_sender()

        #####CONNECTIONS####
        self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.avg, self.log, self.sink)

        #MSG output
        self.msg_connect(self.packet_generator, "out", self, "pkt_out")

        ####THREADS####
        self._main = main_thread(self.msgq, self.packet_generator)

    def set_rate(self, rate):
        self.rate = rate
        self.one_in_n.set_n(max(1, int(self.sample_rate/self.fft_len/self.rate)))

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.set_rate(self.rate)

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq

    def set_average(self, average):
        self.average = average
        self.avg.set_taps(average)

    def get_tune_freq(self):
        return self.tune_freq

    def get_sample_rate(self):
        return self.sample_rate

    def get_average(self):
        return self.average


#main thread
class main_thread(_threading.Thread):
    def __init__(self, rcvd_data, packet_gen):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_data = rcvd_data
        self.packet_gen = packet_gen

        self.state = None
        self.keep_running = True #set to False to stop thread's main loop
        self.start()
    
    def run(self):
        while self.keep_running:
            msg = self.rcvd_data.delete_head()
            itemsize = int(msg.arg1())
            nitems = int(msg.arg2())

            s = msg.to_string()            # get the body of the msg as a string

            if nitems > 1:
                start = itemsize * (nitems - 1)
                s = s[start:start+itemsize]

            #fft_data = np.fromstring (s, np.float32)

            self.packet_gen.post_message(s)