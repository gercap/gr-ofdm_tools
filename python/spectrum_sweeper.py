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

import math, struct,subprocess, time
from gnuradio import gr
from operator import add
import gnuradio.gr.gr_threading as _threading

from gnuradio import fft
import gnuradio.filter as grfilter
from gnuradio import blocks
from gnuradio.filter import window
import ofdm_tools as of
import pmt
import numpy as np
from scipy import signal as sg

#range floats
def frange(x, y, jump):
    out =[] 
    while x <= y:
        out.append(x)
        x += jump
    return out

class spectrum_sweeper(gr.hier_block2):

    def __init__(self, rf_receiver, receiver_type, fft_len, sample_rate, trunc_sample_rate, fstart, ffinish,
     rate, average, t_obs, tune_delay, max_tu):
        gr.hier_block2.__init__(self,
            "ascii plot",
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
            gr.io_signature(0,0,0))
        self.rf_receiver = rf_receiver
        self.receiver_type = receiver_type
        self.fft_len = fft_len
        self.sample_rate = sample_rate
        self.trunc_sample_rate = trunc_sample_rate
        self.fstart = fstart
        self.ffinish = ffinish
        self.rate = rate
        self.average = average
        self.max_tu = max_tu-2 #reserve two bytes for segmentation
        self.t_obs = t_obs*1e-3 #time window for observation
        self.vector_probe_pts = int(2**math.ceil(math.log(sample_rate*self.t_obs,2)))
        print 'number of samples per FFT block', self.vector_probe_pts
        self.tune_delay = tune_delay*1e-3
        self.tune_frequencies = frange(self.fstart+self.trunc_sample_rate/2, self.ffinish, self.trunc_sample_rate)
        if len(self.tune_frequencies)<1: #IN CASE SCANNING SR < TX SAMPLING RATE
            self.tune_frequencies = [(self.fstart + self.ffinish)/2]
        self.freq_resolution = float(self.sample_rate)/float(self.fft_len)
        self.excess_bins = int(math.floor((self.sample_rate - self.trunc_sample_rate)/2/self.freq_resolution))
        print 'excess_bins', self.excess_bins

        #not used, but available
        self.freq_axis = self.sample_rate/2*np.linspace(-1, 1, self.fft_len)
        if self.excess_bins > 0: self.freq_axis = self.freq_axis[(self.excess_bins):-(self.excess_bins)]

        #packet fragmentation to match MTU
        self.fragments = int(math.ceil((self.fft_len*4.0)/(self.max_tu))) #4 bytes per fft bin
        print 'data split in', self.fragments, 'fragments'

        self.msgq = gr.msg_queue(2)

        self.samples = [1e-10]*self.vector_probe_pts

        #######BLOCKS#####
        self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.vector_probe_pts)
        self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.vector_probe_pts,
         max(1, int(self.sample_rate/self.vector_probe_pts/self.rate)))
        self.sink = blocks.message_sink(gr.sizeof_gr_complex * self.vector_probe_pts, self.msgq, True)

        #register message out to other blocks
        self.message_port_register_hier_out("pdus")

        self._packet_source = packet_source()

        #####CONNECTIONS####
        self.connect(self, self.s2p, self.one_in_n, self.sink)
        self.msg_connect(self._packet_source, "out", self, "pdus")

        ####THREADS####
        self._data_colector = data_colector(self.msgq, self.set_samples)

        self._spectrum_stitcher = spectrum_stitcher(self.tune_frequencies, self.fft_len, self.sample_rate,
         self.excess_bins, self.rf_receiver, self.tune_delay, self.average, self.freq_axis, self.get_samples,
          self._packet_source, self.max_tu)

    def get_tune_delay(self):
        return self.tune_delay

    def set_tune_delay(self, tune_delay):
        self.tune_delay = tune_delay*1e-3
        self._spectrum_stitcher.set_tune_delay(tune_delay*1e-3)

    def get_samples(self):
        return self.samples

    def set_samples(self, samples):
        self.samples = samples

    def set_rate(self, rate):
        self.rate = rate
        self.one_in_n.set_n(max(1, int(self.sample_rate/self.fft_len/self.rate)))

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.set_rate(self.rate)

    def set_fstart(self, fstart):
        self.fstart = fstart

    def set_ffinish(self, ffinish):
        self.ffinish = ffinish

    def get_fstart(self, fstart):
        return self.fstart

    def get_ffinish(self, ffinish):
        return self.ffinish

    def get_sample_rate(self):
        return self.sample_rate

    def set_average(self, average):
        self.average = average
        self._spectrum_stitcher.set_average(average)

    def get_average(self):
        return self.average

