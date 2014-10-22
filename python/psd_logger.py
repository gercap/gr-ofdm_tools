#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 germanocapela at gmail dot com
# log the psd after a peak hold
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
import gnuradio.filter as grfilter
from gnuradio import blocks
from gnuradio.filter import window
import numpy as np
import time, scipy.io
import gnuradio.gr.gr_threading as _threading

class psd_logger(gr.hier_block2):
	def __init__(self, fft_len, rate, sample_rate):
		gr.hier_block2.__init__(self,
			"psd_logger",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),
			gr.io_signature(0,0,0))
		self.fft_len = fft_len
		self.rate = rate
		self.sample_rate = sample_rate
		self.msgq = gr.msg_queue(2)
		self.log_file = open('/tmp/psd_log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S"),'w')

		self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
		self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
		 max(1, int(self.sample_rate/self.fft_len/self.rate)))

		mywindow = window.blackmanharris(self.fft_len)
		self.fft = fft.fft_vcc(self.fft_len, True, mywindow)
		power = 0
		for tap in mywindow:
			power += tap*tap

		self.c2mag = blocks.complex_to_mag(self.fft_len)

		self.sink = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq, True)
		self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag, self.sink)

		self._watcher = _queue_watcher(self.msgq, self.log_file)

class _queue_watcher(_threading.Thread):
	def __init__(self, rcvd_data, log_file):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data
		self.log_file = log_file
		self.mat_file = '/tmp/psd_log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S") + '.mat'
		self.keep_running = True
		self.start()

	def run(self):
		peak_vals = None
		while self.keep_running:


			msg = self.rcvd_data.delete_head()
			itemsize = int(msg.arg1())
			nitems = int(msg.arg2())

			if nitems > 1:
				start = itemsize * (nitems - 1)
				s = s[start:start+itemsize]

			payload = msg.to_string()
			complex_data = np.fromstring (payload, np.float32)
			peak_vals = np.maximum(complex_data, peak_vals)
			#self.log_file.write('psd ' + str(complex_data) + '\r')
			#scipy.io.savemat(self.mat_file, mdict={'psd': complex_data})
			np.save(self.mat_file, peak_vals)
