#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 germanocapela at gmail dot com
# spectrum sensor - multichannel energy detector
# log the psd after a peak hold
# log maximum power per channel
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
import threading, os
from os.path import expanduser

from ofdm_cr_tools import frange, movingaverage, src_power

#log files information

class logger(object):
	def __init__(self, periodicity):
		start_dat = time.strftime("%y%m%d")
		start_tim = time.strftime("%H%M%S")

		#create a folder with date and time in user system folder
		home = expanduser("~")
		self.directory = home + '/sensing' + '-' + start_dat + '-' + time.strftime("%H%M") + '/'
		if not os.path.exists(self.directory):
			os.makedirs(self.directory)

		#initialize path for cumulative files
		self.path_cumulative_psd = self.directory + 'sdr_psd_cumulative_log' + '-' + start_dat + '-' + start_tim + '.matz'
		self.path_cumulative_stat = self.directory + 'sdr_ss_cumulative_log' + '-' + start_dat + '-' + start_tim + '.log'
		self.path_cumulative_max_power = self.directory + 'sdr_max_power_cumulative_log' + '-' + start_dat + '-' + start_tim + '.matz'

		#initialize cumulative file logs
		self.cumulative_stat_file = open(self.path_cumulative_stat,'w')
		print 'successfully created', self.cumulative_stat_file
		self.psd_file = open(self.path_cumulative_psd,'w')
		print 'successfully created', self.psd_file
		self.max_power_file = open(self.path_cumulative_max_power,'w')
		print 'successfully created', self.max_power_file

		#initialize cumulative vars
		self.cumulative_statistics = {}
		self.settings = {} #valid for periodic and cumulative measurements
		self.cumulative_psd_peaks = None
		self.cumulative_max_power = None

		#variable for periodicity of periodic logs
		self.periodicity = periodicity

		#initialize path for periodic files
		self.path_periodic_psd = self.directory + 'sdr_psd_periodic_log' + '-' + start_dat + '-' + start_tim + '.matz'
		self.path_periodic_stat = self.directory + 'sdr_ss_periodic_log' + '-' + start_dat + '-' + start_tim + '.log'
		self.path_periodic_max_power = self.directory + 'sdr_max_power_periodic_log' + '-' + start_dat + '-' + start_tim + '.matz'

		#initialize periodic vars
		self.periodic_psd_peaks = None
		self.periodic_statistic = {}
		self.periodic_max_power = None
		self.n_measurements_period = 0

		#initialize log thread
		self._file_logger = file_logger(self.periodicity, self.directory,
			self.cumulative_stat_file, self.path_cumulative_stat,
			self.settings, self.cumulative_statistics, self.periodic_statistic,
			self.psd_file, self.path_cumulative_psd, self.cumulative_psd_peaks,
			self.path_periodic_psd, self.periodic_psd_peaks,
			self.max_power_file, self.path_cumulative_max_power, self.cumulative_max_power,
			self.path_periodic_max_power, self.periodic_max_power,
			self.path_periodic_stat, self.n_measurements_period, self.reset_periodic_vars)

	def reset_periodic_vars(self):
		self.periodic_psd_peaks = None
		self.periodic_statistic = {}
		self.periodic_max_power = None
		self.n_measurements_period = 0

	def set_cumulative_psd_peaks(self, cumulative_psd_peaks):
		self.cumulative_psd_peaks = cumulative_psd_peaks
		self._file_logger.cumulative_psd_peaks = cumulative_psd_peaks

	def set_periodic_psd_peaks(self, periodic_psd_peaks):
		self.periodic_psd_peaks = periodic_psd_peaks
		self._file_logger.periodic_psd_peaks = periodic_psd_peaks

	def set_settings(self, settings):
		self.settings = settings
		self._file_logger.settings = settings

	def set_n_measurements_period(self, n_measurements_period):
		self.n_measurements_period = n_measurements_period
		self._file_logger.n_measurements_period = n_measurements_period

	def set_cumulative_statistics(self, cumulative_statistics):
		self.cumulative_statistics = cumulative_statistics
		self._file_logger.cumulative_statistics = cumulative_statistics

	def set_periodic_statistic(self, periodic_statistic):
		self.periodic_statistic = periodic_statistic
		self._file_logger.periodic_statistic = periodic_statistic

	def set_cumulative_max_power(self, cumulative_max_power):
		self.cumulative_max_power = cumulative_max_power
		self._file_logger.cumulative_max_power = cumulative_max_power

	def set_periodic_max_power(self, periodic_max_power):
		self.periodic_max_power = periodic_max_power
		self._file_logger.periodic_max_power = periodic_max_power


