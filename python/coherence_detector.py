#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2015 germanocapela at gmail.com
#
# Connect to spectral coherence detector flowgraph 
#
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

from gnuradio import gr, gru, fft
from gnuradio import blocks
from gnuradio.filter import window
import numpy as np
import gnuradio.gr.gr_threading as _threading
from scipy import signal as sg
import threading, os, pmt, subprocess, time, datetime, Queue, sys, pmt
from os.path import expanduser
from operator import add
from terminaltables import AsciiTable

from ofdm_cr_tools import frange, movingaverage, src_power, logger, file_logger
from ofdm_tools import message_pdu


class coherence_detector(gr.hier_block2):
	def __init__(self, N, sample_rate, search_bw = 1, threshold = 10,
	 tune_freq = 0, alpha_avg = 1, test_duration = 1, period = 3600, stats = False, output = False,
	  subject_channels = []):

		gr.hier_block2.__init__(self,
			"coherence_detector",
			gr.io_signature(1, 1, gr.sizeof_float*N),
			gr.io_signature(0, 0, 0))
		self.N = N #lenght of the fft for spectral analysis
		self.sample_rate = sample_rate 
		self.search_bw = search_bw #search bandwidth within each channel
		self.threshold = threshold #threshold comparison
		self.tune_freq = tune_freq #center frequency
		self.alpha_avg = alpha_avg #averaging factor for noise level between consecutive measurements
		self.output = output
		self.subject_channels = subject_channels
		self.spectrum_constraint = []

		#data queue to share data between theads
		self.q0 = Queue.Queue()
		self.q1 = Queue.Queue()

		#gnuradio msg queues
		self.msgq = gr.msg_queue(2)

		#######BLOCKS#####
		self.sink = blocks.message_sink(gr.sizeof_float * self.N, self.msgq, True)

		#####CONNECTIONS####
		self.connect(self, self.sink)

		self._watcher = watcher(self.msgq, self.tune_freq, self.threshold, self.search_bw, self.N,
		 self.sample_rate, self.q0, self.q1, self.subject_channels, self.set_spectrum_constraint)
		self._output_data = output_data(self.q0, self.q1, self.sample_rate, self.tune_freq, self.N,
			 self.search_bw, self.output, self.subject_channels)

	def set_spectrum_constraint(self, spectrum_constraint):
		self.spectrum_constraint = spectrum_constraint

	def get_spectrum_constraint(self):
		return self.spectrum_constraint

#ascii thread
class output_data(_threading.Thread):
	def __init__(self, data_queue0, data_queue1, sample_rate, tune_freq, N,
	 search_bw, output, subject_channels):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.data_queue0 = data_queue0
		self.data_queue1 = data_queue1
		self.N = N
		self.sample_rate = sample_rate
		self.tune_freq = tune_freq
		self.search_bw = search_bw
		self.output = output

		self.Fr = float(self.sample_rate)/float(self.N) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = np.array(range(-self.N/2, self.N/2)) * self.Fr + self.tune_freq #subject channels

		self.subject_channels = subject_channels # list of channels to be analysed by the flanck detector
		self.idx_subject_channels = [0]*len(self.subject_channels) # aux list to index ax_ch
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = self.ax_ch.index(channel)
			k += 1

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.gnuplot = subprocess.Popen(["/usr/bin/gnuplot"], stdin=subprocess.PIPE)
		self.start()

	def run(self):
		if self.output == 't':
			while self.keep_running:
				data = self.data_queue0.get()
				left_column = np.array([['Freq [Hz]'],['Coherence']])
				table0 = np.vstack((self.ax_ch, data))
				table =  np.hstack((left_column, table0))
				table_plot = AsciiTable(np.ndarray.tolist(table.T))
				print '\n'
				print table_plot.table
				print '\n'
				sys.stdout.flush()

		if self.output == 'g':
			while self.keep_running:
				data = self.data_queue0.get()
				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'Spectral Coherence' \n")

				for i,j in zip(self.ax_ch, data):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				self.gnuplot.stdin.write("e\n")
				self.gnuplot.stdin.flush()

				print(chr(27) + "[2J")

		if self.output == 't_o':
			while self.keep_running:
				data = self.data_queue1.get()
				left_column = np.array([['Freq [Hz]'],['Outcome']])
				table0 = np.vstack((self.ax_ch, data))
				table =  np.hstack((left_column, table0))
				table_plot = AsciiTable(np.ndarray.tolist(table.T))
				print '\n'
				print table_plot.table
				print '\n'
				sys.stdout.flush()

		if self.output == 'g_o':
			while self.keep_running:
				data = self.data_queue1.get()
				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'Spectral Coherence Outcome' \n")

				for i,j in zip(self.ax_ch, data):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				self.gnuplot.stdin.write("e\n")
				self.gnuplot.stdin.flush()

				print(chr(27) + "[2J")


#queue wathcer to log statistics and max power per channel
class watcher(_threading.Thread):
	def __init__(self, rcvd_data, tune_freq, threshold,
		 search_bw, N, sample_rate, data_queue0, data_queue1, subject_channels, set_spectrum_constraint):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.tune_freq = tune_freq
		self.threshold = threshold
		self.search_bw = search_bw
		self.N = N
		self.sample_rate = sample_rate

		self.Fr = float(self.sample_rate)/float(self.N) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = np.array(range(-self.N/2, self.N/2)) * self.Fr + self.tune_freq #subject channels

		self.subject_channels = subject_channels
		self.idx_subject_channels = [0]*len(self.subject_channels) # aux list to index ax_ch
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = self.ax_ch.index(channel)
			k += 1
		#self.subject_channels_outcome = [True]*len(self.subject_channels)
		self.outcome = [1]*len(self.ax_ch)
		self.set_spectrum_constraint = set_spectrum_constraint
		self.spectrum_constraint = []

		self.plc = np.array([0.0]*len(self.ax_ch))
		self.data_queue0 = data_queue0
		self.data_queue1 = data_queue1

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
			self.plc = self.plc * 0.6 + np.array(float_data) * 0.4
			self.data_queue0.put(self.plc)

			#scan channels
			self.scanner(float_data)
			#self.scanner(self.plc)

	#function that scans channels and compares with threshold to determine occupied / not occupied
	def scanner(self, data):
		self.spectrum_constraint = []
		j = 0
		for element in data:
			if element > self.threshold:
				self.outcome[j] = 1
				self.spectrum_constraint.append(self.ax_ch[j])
			else:
				self.outcome[j] = 0
			#print element, self.threshold
			j += 1
		print self.spectrum_constraint
		self.set_spectrum_constraint(self.spectrum_constraint)
		self.data_queue1.put(self.outcome)
