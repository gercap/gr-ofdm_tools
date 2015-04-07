#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 germanocapela at gmail dot com
# spectrum sensor - multichannel energy detector
# log the psd after a peak hold
# log maximum power per channel

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
from terminaltables import AsciiTable

from ofdm_cr_tools import frange, movingaverage, src_power, logger, file_logger
from ofdm_tools import message_pdu


class spectrum_sensor_v2(gr.hier_block2):
	def __init__(self, fft_len, sens_per_sec, sample_rate, channel_space = 1,
	 search_bw = 1, thr_leveler = 10, tune_freq = 0, alpha_avg = 1, test_duration = 1,
	  period = 3600, trunc_band = 1, verbose = False, stats = False, psd = False, waterfall = False, output = False, subject_channels = []):
		gr.hier_block2.__init__(self,
			"spectrum_sensor_v2",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),
			gr.io_signature(0, 0, 0))
		self.fft_len = fft_len #lenght of the fft for spectral analysis
		self.sens_per_sec = sens_per_sec #number of measurements per second (decimates)
		self.sample_rate = sample_rate 
		self.channel_space = channel_space #channel space for analysis
		self.search_bw = search_bw #search bandwidth within each channel
		self.thr_leveler = thr_leveler #leveler factor for noise floor / threshold comparison
		self.tune_freq = tune_freq #center frequency
		self.threshold = 0 #actual value of the threshold
		self.alpha_avg = alpha_avg #averaging factor for noise level between consecutive measurements
		self.verbose = verbose
		self.trunc_band = trunc_band
		self.stats = stats
		self.psd = psd
		self.waterfall = waterfall
		self.output = output
		self.subject_channels = subject_channels

		#data queue to share data between theads
		self.q = Queue.Queue()

		#gnuradio msg queues
		self.msgq0 = gr.msg_queue(2)
		self.msgq1 = gr.msg_queue(2)
		
		#output top 4 freqs
		self.top4 = [0, 0, 0, 0]
		
		#register message out to other blocks
		self.message_port_register_hier_in("freq_out_0")
		self.message_port_register_hier_in("freq_out_1")
		self.message_port_register_hier_in("freq_out_2")
		self.message_port_register_hier_in("freq_out_3")
		self.message_port_register_hier_in("freq_msg_PDU")

		#######BLOCKS#####
		self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
		self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
		 max(1, int(self.sample_rate/self.fft_len/self.sens_per_sec)))

		mywindow = window.blackmanharris(self.fft_len)
		self.fft = fft.fft_vcc(self.fft_len, True, (), True)

		self.c2mag2 = blocks.complex_to_mag_squared(self.fft_len)
		self.multiply = blocks.multiply_const_vff(np.array([1.0/float(self.fft_len**2)]*fft_len))

		#MSG sinks PSD data
		#stats and basic
		self.sink0 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq0, True)
		if self.psd:
			self.sink1 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq1, True)

		#-----waterfall-----> different decimation because operates in a slower rate
		if self.waterfall:
			self.msgq2 = gr.msg_queue(2)
			self.sink2 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq2, True)
			self.one_in_n_waterfall = blocks.keep_one_in_n(gr.sizeof_float * self.fft_len, self.sens_per_sec) #keep 1 per second...

		#MSG output blocks to other blocks
		self.message_out0 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[0])), 1000)
		self.message_out1 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[1])), 1000)
		self.message_out2 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[2])), 1000)
		self.message_out3 = blocks.message_strobe( pmt.cons( pmt.intern("freq"), pmt.to_pmt(self.top4[3])), 1000)
		self.PDU_messages = message_pdu.message_pdu()

		#####CONNECTIONS####
		#main stream
		self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.multiply, self.sink0)
		#psd stream
		if self.psd:
			self.connect(self.multiply, self.sink1)
		#waterfall stream
		if self.waterfall:
			self.connect(self.multiply, self.one_in_n_waterfall, self.sink2)

		#MSG output
		self.msg_connect(self.message_out0, "strobe", self, "freq_out_0")
		self.msg_connect(self.message_out1, "strobe", self, "freq_out_1")
		self.msg_connect(self.message_out2, "strobe", self, "freq_out_2")
		self.msg_connect(self.message_out3, "strobe", self, "freq_out_3")
		self.msg_connect(self.PDU_messages, 'out', self, 'freq_msg_PDU')

		#start periodic logging
		if self.stats or self.psd or self.waterfall:
			self._logger = logger(self.fft_len, period, test_duration)

		#Watchers
		#statistics and power
		if self.stats:
			self._stats_watcher = stats_watcher(self.msgq0, sens_per_sec, self.tune_freq, self.channel_space,
			 self.search_bw, self.fft_len, self.sample_rate, self.thr_leveler, self.alpha_avg, test_duration,
			  trunc_band, verbose, self._logger, self.q)
		#psd
		if self.psd:
			self._psd_watcher = psd_watcher(self.msgq1, verbose, self._logger)
		#waterfall
		if self.waterfall:
			self._waterfall_watcher = waterfall_watcher(self.msgq2, verbose, self._logger)
		#output_data - start basic watcher and output data threads
		if self.output:
			if self.stats is not True:
				self._basic_spectrum_watcher = basic_spectrum_watcher(self.msgq0, sens_per_sec, self.tune_freq, self.channel_space,
				 self.search_bw, self.fft_len, self.sample_rate, trunc_band, verbose, self.q)
			self._output_data = output_data(self.q, self.sample_rate, self.tune_freq, self.fft_len, self.trunc_band,
			 self.channel_space, self.search_bw, self.output, self.subject_channels, self.set_freqs)
			#send PDU's w/ freq data
			self._send_PDU_data = send_PDU_data(self.top4, self.PDU_messages)

	def set_freqs(self, freq0, freq1, freq2, freq3):
		self.top4[0] = freq0
		self.top4[1] = freq1
		self.top4[2] = freq2
		self.top4[3] = freq3
		self.message_out0.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq0-self.tune_freq) )) #send differencial frequency
		self.message_out1.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq1-self.tune_freq) ))
		self.message_out2.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq2-self.tune_freq) ))
		self.message_out3.set_msg(pmt.cons( pmt.to_pmt("freq"), pmt.to_pmt(freq3-self.tune_freq) ))