#queue wathcer to log max psd
class file_logger(_threading.Thread):
	def __init__(self, periodicity, directory,
	 cumulative_stat_file, path_cumulative_stat,
	 settings, cumulative_statistics, periodic_statistic,
	 psd_file, path_cumulative_psd, cumulative_psd_peaks,
	 path_periodic_psd, periodic_psd_peaks,
	 max_power_file, path_cumulative_max_power, cumulative_max_power,
	 path_periodic_max_power, periodic_max_power,
	 path_periodic_stat, n_measurements_period, reset_periodic_vars):

		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.periodicity = periodicity
		self.directory = directory

		self.cumulative_stat_file = cumulative_stat_file
		self.path_cumulative_stat = path_cumulative_stat

		self.settings = settings
		self.cumulative_statistics = cumulative_statistics
		self.periodic_statistic = periodic_statistic

		self.psd_file = psd_file
		self.path_cumulative_psd = path_cumulative_psd
		self.cumulative_psd_peaks = cumulative_psd_peaks
		self.path_periodic_psd = path_periodic_psd
		self.periodic_psd_peaks = periodic_psd_peaks

		self.max_power_file = max_power_file
		self.path_cumulative_max_power = path_cumulative_max_power
		self.cumulative_max_power = cumulative_max_power
		self.periodic_max_power = periodic_max_power

		self.path_periodic_stat = path_periodic_stat
		self.path_periodic_max_power = path_periodic_max_power

		self.n_measurements_period = n_measurements_period

		self.reset_periodic_vars = reset_periodic_vars

		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:

			# save comulative statistics
			self.cumulative_stat_file = open(self.path_cumulative_stat,'w')
			self.cumulative_stat_file.write('settings ' + str(self.settings) + '\n')
			self.cumulative_stat_file.write('statistics ' + str(self.cumulative_statistics) + '\n')
			self.cumulative_stat_file.write('settings ' + str(self.settings) + '\n')
			self.cumulative_stat_file.write('statistics ' + str(self.cumulative_statistics) + '\n')

			# save periodic stats
			periodic_stat_file = open(self.path_periodic_stat,'w')
			periodic_stat_file.write('settings ' + str(self.settings) + '\n')
			periodic_stat_file.write('statistics ' + str(self.periodic_statistic) + '\n')
			periodic_stat_file.write('settings ' + str(self.settings) + '\n')
			periodic_stat_file.write('statistics ' + str(self.periodic_statistic) + '\n')

			#save cumulative psd
			self.psd_file = open(self.path_cumulative_psd,'w')
			np.save(self.psd_file, self.cumulative_psd_peaks)

			#save periodic psd
			periodic_psd_file = open(self.path_periodic_psd,'w')
			np.save(periodic_psd_file, self.periodic_psd_peaks)

			#save cumulative max powers
			self.max_power_file = open(self.path_cumulative_max_power,'w')
			np.save(self.max_power_file, self.cumulative_max_power)

			#save periodic max powers
			periodic_max_power_file = open(self.path_periodic_max_power,'w')
			np.save(periodic_max_power_file, self.periodic_max_power)

			dat = time.strftime("%y%m%d")
			tim = time.strftime("%H%M%S")

			#reset periodic files
			self.path_periodic_psd = self.directory + 'sdr_psd_periodic_log' + '-' + dat + '-' + tim + '.matz'
			self.path_periodic_stat = self.directory + 'sdr_ss_periodic_log' + '-' + dat + '-' + tim + '.log'
			self.path_periodic_max_power = self.directory + 'sdr_max_power_periodic_log' + '-' + dat + '-' + tim + '.matz'
			#reset periodic vars
			self.periodic_psd_peaks = None
			self.periodic_statistic = {}
			self.n_measurements_period = 0
			self.periodic_max_power = None
			self.reset_periodic_vars()

			time.sleep(self.periodicity)
			print 'logged to files'



