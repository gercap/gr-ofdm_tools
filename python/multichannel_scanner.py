#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2016 germanocapela at gmail dot com

# Selects top 2 channels and outputs to 2 x message out, so they can be used by a frequency translating fir filter

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

from gnuradio import gr, gru, fft
from gnuradio import blocks
from gnuradio.filter import window
import numpy as np
import gnuradio.gr.gr_threading as _threading
from scipy import signal as sg
import threading, os, pmt, subprocess, time, datetime, Queue, sys, pmt
from os.path import expanduser
from operator import add
import platform

from ofdm_cr_tools import frange, movingaverage, src_power, logger, file_logger
from ofdm_tools import message_pdu

plat = platform.system()
if plat == "Windows":
    clear = lambda: os.system('cls')
elif plat == "Linux" or plat == "Darwin":
    clear = lambda: os.system('clear')

class multichannel_scanner(gr.hier_block2):
    def __init__(self, fft_len, sens_per_sec, sample_rate, channel_space = 1,
     search_bw = 1, tune_freq = 0, trunc_band = 1, verbose = False, output = False, subject_channels = []):
        gr.hier_block2.__init__(self,
            "multichannel_scanner",
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
            gr.io_signature(0, 0, 0))
        self.fft_len = fft_len #lenght of the fft for spectral analysis
        self.sens_per_sec = sens_per_sec #number of measurements per second (decimates)
        self.sample_rate = sample_rate 
        self.channel_space = channel_space #channel space for analysis
        self.search_bw = search_bw #search bandwidth within each channel
        self.tune_freq = tune_freq #center frequency
        self.verbose = verbose
        self.trunc_band = trunc_band
        self.output = output
        self.subject_channels = subject_channels
        self.subject_channels_pwr = np.array([1.0]*len(self.subject_channels))

        #gnuradio msg queues
        self.msgq0 = gr.msg_queue(2)
        
        #output top 4 freqs
        self.top4 = [self.subject_channels[0], self.subject_channels[0], self.subject_channels[0], self.subject_channels[0]]
        
        #register message out to other blocks
        self.message_port_register_hier_out("freq_out_0")
        self.message_port_register_hier_out("freq_out_1")
        self.message_port_register_hier_out("freq_out_2")
        self.message_port_register_hier_out("freq_out_3")
        self.message_port_register_hier_out("freq_msg_PDU")

        #######BLOCKS#####
        self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
        self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
         max(1, int(self.sample_rate/self.fft_len/self.sens_per_sec)))

        mywindow = window.blackmanharris(self.fft_len)
        self.fft = fft.fft_vcc(self.fft_len, True, (), True)

        self.c2mag2 = blocks.complex_to_mag_squared(self.fft_len)
        self.multiply = blocks.multiply_const_vff(np.array([1.0/float(self.fft_len**2)]*fft_len))

        #MSG sinks PSD data
        self.sink0 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq0, True)

        #MSG output blocks to other blocks
        self.message_out0 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[0])), 1000)
        self.message_out1 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[1])), 1000)
        self.message_out2 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[2])), 1000)
        self.message_out3 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[3])), 1000)
        self.PDU_messages = message_pdu(None)

        #####CONNECTIONS####
        print 'connecting elements'
        self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.multiply, self.sink0)
        print 'elements connected'

        #MSG output
        self.msg_connect(self.message_out0, "strobe", self, "freq_out_0")
        self.msg_connect(self.message_out1, "strobe", self, "freq_out_1")
        self.msg_connect(self.message_out2, "strobe", self, "freq_out_2")
        self.msg_connect(self.message_out3, "strobe", self, "freq_out_3")
        self.msg_connect(self.PDU_messages, 'out', self, 'freq_msg_PDU')

        self._output_data = output_data(self.output, self.subject_channels, self.subject_channels_pwr,
            self.PDU_messages)

        self._basic_spectrum_watcher = basic_spectrum_watcher(self.msgq0, sens_per_sec, self.tune_freq,
         self.channel_space, self.search_bw, self.fft_len, self.sample_rate, trunc_band, verbose,
          self.subject_channels, self.set_freqs, self._output_data)

    def set_freqs(self, freq0, freq1, freq2, freq3):
        self.message_out0.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq0-self.tune_freq) )) #send differencial frequency
        self.message_out1.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq1-self.tune_freq) ))
        self.message_out2.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq2-self.tune_freq) ))
        self.message_out3.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq3-self.tune_freq) ))