#PDU thread
class send_PDU_data(_threading.Thread):
	def __init__(self, top4, PDU_messages):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.top4 = top4
		self.PDU_messages = PDU_messages

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.start()

	def run(self):
		while self.keep_running:
			for freq in self.top4:
				self.PDU_messages.post_message("freq", str(freq))
			time.sleep(1)

#ascii thread
class output_data(_threading.Thread):
	def __init__(self, data_queue, sample_rate, tune_freq, fft_len, trunc_band,
	 channel_space, search_bw, output, subject_channels, set_freqs):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.data_queue = data_queue
		self.fft_len = fft_len
		self.sample_rate = sample_rate
		self.tune_freq = tune_freq
		self.fft_len = fft_len
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.output = output
		self.set_freqs = set_freqs

		self.trunc_band = trunc_band
		self.trunc = sample_rate-trunc_band
		self.trunc_ch = int(self.trunc/self.channel_space)/2

		self.Fr = float(self.sample_rate)/float(self.fft_len) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.bb_freqs = frange(-self.sample_rate/2, self.sample_rate/2, self.channel_space) #baseband freqs
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = frange(self.Fstart, self.Ffinish, self.channel_space) #subject channels
		if self.trunc > 0:
			self.ax_ch = self.ax_ch[self.trunc_ch:-self.trunc_ch] #trunked subject channels

		self.subject_channels = subject_channels # list of channels to be analysed by the flanck detector
		self.idx_subject_channels = [0]*len(self.subject_channels) # aux list to index ax_ch
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = self.ax_ch.index(channel)
			k += 1
		self.subject_channels_pwr = np.array([1.0]*len(self.subject_channels))

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.gnuplot = subprocess.Popen(["/usr/bin/gnuplot"], stdin=subprocess.PIPE)
		self.start()

	def publish(self):
		power_level_ch = self.data_queue.get()
		k = 0
		for channel in self.idx_subject_channels:
			self.subject_channels_pwr[k] = 10*np.log10(power_level_ch[channel])
			k += 1

		ff = self.subject_channels_pwr.argsort()[-4:][::-1]
		self.set_freqs(self.subject_channels[ff[0]], self.subject_channels[ff[1]],
		 self.subject_channels[ff[2]], self.subject_channels[ff[3]])

	def run(self):

		if self.output == 't':
			while self.keep_running:

				left_column = np.array([['Freq [Hz]'],['Power [dB]']])
				table0 = np.vstack((self.subject_channels, self.subject_channels_pwr))
				table =  np.hstack((left_column, table0))
				table_plot = AsciiTable(np.ndarray.tolist(table.T))
				print '\n'
				print table_plot.table
				print '\n'
				sys.stdout.flush()

				#publish top 4 frequencies
				self.publish()


		if self.output == 'g':
			while self.keep_running:

				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'PowerByChannel' \n")

				for i,j in zip(self.subject_channels, self.subject_channels_pwr):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				min_pwr = min(self.subject_channels_pwr)
				self.gnuplot.stdin.write("e\n")
				#self.gnuplot.stdin.write("set yrange [-90:0]")
				self.gnuplot.stdin.write("set yrange ["+str(min_pwr-10)+":0] \n")
				self.gnuplot.stdin.flush()
				print(chr(27) + "[2J")

				#publish top 4 frequencies
				self.publish()

		if self.output == 'o':
			while self.keep_running:
				#publish top 4 frequencies
				self.publish()

