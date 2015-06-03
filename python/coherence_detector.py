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
	 tune_freq = 0, alpha_avg = 1, test_duration = 1, period = 3600, stats = False, output = False, rate = 10,
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
		self.subject_channels_outcome = [0.1]*len(subject_channels)
		self.rate = rate

		#data queue to share data between theads
		self.q0 = Queue.Queue()

		#gnuradio msg queues
		self.msgq = gr.msg_queue(2)

		#######BLOCKS#####
		self.sink = blocks.message_sink(gr.sizeof_float * self.N, self.msgq, True)

		#####CONNECTIONS####
		self.connect(self, self.sink)

		self._watcher = watcher(self.msgq, self.tune_freq, self.threshold, self.search_bw, self.N,
		 self.sample_rate, self.q0, self.subject_channels, self.set_subject_channels_outcome, self.rate)
		if self.output != False:
			self._output_data = output_data(self.q0, self.sample_rate, self.tune_freq, self.N,
				 self.search_bw, self.output, self.subject_channels, self.get_subject_channels_outcome)

	def set_subject_channels_outcome(self, subject_channels_outcome):
		self.subject_channels_outcome = subject_channels_outcome

	def get_subject_channels_outcome(self):
		return self.subject_channels_outcome

#ascii thread
class output_data(_threading.Thread):
	def __init__(self, data_queue0, sample_rate, tune_freq, N,
	 search_bw, output, subject_channels, get_subject_channels_outcome):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.data_queue0 = data_queue0
		self.N = N
		self.sample_rate = sample_rate
		self.tune_freq = tune_freq
		self.search_bw = search_bw
		self.output = output
		self.get_subject_channels_outcome = get_subject_channels_outcome

		self.Fr = float(self.sample_rate)/float(self.N) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = np.array(range(-self.N/2, self.N/2)) * self.Fr + self.tune_freq #subject channels

		self.subject_channels = subject_channels
		self.idx_subject_channels = [0]*len(self.subject_channels)
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = find_nearest_index(self.ax_ch, channel)
			k += 1

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.gnuplot = subprocess.Popen(["/usr/bin/gnuplot"], stdin=subprocess.PIPE)
		self.start()

	def run(self):

		if self.output == 'g':
			while self.keep_running:
				data = self.data_queue0.get()
				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'Spectral Coherence' \n")

				for i,j in zip(self.subject_channels, data):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				self.gnuplot.stdin.write("e\n")
				self.gnuplot.stdin.flush()

				print(chr(27) + "[2J")

		if self.output == 't_o':
			while self.keep_running:
				data = self.data_queue0.get()
				left_column = np.array([['Freq [Hz]'],['Coherence'],['Outcome']])
				table0 = np.vstack((self.subject_channels, data, self.get_subject_channels_outcome()))
				table =  np.hstack((left_column, table0))
				table_plot = AsciiTable(np.ndarray.tolist(table.T))
				print '\n'
				print table_plot.table
				sys.stdout.flush()


		if self.output == 'g_o':
			while self.keep_running:
				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'Spectral Coherence Outcome' \n")

				for i,j in zip(self.subject_channels, self.get_subject_channels_outcome()):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				self.gnuplot.stdin.write("e\n")
				self.gnuplot.stdin.flush()

				print(chr(27) + "[2J")


#queue wathcer to log statistics and max power per channel
class watcher(_threading.Thread):
	def __init__(self, rcvd_data, tune_freq, threshold,
		 search_bw, N, sample_rate, data_queue0, subject_channels, set_subject_channels_outcome, rate):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.tune_freq = tune_freq
		self.threshold = threshold
		self.search_bw = search_bw
		self.N = N
		self.sample_rate = sample_rate
		self.rate = rate

		self.Fr = float(self.sample_rate)/float(self.N) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.srch_bins = int(self.search_bw/self.Fr/2) #binwidth for search
		self.ax_ch = np.array(range(-self.N/2, self.N/2)) * self.Fr + self.tune_freq #all channels

		# ax_ch - all channels available from bins
		# subject_channels - channels to analyze
		# idx_subject_channels - index CLOSEST subject_channels in ax_ch
		# subject_channels_outcome - outcome for subject_channels

		self.subject_channels = subject_channels
		self.n_chans = len(self.subject_channels)
		self.idx_subject_channels = [0]*self.n_chans
		self.subject_channels_coherence = [0]*self.n_chans
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = find_nearest_index(self.ax_ch, channel)
			k += 1

		self.set_subject_channels_outcome = set_subject_channels_outcome
		self.subject_channels_outcome = [0]*self.n_chans

		self.plc = np.array([0.0]*len(self.ax_ch))
		self.data_queue0 = data_queue0

		#file out
		start_dat = time.strftime("%y%m%d")
		start_tim = time.strftime("%H%M%S")
		
		self.coherence_path = './coherence_log' + '-' + start_dat + '-' + start_tim + '.log'
		self.coherence_file = open(self.coherence_path,'w')

		self.coherence_file.write('Freqs' + '\n')
		self.coherence_file.write(str(self.subject_channels) + '\n')
		self.coherence_file.write('Coherences at ' + str(self.rate) + ' measurements per second' + '\n')
		
		print "Created file: ", self.coherence_path

		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:
			msg = self.rcvd_data.delete_head()

			itemsize = int(msg.arg1())
			nitems = int(msg.arg2())
			s = msg.to_string()
			if nitems > 1:
				print 'Discarded: ', nitems, ' vectors'
				start = itemsize * (nitems - 1)
				s = s[start:start+itemsize]

			#convert received data to numpy vector
			float_data = np.fromstring (s, np.float32)
			self.plc = self.plc * 0.6 + np.array(float_data) * 0.4

			#scan channels
			self.scanner(float_data)
			#self.scanner(self.plc)

	#function that scans channels and compares with threshold to determine occupied / not occupied
	def scanner(self, data):
		self.subject_channels_outcome = [0]*self.n_chans

		for j, channel in zip(range(self.n_chans),self.idx_subject_channels):
			coherence = data[(channel-self.srch_bins):(channel+self.srch_bins)].sum()
			self.subject_channels_coherence[j] = coherence
			if coherence > self.threshold:
				self.subject_channels_outcome[j] = 1
			else:
				self.subject_channels_outcome[j] = 0.1

		self.coherence_file.write(str(self.subject_channels_coherence) + '\n')

		self.set_subject_channels_outcome(self.subject_channels_outcome) #publish detection outcome
		self.data_queue0.put(self.subject_channels_coherence) #send coherence to threads

def find_nearest_index(array, value):
	idx = (np.abs(array-value)).argmin()
	return idx

def find_nearest_value(array, value):
	idx = (np.abs(array-value)).argmin()
	return array[idx]
