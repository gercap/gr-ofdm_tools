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

import math, struct, socket
from gnuradio import gr
import subprocess
from operator import add
import gnuradio.gr.gr_threading as _threading

from gnuradio import fft
import gnuradio.filter as grfilter
from gnuradio import blocks
from gnuradio.filter import window
import pmt
import numpy as np

class local_worker(gr.hier_block2):

    def __init__(self, fft_len, sample_rate, average, rate, max_tu, data_precision):
        gr.hier_block2.__init__(self,
            "ascii plot",
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
            gr.io_signature(0,0,0))
        self.fft_len = fft_len
        self.sample_rate = sample_rate
        self.average = average
        self.rate = rate
        self.max_tu = max_tu-2 #reserve two bytes for segmentation

        self.data_precision = data_precision         

        if data_precision:
            print '32bit FFT in use (more bandwidth and precision)'
        else:
            print '16bit FFT in use (less bandwidth and precision)'
     
        self.msgq = gr.msg_queue(2)

        #######BLOCKS#####
        self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
        self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
         max(1, int(self.sample_rate/self.fft_len/self.rate)))

        mywindow = window.blackmanharris(self.fft_len)
        self.fft = fft.fft_vcc(self.fft_len, True, mywindow, True)

        self.c2mag2 = blocks.complex_to_mag_squared(self.fft_len)
        self.avg = grfilter.single_pole_iir_filter_ff(self.average, self.fft_len)
        self.log = blocks.nlog10_ff(10, self.fft_len,
                                -10*math.log10(self.fft_len)                # Adjust for number of bins
                                -10*math.log10(self.sample_rate))                # Adjust for sample rate

        self.sink = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq, True)

        #register message out to other blocks
        self.message_port_register_hier_out("pdus")

        self._packet_source = packet_source()

        #####CONNECTIONS####
        self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.avg, self.log, self.sink)
        self.msg_connect(self._packet_source, "out", self, "pdus")

        ####THREADS####
        self._main = main_thread(self.msgq, self._packet_source, self.max_tu, self.data_precision)

    def set_rate(self, rate):
        self.rate = rate
        self.one_in_n.set_n(max(1, int(self.sample_rate/self.fft_len/self.rate)))

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.set_rate(self.rate)

    def set_average(self, average):
        self.average = average
        self.avg.set_taps(average)

    def set_data_precision(self, data_precision):
        self.data_precision = data_precision
        self._main.data_precision = data_precision
        if data_precision:
            print '-->Local: 32bit FFT in use (more bandwidth and precision)'
        else:
            print '-->Local: 16bit FFT in use (less bandwidth and precision)'

    def get_sample_rate(self):
        return self.sample_rate

    def get_average(self):
        return self.average

#main thread
class main_thread(_threading.Thread):
    def __init__(self, rcvd_data, packet_source, max_tu, data_precision):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_data = rcvd_data
        self.packet_source = packet_source
        self.max_tu = max_tu
        self.data_precision = data_precision

        self.state = None
        self.keep_running = True #set to False to stop thread's main loop
        self.start()
    
    def run(self):
        while self.keep_running:
            msg = self.rcvd_data.delete_head()
            itemsize = int(msg.arg1())
            nitems = int(msg.arg2())

            data = msg.to_string() # get the body of the msg as a string

            if nitems > 1:
                print 'nitems exceeded'
                start = itemsize * (nitems - 1)
                data = data[start:start+itemsize]

            self.packet_source.send_packet(data, self.max_tu, self.data_precision)

class packet_source(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(self,"packet_source",[],[])
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        print "reporting fft data on localhost UDP 5005 port"
        # set up message ports
        self.message_port_register_out(pmt.intern("out"));

    def send_packet(self, data, max_tu, data_precision):

        if not data_precision:
            fft_data = np.fromstring(data, np.float32)
            fft_data = fft_data.astype(np.float16, copy=False)
            data = fft_data.tostring()

        fragments = int(math.ceil(len(data)/(float(max_tu))))+1 #4 bytes per fft bin

        j = 0
        for i in range(fragments):

            n_frags = struct.pack('!B', fragments) #1 byte for number of fragments
            frag_id = struct.pack('!B', i) #1 byte for fragment number
            frag = data[j:j+max_tu]
            if i == fragments-1: frag = data[j:]
            
            frame = n_frags + frag_id + frag #construct frame

            self.udp_sock.sendto(frame, ("127.0.0.1", 5005))

            data_pmt = pmt.make_u8vector(len(frame), ord(' '))
            # Copy all characters to the u8vector:
            for i in range(len(frame)): pmt.u8vector_set(data_pmt, i, ord(frame[i]))
            self.message_port_pub(pmt.intern("out"), pmt.cons(pmt.PMT_NIL, data_pmt))            
            j += max_tu