#queue wathcer to log waterfall
class waterfall_watcher(_threading.Thread):
	def __init__(self, rcvd_data, verbose, logger):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.verbose = verbose
		self.logger = logger
		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:

			msg = self.rcvd_data.delete_head()

			if self.verbose:
				itemsize = int(msg.arg1())
				nitems = int(msg.arg2())
				if nitems > 1:
					start = itemsize * (nitems - 1)
					s = s[start:start+itemsize]
					print 'nitems in queue =', nitems

			payload = msg.to_string()
			float_data = np.fromstring (payload, np.float32)

			#append to current period variable which then is appended to the cumulative file and reset
			self.logger.cumulative_waterfall.append(float_data)

			#update cumulative log
			self.logger.set_cumulative_waterfall(self.logger.cumulative_waterfall)

#queue wathcer to log max psd
class psd_watcher(_threading.Thread):
	def __init__(self, rcvd_data, verbose, logger):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.verbose = verbose
		self.logger = logger
		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:

			msg = self.rcvd_data.delete_head()

			if self.verbose:
				itemsize = int(msg.arg1())
				nitems = int(msg.arg2())
				if nitems > 1:
					start = itemsize * (nitems - 1)
					s = s[start:start+itemsize]
					print 'nitems in queue =', nitems

			payload = msg.to_string()
			float_data = np.fromstring (payload, np.float32)

			#cumulative log
			self.logger.set_cumulative_psd(np.maximum(float_data, self.logger.cumulative_psd))

			#periodic log
			self.logger.set_periodic_psd_peaks(np.maximum(float_data, self.logger.periodic_psd_peaks))

