#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 germanocapela at gmail dot com
# spectrum sensor - multichannel energy detector
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

from scipy import signal as sg
import pmt

from ofdm_cr_tools import frange, fast_spectrum_scan, movingaverage

class spectrum_sensor_v1(gr.hier_block2):
	def __init__(self, fft_len, sens_per_sec, sample_rate, channel_space=1,
	 search_bw=1, thr_leveler = 10, tune_freq=0, alpha_avg=1, test_duration=1, verbose=False):
		gr.hier_block2.__init__(self,
			"spectrum_sensor_v1",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),
			gr.io_signature(0,0,0))
		self.fft_len = fft_len
		self.sens_per_sec = sens_per_sec
		self.sample_rate = sample_rate
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.thr_leveler = thr_leveler
		self.tune_freq = tune_freq
		self.threshold = 0
		self.power_level_ch = []
		self.alpha_avg = alpha_avg

		self.msgq0 = gr.msg_queue(2)
		self.msgq1 = gr.msg_queue(2)

		self.log_stat_file = open('/tmp/ss_log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S"),'w')
		self.log_stat_file.write('Time,'+time.strftime("%H%M%S") + ',sample_rate,' + str(sample_rate) +
		 ',channel_space,' + str(channel_space) + ',channel_bw,' + str(search_bw) +
		  ',tune_freq,' + str(tune_freq) + ',sens_per_sec,' + str(sens_per_sec) + 'test_duration,' + str(test_duration) +'\n')
		print 'successfully created log_stat_file', self.log_stat_file

		#######BLOCKS#####
		self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
		self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
		 max(1, int(self.sample_rate/self.fft_len/self.sens_per_sec)))

		mywindow = window.blackmanharris(self.fft_len)
		self.fft = fft.fft_vcc(self.fft_len, True, (), True)

		self.c2mag = blocks.complex_to_mag(self.fft_len)

		self.sink0 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq0, True)
		self.sink1 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq1, True)
		#####CONNECTIONS####
		self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag, self.sink0)
		self.connect(self.c2mag, self.sink1)

		self._watcher0 = _queue0_watcher(self.msgq0, self.log_stat_file, sens_per_sec, self.tune_freq, self.channel_space,
		 self.search_bw, self.fft_len, self.sample_rate, self.thr_leveler, self.alpha_avg, test_duration, verbose)

		self._watcher1 = _queue1_watcher(self.msgq1, verbose)

class _queue1_watcher(_threading.Thread):
	def __init__(self, rcvd_data, verbose):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data
		dat = time.strftime("%y%m%d")
		tim = time.strftime("%H%M%S")
		self.path = '/tmp/psd_log'+'-'+ dat + '-' + tim + '.matz'
		self.psd_mat_file = open(self.path,'w')
		print 'successfully created log_psd_file', self.psd_mat_file

		self.verbose = verbose
		self.keep_running = True
		self.start()


	def run(self):
		peaks = None
		while self.keep_running:

			msg = self.rcvd_data.delete_head()
			itemsize = int(msg.arg1())
			nitems = int(msg.arg2())

			if nitems > 1:
				start = itemsize * (nitems - 1)
				s = s[start:start+itemsize]
				if self.verbose:
					print 'nitems in queue =', nitems

			payload = msg.to_string()
			complex_data = np.fromstring (payload, np.float32)
			peaks = np.maximum(complex_data, peaks)
			self.psd_mat_file = open(self.path,'w')
			#self.psd_mat_file.write(str(peaks + '\n')
			np.save(self.psd_mat_file, peaks)
			
			#scipy.io.savemat(self.path, mdict={'psd': peaks})

