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
from gnuradio import gr
import subprocess
from operator import add
import gnuradio.gr.gr_threading as _threading

from gnuradio import fft
import gnuradio.filter as grfilter
from gnuradio import blocks
from gnuradio.filter import window

class ascii_plot(gr.hier_block2):

	def __init__(self, fft_len, sample_rate, tune_freq, average, rate, width, height):
		gr.hier_block2.__init__(self,
			"ascii plot",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),
			gr.io_signature(0,0,0))
		self.fft_len = fft_len
		self.sample_rate = sample_rate
		self.average = average
		self.tune_freq = tune_freq
		self.rate = rate
		self.width = width
		self.height = height

		self.msgq = gr.msg_queue(2)

		#######BLOCKS#####
		self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
		self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
		 max(1, int(self.sample_rate/self.fft_len/self.rate)))

		mywindow = window.blackmanharris(self.fft_len)
		self.fft = fft.fft_vcc(self.fft_len, True, (), True)

		self.c2mag2 = blocks.complex_to_mag_squared(self.fft_len)
		self.avg = grfilter.single_pole_iir_filter_ff(1.0, self.fft_len)
		self.log = blocks.nlog10_ff(10, self.fft_len,
								-10*math.log10(self.fft_len)                # Adjust for number of bins
								-10*math.log10(self.sample_rate))                # Adjust for sample rate

		self.sink = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq, True)
		#####CONNECTIONS####
		self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.avg, self.log, self.sink)

		self._main = main_thread(self.msgq, self.fft_len, self.sample_rate, self.tune_freq, self.width, self.height)

	def set_width(self, width):
		self._main.width = width
		self._main.updateWindow()

	def set_height(self, height):
		self._main.height = height
		self._main.updateWindow()

	def get_sample_rate(self):
		return self.sample_rate

	def set_sample_rate(self, sample_rate):
		self.sample_rate = sample_rate
		self._main.sample_rate = sample_rate
		self._main.updateWindow()

	def get_tune_freq(self):
		return self.tune_freq

	def set_tune_freq(self, tune_freq):
		self.tune_freq = tune_freq
		self._main.tune_freq = tune_freq
		self._main.updateWindow()

	def set_average(self, average):
		self.average = average
		self.avg.set_taps(self.average)

	def get_average(self):
		return self.average


#main thread
class main_thread(_threading.Thread):
	def __init__(self, rcvd_data, fft_len, sample_rate, tune_freq, width, height):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data
		self.fft_len = fft_len
		self.sample_rate = sample_rate
		self.tune_freq = tune_freq

		self.width = int(width)
		self.height = int(height)

		self.axis = self.sample_rate/2*np.linspace(-1, 1, self.fft_len) + self.tune_freq
		#self.axis = self.axis[len(self.axis)/2:]
		self.absc = range(self.width)
		self.widthDens = len(self.axis)/int(self.width)
		self.matrix = [[' ' for x in range(self.height)] for y in range(self.width)]

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.start()

	def updateWindow(self):
		self.axis = self.sample_rate/2*np.linspace(-1, 1, self.fft_len) + self.tune_freq
		#self.axis = self.axis[len(self.axis)/2:]
		self.absc = range(self.width)
		self.widthDens = len(self.axis)/int(self.width)
		self.matrix = [[' ' for x in range(self.height)] for y in range(self.width)]
	
	def run(self):
		while self.keep_running:
			msg = self.rcvd_data.delete_head()
			itemsize = int(msg.arg1())
			nitems = int(msg.arg2())

			if nitems > 1:
				start = itemsize * (nitems - 1)
				s = s[start:start+itemsize]

			fft_data = np.fromstring (msg.to_string(), np.float32)
			minValue = min(fft_data)
			maxValue = max(fft_data)
			
			toClient = ''
			auxWidth = 0
			for i in range(self.width):
				htValue = sum(fft_data[auxWidth:auxWidth+self.widthDens])/self.widthDens
				htValueNormed = int(math.floor(((htValue - minValue) * (self.height-1)) / math.floor((maxValue - minValue))))

				self.matrix[i][htValueNormed] = '^'
				for k in range(htValueNormed): self.matrix[i][k] = '|'

				auxWidth += self.widthDens
				toClient += '_ '

			toClient += '_ _ _ _\n'

			for i in reversed(range(self.height)):
				#print vert scale
				if i%5 == 0:
					NewValue = (((i - 0) * math.floor((maxValue - minValue))) / self.height) + minValue
					toP = "%.3f" % (NewValue)
					toClient += toP[:6]
					toClient += ' '
				else:
					toClient += '------ '

				#print the actual matrix of values
				for j in range(self.width):
					toClient += self.matrix[j][i]
					toClient += ' '
				toClient += '\n'

			#ptint horiz scale
			toClient += '------ '
			for a in range(self.width):
				if a%10 == 0:
					NewValue = (((a - 0) * (self.axis[-1]-self.axis[0])) / self.width) + self.axis[0]
					toP = "%.3f" % (NewValue)
					
					toClient += '| '
					toClient += toP[:5]
					toClient += ' ' * (2*10-5-2)

			toClient += '\n'
			
			#print bottom
			toClient += "Tune freq: %s MHz, Sample rate: %s MS/s, FFT: %s \n" % (self.tune_freq/1e6, self.sample_rate/1e6, self.fft_len)
			for a in range(self.width):
				toClient += '_ '
			toClient += '_ _ _ _'
			
			print toClient

			#time.sleep(.2)
			self.matrix = [[' ' for x in range(self.height)] for y in range(self.width)]