#queue wathcer to log statistics and max power per channel
class stats_watcher(_threading.Thread):
	def __init__(self, rcvd_data, sens_per_sec, tune_freq, channel_space,
		 search_bw, fft_len, sample_rate, thr_leveler, alpha_avg, test_duration, trunc_band, verbose, logger, data_queue):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.sens_per_sec = sens_per_sec
		self.tune_freq = tune_freq
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.fft_len = fft_len
		self.sample_rate = sample_rate
		self.thr_leveler = thr_leveler
		self.noise_estimate = 1e-11
		self.alpha_avg = alpha_avg
		self.test_duration = test_duration
		self.trunc_band = trunc_band
		self.trunc = sample_rate-trunc_band
		self.trunc_ch = int(self.trunc/self.channel_space)/2

		self.Fr = float(self.sample_rate)/float(self.fft_len) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.bb_freqs = frange(-self.sample_rate/2, self.sample_rate/2, self.channel_space) #baseband freqs
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = frange(self.Fstart, self.Ffinish, self.channel_space) #subject channels
		if self.trunc > 0:
			self.ax_ch = self.ax_ch[self.trunc_ch:-self.trunc_ch] #trunked subject channels
		
		self.plc = np.array([0.0]*len(self.ax_ch))
		self.data_queue = data_queue

		self.verbose = verbose
		self.logger = logger
		self.keep_running = True
		self.start()

	def run(self):

		self.logger.set_settings({'date':time.strftime("%y%m%d"), 'time':time.strftime("%H%M%S"), 'tune_freq':self.tune_freq,
		 'sample_rate':self.sample_rate, 'fft_len':self.fft_len,'channel_space':self.channel_space, 'search_bw':self.search_bw,
		  'test_duration':self.test_duration, 'sens_per_sec':self.sens_per_sec, 'n_measurements':0, 'noise_estimate':self.noise_estimate,
		   'trunc_band':self.trunc_band, 'thr_leveler':self.thr_leveler})

		while self.keep_running:

			msg = self.rcvd_data.delete_head()
			
			if self.verbose:
				itemsize = int(msg.arg1())
				nitems = int(msg.arg2())
				if nitems > 1:
					start = itemsize * (nitems - 1)
					s = s[start:start+itemsize]

			#convert received data to numpy vector
			payload = msg.to_string()
			float_data = np.fromstring (payload, np.float32)

			#scan channels
			spectrum_constraint_hz = self.spectrum_scanner(float_data)
			#count cumulative measurements
			self.logger.settings['n_measurements'] += 1
			#count periodic measurements
			self.logger.n_measurements_period += 1
			self.logger.settings['n_measurements_period'] = self.logger.n_measurements_period
			#get noise estimate
			self.logger.settings['noise_estimate'] = self.noise_estimate

			for el in spectrum_constraint_hz:
				#count occurrences -> cumulative
				if el in self.logger.cumulative_statistics:
					self.logger.cumulative_statistics[el] += 1
				else:
					self.logger.cumulative_statistics[el] = 1
				#count occurrences -> periodic
				if el in self.logger.periodic_statistic:
					self.logger.periodic_statistic[el] += 1
				else:
					self.logger.periodic_statistic[el] = 1

			#update thread that logs data
			self.logger.set_settings(self.logger.settings)
			self.logger.set_n_measurements_period(self.logger.n_measurements_period)
			self.logger.set_cumulative_statistics(self.logger.cumulative_statistics)
			self.logger.set_periodic_statistic(self.logger.periodic_statistic)

	#function that scans channels and compares with threshold to determine occupied / not occupied
	def spectrum_scanner(self, samples):

		#measure power for each channel
		power_level_ch = src_power(samples, self.fft_len, self.Fr, self.sample_rate, self.bb_freqs, self.srch_bins)

		#trunc channels outside useful band (filter curve) --> trunc band < sample_rate
		if self.trunc > 0:
			power_level_ch = power_level_ch[self.trunc_ch:-self.trunc_ch]
		
		#share data among threads
		self.plc = self.plc * 0.6 + np.array(power_level_ch) * 0.4
		self.data_queue.put(self.plc)
		
		#log maximum powers - cumulative
		self.logger.set_cumulative_max_power(np.maximum(power_level_ch, self.logger.cumulative_max_power))

		#log maximum powers - periodic
		self.logger.set_periodic_max_power(np.maximum(power_level_ch, self.logger.periodic_max_power))

		#compute noise estimate (averaged)
		min_power = np.amin (power_level_ch)
		self.noise_estimate = (1-self.alpha_avg) * self.noise_estimate + self.alpha_avg * min_power
		thr = self.noise_estimate * self.thr_leveler
		if self.verbose:
			print 'noise_estimate dB (channel)', 10*np.log10(self.noise_estimate+1e-20)

		#compare channel power with detection threshold
		spectrum_constraint_hz = []
		i = 0
		for item in power_level_ch:
			if item>thr:
				spectrum_constraint_hz.append(self.ax_ch[i])
			i += 1

		return spectrum_constraint_hz


#queue wathcer to log statistics and max power per channel
class basic_spectrum_watcher(_threading.Thread):
	def __init__(self, rcvd_data, sens_per_sec, tune_freq, channel_space,
		 search_bw, fft_len, sample_rate, trunc_band, verbose, data_queue):
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

		self.Fr = float(self.sample_rate)/float(self.fft_len) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.bb_freqs = frange(-self.sample_rate/2, self.sample_rate/2, self.channel_space) #baseband freqs
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = frange(self.Fstart, self.Ffinish, self.channel_space) #subject channels
		if self.trunc > 0:
			self.ax_ch = self.ax_ch[self.trunc_ch:-self.trunc_ch] #trunked subject channels
		
		self.plc = np.array([0.0]*len(self.ax_ch))
		self.data_queue = data_queue

		self.verbose = verbose
		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:
			msg = self.rcvd_data.delete_head()

			#convert received data to numpy vector
			payload = msg.to_string()
			float_data = np.fromstring (payload, np.float32)

			#scan channels
			self.spectrum_scanner(float_data)

	#function that scans channels and compares with threshold to determine occupied / not occupied
	def spectrum_scanner(self, samples):

		#measure power for each channel
		power_level_ch = src_power(samples, self.fft_len, self.Fr, self.sample_rate, self.bb_freqs, self.srch_bins)

		#trunc channels outside useful band (filter curve) --> trunc band < sample_rate
		if self.trunc > 0:
			power_level_ch = power_level_ch[self.trunc_ch:-self.trunc_ch]
		
		#share data among threads
		self.plc = self.plc * 0.6 + np.array(power_level_ch) * 0.4
		self.data_queue.put(self.plc)