class _queue0_watcher(_threading.Thread):
	def __init__(self, rcvd_data, log_stat_file, sens_per_sec, tune_freq, channel_space,
		 search_bw, fft_len, sample_rate, thr_leveler, alpha_avg, test_duration, verbose):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data
		self.log_stat_file = log_stat_file

		self.tune_freq = tune_freq
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.fft_len = fft_len
		self.sample_rate = sample_rate
		self.thr_leveler = thr_leveler
		self.noise_estimate = 1e-11
		self.alpha_avg = alpha_avg

		self.settings = {'date':time.strftime("%y%m%d"), 'time':time.strftime("%H%M%S"), 'tune_freq':tune_freq, 'sample_rate':sample_rate, 'fft_len':fft_len,'channel_space':channel_space, 'search_bw':search_bw, 'test_duration':test_duration, 'sens_per_sec':sens_per_sec, 'n_measurements':0}
		self.statistic = {}
		self.log_stat_file.write('settings ' + str(self.settings) + '\n')
		self.log_stat_file.write('statistics ' + str(self.statistic) + '\n')

		self.verbose = verbose
		self.keep_running = True
		self.start()


	def run(self):
		while self.keep_running:

			msg = self.rcvd_data.delete_head()
			itemsize = int(msg.arg1())
			nitems = int(msg.arg2())

			if nitems > 1:
				start = itemsize * (nitems - 1)
				s = s[start:start+itemsize]
				if self.verbose:
					print 'nitems in queue =', nitems

			payload = msg.to_string()
			complex_data = np.fromstring (payload, np.float32)
			spectrum_constraint_hz = self.spectrum_scanner(complex_data)
			self.settings['n_measurements'] += 1

			#register data/time
			self.settings['date'] = time.strftime("%y%m%d")
			self.settings['time'] = time.strftime("%H%M%S")

			#count occurrences
			for el in spectrum_constraint_hz:
				if el in self.statistic:
					self.statistic[el] += 1
				else:
					self.statistic[el] = 1

			#log data
			self.log_stat_file.write('settings ' + str(self.settings) + '\n')
			self.log_stat_file.write('statistics ' + str(self.statistic) + '\n')
			
			if self.verbose:
				#print 'settings', self.settings
				print 'statistics', self.statistic

	def spectrum_scanner(self, samples):

		Fr = float(self.sample_rate)/float(self.fft_len)
		Fstart = self.tune_freq - self.sample_rate/2
		Ffinish = self.tune_freq + self.sample_rate/2

		#print 'Scanning...'
		bb_freqs = frange(-self.sample_rate/2, self.sample_rate/2, self.channel_space)
		srch_bins = self.search_bw/Fr

		power_level_ch = src_power(samples, self.fft_len, Fr, self.sample_rate, bb_freqs, srch_bins)
		ax_ch = frange(Fstart, Ffinish, self.channel_space)

		min_power = np.amin (power_level_ch)
		self.noise_estimate = (1-self.alpha_avg) * self.noise_estimate + self.alpha_avg * min_power
		thr = self.noise_estimate * self.thr_leveler

		# test detection threshold
		spectrum_constraint_hz = []
		i = 0
		for item in power_level_ch:
			if item>thr:
				spectrum_constraint_hz.append(ax_ch[i])
			i += 1

		return spectrum_constraint_hz

def src_power(psd, nFFT, Fr, Sf, bb_freqs, srch_bins):
	psd = movingaverage(psd, 1*srch_bins)
	fft_axis = Sf/2*np.linspace(-1, 1, nFFT) #fft_axis = np.fft.fftshift(f)
	power_level_ch_fft = []

	f = bb_freqs[0]
	bin_n = (f+Sf/2)/Fr
	power_level = float(sum(psd[0:int(bin_n+srch_bins/2)]))
	power_level_ch_fft.append(power_level)

	for f in bb_freqs[1:]:
		bin_n = (f+Sf/2)/Fr #freq = bin_n*Fr-Sf/2
		power_level = float(sum(psd[int(bin_n-srch_bins/2):int(bin_n+srch_bins/2)]))
		power_level_ch_fft.append(power_level)
	return power_level_ch_fft