class data_colector(_threading.Thread):
    def __init__(self, rcvd_data, set_samples):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_data = rcvd_data
        self.set_samples = set_samples

        self.state = None
        self.keep_running = True #set to False to stop thread's main loop
        self.start()
    
    def run(self):
        while self.keep_running:
            msg = self.rcvd_data.delete_head()
            itemsize = int(msg.arg1())
            nitems = int(msg.arg2())

            samples = msg.to_string()            # get the body of the msg as a string
            if nitems > 1:
                print 'nitems exceeded'
                start = itemsize * (nitems - 1)
                samples = samples[start:start+itemsize]
            self.set_samples(np.fromstring (samples, np.complex64))

class spectrum_stitcher(_threading.Thread):
    def __init__(self, tune_frequencies, fft_len, sample_rate, excess_bins, rf_receiver, tune_delay, average,
     freq_axis, get_samples, packet_source, max_tu):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.tune_frequencies = tune_frequencies
        self.fft_len = fft_len
        self.sample_rate = sample_rate
        self.excess_bins = excess_bins
        self.rf_receiver = rf_receiver
        self.tune_delay = tune_delay
        self.average = average
        self.freq_axis = freq_axis
        self.get_samples = get_samples
        self.packet_source = packet_source
        self.max_tu = max_tu

        self.state = None
        self.keep_running = True #set to False to stop thread's main loop
        self.start()

    def get_tune_delay(self):
        return self.tune_delay

    def set_tune_delay(self, tune_delay):
        self.tune_delay = tune_delay

    def get_average(self):
        return self.average

    def set_average(self, average):
        self.average = average

    def run(self):
        time.sleep(2)
        print 'frequencies', self.tune_frequencies

        while self.keep_running:
            psd = np.array([])
            psd_old = np.array([1e-10]*(self.fft_len-self.excess_bins*2)*len(self.tune_frequencies))
            #axis = np.array([])
            j = 0
            for f in self.tune_frequencies:
                try: self.rf_receiver.set_center_freq(f, 0)
                except: print 'cant tune receiver'
                time.sleep(self.tune_delay)
                vector = self.get_samples()

                _psd  = _src_power(vector, self.fft_len, self.sample_rate, self.excess_bins)
                psd = np.concatenate((psd, _psd), axis=0)
                #axis = np.concatenate((axis, self.freq_axis+self.tune_frequencies[j]), axis=0)
                j += 1

            psd = (1-self.average) * psd + self.average * psd_old
            psd_old = psd

            fmt = "<%df" % len(psd)
            self.packet_source.send_packet(struct.pack(fmt, *psd), self.max_tu)

class packet_source(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(self,"packet_source",[],[])

        # set up message ports
        self.message_port_register_out(pmt.intern("out"));

    def send_packet(self, data, max_tu):

        fragments = int(math.ceil(len(data)/(max_tu)))+1 #4 bytes per fft bin

        j = 0
        for i in range(fragments):

            n_frags = struct.pack('!B', fragments) #1 byte for number of fragments
            frag_id = struct.pack('!B', i) #1 byte for fragment number
            frag = data[j:j+max_tu]
            if i == fragments-1: frag = data[j:]
            
            frame = n_frags + frag_id + frag #construct frame

            data_pmt = pmt.make_u8vector(len(frame), ord(' '))
            # Copy all characters to the u8vector:
            for i in range(len(frame)): pmt.u8vector_set(data_pmt, i, ord(frame[i]))
            self.message_port_pub(pmt.intern("out"), pmt.cons(pmt.PMT_NIL, data_pmt))
            j += max_tu

def _src_power(vector, nFFT, samp_rate, excess_bins):

    #welch method
    welch_axis, psd_welch = sg.welch(vector, window='flattop', fs = samp_rate, nperseg= nFFT/4.0, nfft = nFFT)

    psd_fft = np.fft.fftshift(psd_welch)
    if excess_bins > 0:
        psd_fft = psd_fft[(excess_bins):-(excess_bins)]
    """ 

    win = sg.flattop(len(vector))
    #vector = vector * win
    psd_fft = np.fft.fftshift(((np.absolute(np.fft.fft(vector, nFFT)))**2)/(nFFT))
    if excess_bins > 0:
        psd_fft = psd_fft[(excess_bins):-(excess_bins)]
    """
    return 10*np.log10(psd_fft)