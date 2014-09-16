#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 Germano Capela at gmail.com.
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

import numpy as np, time, math
from ofdm_cr_tools import fft_plot_dB, welch_plot_dB, fft_plot_lin
from gnuradio import gr
import subprocess
from operator import add
import gnuradio.gr.gr_threading as _threading


#main cognitive engine thread
class main_thread(_threading.Thread):
	def __init__(self, fft_len, method, samp_rate, fc, average, refresh_rate, length, height):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.fft_len = fft_len
		self.method = method
		self.samp_rate = samp_rate
		self.fc = fc
		self.average = average
		self.refresh_rate = refresh_rate
		self.samples = np.array([0]*fft_len)
		self.length = length
		self.height = height

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.gnuplot = subprocess.Popen(["/usr/bin/gnuplot"], stdin=subprocess.PIPE)
		self.start()

	def run(self):
		print 'main thread started'
		time.sleep(self.refresh_rate)
		avg_0 = np.array([0]*self.fft_len)
		avg_1 = np.array([0]*self.fft_len)

		while self.keep_running:
			self.gnuplot.stdin.write("set term dumb "+str(self.length)+" "+str(self.height)+ " \n")
			self.gnuplot.stdin.write("plot '-' using 1:2 title 'GNURadio PSD' with linespoints \n")

			if self.average > 0:
				x_axis, psd = fft_plot_lin(self.samples, self.samp_rate, self.fc, self.fft_len)
				avg_0 = avg_1
				avg_1 = (1-self.average) * avg_1 + self.average * psd
				psd = 10*np.log10(avg_1+1e-20)
			else:
				if self.method == 'welch': x_axis, psd = welch_plot_dB(self.samples, self.samp_rate, self.fc, self.fft_len)
				else: x_axis, psd = fft_plot_dB(self.samples, self.samp_rate, self.fc, self.fft_len)

			for i,j in zip(x_axis, psd):
				self.gnuplot.stdin.write("%f %f\n" % (i,j))

			self.gnuplot.stdin.write("e\n")
			self.gnuplot.stdin.flush()
			time.sleep(self.refresh_rate)


class ascii_plot(gr.sync_block):

	def __init__(self, fft_len, method, samp_rate, fc, average, refresh_rate, length, height):
		gr.sync_block.__init__(self,
			name="ascii_plot",
			in_sig=[np.complex64],
			out_sig=None)
		self.fft_len = fft_len
		self.method = method
		self.samp_rate = samp_rate
		self.fc = fc
		self.average = average
		self.refresh_rate = refresh_rate
		self.main = main_thread(fft_len, method, samp_rate, fc, average, refresh_rate, length, height)

	def work(self, input_items, output_items):
		in0 = input_items[0][0:self.fft_len]
		self.main.samples = in0
		return len(in0)

	def set_length(self, length):
		self.main.length = length

	def set_height(self, height):
		self.main.height = height

	def get_fft_len(self):
		return self.fft_len

	def set_fft_len(self, fft_len):
		self.fft_len = fft_len
		self.main.fft_len = fft_len

	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate
		self.main.samp_rate = samp_rate

	def get_fc(self):
		return self.fc

	def set_fc(self, fc):
		self.fc = fc
		self.main.fc = fc

	def get_average(self):
		return self.average

	def set_average(self, average):
		self.average = average
		self.main.average = average