#ascii thread
class output_data(_threading.Thread):
    def __init__(self, output, subject_channels, subject_channels_pwr, PDU_messages):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.output = output
        self.subject_channels = subject_channels # list of channels to be analysed by the flanck detector
        self.subject_channels_pwr = subject_channels_pwr
        self.top4 = [subject_channels[0]]*4
        self.PDU_messages = PDU_messages


        self.state = None
        self.keep_running = True #set to False to stop thread's main loop
        self.start()

    def run(self):       
        while self.keep_running:
            if self.output == 't':
                #clear()
                print "%-10s %-10s" % ('Freq [Hz]', 'Power [dB]')
                for f in self.top4:
                    print "%-10s %-10s" % (f, self.subject_channels_pwr[self.subject_channels.index(f)])
                    self.PDU_messages.post_message("freq", str(f))
                print ""                

            time.sleep(1)

#queue wathcer to log statistics and max power per channel
class basic_spectrum_watcher(_threading.Thread):
    def __init__(self, rcvd_data, sens_per_sec, tune_freq, channel_space,
         search_bw, fft_len, sample_rate, trunc_band, verbose, subject_channels, set_freqs, output_data):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_data = rcvd_data

        self.sens_per_sec = sens_per_sec
        self.tune_freq = tune_freq
        self.channel_space = channel_space
        self.search_bw = search_bw
        self.fft_len = fft_len
        self.sample_rate = sample_rate
        self.trunc_band = trunc_band
        self.trunc = sample_rate-trunc_band
        self.trunc_ch = int(self.trunc/self.channel_space)/2
        self.subject_channels = subject_channels
        self.set_freqs = set_freqs
        self.output_data = output_data

        self.Fr = float(self.sample_rate)/float(self.fft_len) #freq resolution
        self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
        self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
        self.bb_freqs = frange(-self.sample_rate/2, self.sample_rate/2, self.channel_space) #baseband freqs
        self.srch_bins = self.search_bw/self.Fr #binwidth for search
        self.ax_ch = frange(self.Fstart, self.Ffinish, self.channel_space) #subject channels
        if self.trunc > 0:
            self.ax_ch = self.ax_ch[self.trunc_ch:-self.trunc_ch] #trunked subject channels
        
        self.plc = np.array([0.0]*len(self.ax_ch))

        self.subject_channels = subject_channels # list of channels to be analysed by the flanck detector
        self.idx_subject_channels = [0]*len(self.subject_channels) # aux list to index ax_ch
        k = 0
        for channel in subject_channels:
            self.idx_subject_channels[k] = self.ax_ch.index(channel)
            k += 1
        self.subject_channels_pwr = np.array([1.0]*len(self.subject_channels))

        self.verbose = verbose
        self.keep_running = True
        self.start()

    def run(self):
        while self.keep_running:
            msg = self.rcvd_data.delete_head()

            itemsize = int(msg.arg1())
            nitems = int(msg.arg2())
            s = msg.to_string()
            if nitems > 1:
                start = itemsize * (nitems - 1)
                s = s[start:start+itemsize]

            #convert received data to numpy vector
            float_data = np.fromstring (s, np.float32)

            #scan channels
            self.spectrum_scanner(float_data)
            self.publish()

    #function that scans channels
    def spectrum_scanner(self, samples):

        #measure power for each channel
        power_level_ch = src_power(samples, self.fft_len, self.Fr, self.sample_rate, self.bb_freqs, self.srch_bins)

        #trunc channels outside useful band (filter curve) --> trunc band < sample_rate
        if self.trunc > 0:
            power_level_ch = power_level_ch[self.trunc_ch:-self.trunc_ch]
        
        #share data among threads
        self.plc = self.plc * 0.6 + np.array(power_level_ch) * 0.4


    def publish(self):
        k = 0
        for channel in self.idx_subject_channels:
            self.subject_channels_pwr[k] = 10*np.log10(self.plc[channel])
            k += 1

        ff = self.subject_channels_pwr.argsort()[-4:][::-1]
        self.set_freqs(self.subject_channels[ff[0]], self.subject_channels[ff[1]],
         self.subject_channels[ff[2]], self.subject_channels[ff[3]])

        self.output_data.subject_channels_pwr = self.subject_channels_pwr
        self.output_data.top4 = [self.subject_channels[ff[0]], self.subject_channels[ff[1]],
         self.subject_channels[ff[2]], self.subject_channels[ff[3]]]