class spectrum_sensor_v1(gr.hier_block2):
	def __init__(self, fft_len, sens_per_sec, sample_rate, channel_space=1,
	 search_bw=1, thr_leveler = 10, tune_freq=0, alpha_avg=1, test_duration=1, period=3600, trunc_band=1, verbose=False):
		gr.hier_block2.__init__(self,
			"spectrum_sensor_v1",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),
			gr.io_signature(0,0,0))
		self.fft_len = fft_len #lenght of the fft for spectral analysis
		self.sens_per_sec = sens_per_sec #number of measurements per second (decimates)
		self.sample_rate = sample_rate 
		self.channel_space = channel_space #channel space for analysis
		self.search_bw = search_bw #search bandwidth within each channel
		self.thr_leveler = thr_leveler #leveler factor for noise floor / threshold comparison
		self.tune_freq = tune_freq #center frequency
		self.threshold = 0 #actual value of the threshold
		self.alpha_avg = alpha_avg #averaging factor for noise level between consecutive measurements

		self.msgq0 = gr.msg_queue(2)
		self.msgq1 = gr.msg_queue(2)

		#######BLOCKS#####
		self.s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_len)
		self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fft_len,
		 max(1, int(self.sample_rate/self.fft_len/self.sens_per_sec)))

		mywindow = window.blackmanharris(self.fft_len)
		self.fft = fft.fft_vcc(self.fft_len, True, (), True)

		self.c2mag2 = blocks.complex_to_mag_squared(self.fft_len)
		self.multiply = blocks.multiply_const_vff(np.array([1.0/float(self.fft_len**2)]*fft_len))

		self.sink0 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq0, True)
		self.sink1 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq1, True)
		#####CONNECTIONS####
		self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.multiply, self.sink0)
		self.connect(self.multiply, self.sink1)

		#start periodic logging
		self._logger = logger(period)

		#Watchers
		#statistics and power
		self._watcher0 = _queue0_watcher(self.msgq0, sens_per_sec, self.tune_freq, self.channel_space,
		 self.search_bw, self.fft_len, self.sample_rate, self.thr_leveler, self.alpha_avg, test_duration, trunc_band, verbose, self._logger)
		#psd
		self._watcher1 = _queue1_watcher(self.msgq1, verbose, self._logger)

#queue wathcer to log max psd
class _queue1_watcher(_threading.Thread):
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
			complex_data = np.fromstring (payload, np.float32)

			#cumulative log
			self.logger.set_cumulative_psd_peaks(np.maximum(complex_data, self.logger.cumulative_psd_peaks))

			#periodic log
			self.logger.set_periodic_psd_peaks(np.maximum(complex_data, self.logger.periodic_psd_peaks))


#queue wathcer to log statistics and max power per channel
class _queue0_watcher(_threading.Thread):
	def __init__(self, rcvd_data, sens_per_sec, tune_freq, channel_space,
		 search_bw, fft_len, sample_rate, thr_leveler, alpha_avg, test_duration, trunc_band, verbose, logger):
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

		self.prev_power = np.array([0]*len(self.ax_ch))
		self.curr_power = np.array([0]*len(self.ax_ch))
		self.flag = False

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
			complex_data = np.fromstring (payload, np.float32)

			#scan channels
			spectrum_constraint_hz = self.spectrum_scanner(complex_data)
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

		self.prev_power = self.curr_power
		self.curr_power = (1-0.8) * np.array(power_level_ch) + (0.8) * self.prev_power

		j = 0
		for measure in self.curr_power:
			if measure > self.prev_power[j] and measure > thr and self.flag == False:
				print 'detected flanck!', self.ax_ch[j]/1e6, 'MHz'
				self.flag = True
			if self.flag == True and measure < thr:
				self.flag = False
				print 'detected negative flanck!' , self.ax_ch[j]/1e6, 'MHz'
			j += 1

		#compare channel power with detection threshold
		spectrum_constraint_hz = []
		i = 0
		for item in power_level_ch:
			if item>thr:
				spectrum_constraint_hz.append(self.ax_ch[i])
			i += 1

		return spectrum_constraint_hz
