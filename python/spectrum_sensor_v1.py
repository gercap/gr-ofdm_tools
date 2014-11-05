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

from ofdm_cr_tools import frange, movingaverage

#log files information

start_dat = time.strftime("%y%m%d")
start_tim = time.strftime("%H%M%S")

#create a folder with date and time in user system folder
home = expanduser("~")
directory = home+'/sensing' + '-' + start_dat + '-' + time.strftime("%H%M") + '/'
if not os.path.exists(directory):
	os.makedirs(directory)

#initialize path for cumulative files
path_cumulative_psd = directory+'sdr_psd_cumulative_log' + '-' + start_dat + '-' + start_tim + '.matz'
path_cumulative_stat = directory+'sdr_ss_cumulative_log' + '-' + start_dat + '-' + start_tim + '.log'
path_cumulative_max_power = directory+'sdr_max_power_cumulative_log' + '-' + start_dat + '-' + start_tim + '.matz'

#initialize cumulative file logs
cumulative_stat_file = open(path_cumulative_stat,'w')
print 'successfully created', cumulative_stat_file
psd_file = open(path_cumulative_psd,'w')
print 'successfully created', psd_file
max_power_file = open(path_cumulative_max_power,'w')
print 'successfully created', max_power_file

#initialize cumulative vars
cumulative_statistics = {}
settings = {} #valid for periodic and cumulative measurements
cumulative_psd_peaks = None
cumulative_max_power = None

#global variable for periodicity of periodic logs
periodicity = 60*60

#initialize path for periodic files and periodic variables
path_periodic_psd = directory+'sdr_psd_periodic_log' + '-' + start_dat + '-' + start_tim + '.matz'
path_periodic_stat = directory+'sdr_ss_periodic_log' + '-' + start_dat + '-' + start_tim + '.log'
path_periodic_max_power = directory+'sdr_max_power_periodic_log' + '-' + start_dat + '-' + start_tim + '.matz'

#initialize periodic vars
periodic_psd_peaks = None
periodic_statistic = {}
periodic_max_power = None
n_measurements_period = 0 #reset counter for periodic measurements

#function to set periodicity upon flowgraph construction
def set_log_periodicity(period):
	global periodicity
	periodicity = period

#function that starts the periodic procedure of renewing periodic log files
def periodic_files():
	global path_periodic_psd, path_periodic_stat, path_periodic_max_power #path of periodic files (reset every period)
	global periodic_psd_peaks, periodic_statistic, periodic_max_power, n_measurements_period #periodic variables (reset every period)

	#log cumulative stats
	cumulative_stat_file = open(path_cumulative_stat,'w')
	cumulative_stat_file.write('settings ' + str(settings) + '\n')
	cumulative_stat_file.write('statistics ' + str(cumulative_statistics) + '\n')
	cumulative_stat_file.write('settings ' + str(settings) + '\n')
	cumulative_stat_file.write('statistics ' + str(cumulative_statistics) + '\n')

	#log periodic stats
	periodic_stat_file = open(path_periodic_stat,'w')
	periodic_stat_file.write('settings ' + str(settings) + '\n')
	periodic_stat_file.write('statistics ' + str(periodic_statistic) + '\n')
	periodic_stat_file.write('settings ' + str(settings) + '\n')
	periodic_stat_file.write('statistics ' + str(periodic_statistic) + '\n')

	#log cumulative psd
	psd_file = open(path_cumulative_psd,'w')
	np.save(psd_file, cumulative_psd_peaks)

	#log periodic psd
	periodic_psd_file = open(path_periodic_psd,'w')
	np.save(periodic_psd_file, periodic_psd_peaks)

	#log cumulative max powers
	max_power_file = open(path_cumulative_max_power,'w')
	np.save(max_power_file, cumulative_max_power)

	#log periodic max powers
	periodic_max_power_file = open(path_periodic_max_power,'w')
	np.save(periodic_max_power_file, periodic_max_power)

	dat = time.strftime("%y%m%d")
	tim = time.strftime("%H%M%S")

	#reset periodic files
	path_periodic_psd = directory+'sdr_psd_periodic_log' + '-' + dat + '-' + tim + '.matz'
	path_periodic_stat = directory+'sdr_ss_periodic_log' + '-' + dat + '-' + tim + '.log'
	path_periodic_max_power = directory+'sdr_max_power_periodic_log' + '-' + dat + '-' + tim + '.matz'
	#reset periodic vars
	periodic_psd_peaks = None
	periodic_statistic = {}
	n_measurements_period = 0
	periodic_max_power = None

	threading.Timer(periodicity, periodic_files).start()


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
		self.multiply = blocks.multiply_const_vff(np.array([1/float(self.fft_len*self.sample_rate)]*fft_len))

		self.sink0 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq0, True)
		self.sink1 = blocks.message_sink(gr.sizeof_float * self.fft_len, self.msgq1, True)
		#####CONNECTIONS####
		self.connect(self, self.s2p, self.one_in_n, self.fft, self.c2mag2, self.multiply, self.sink0)
		self.connect(self.multiply, self.sink1)

		#Watchers
		self._watcher0 = _queue0_watcher(self.msgq0, sens_per_sec, self.tune_freq, self.channel_space,
		 self.search_bw, self.fft_len, self.sample_rate, self.thr_leveler, self.alpha_avg, test_duration, trunc_band, verbose)
		self._watcher1 = _queue1_watcher(self.msgq1, verbose)

		#start periodic logging
		set_log_periodicity(period)
		periodic_files()

#queue wathcer to log max psd
class _queue1_watcher(_threading.Thread):
	def __init__(self, rcvd_data, verbose):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.verbose = verbose
		self.keep_running = True
		self.start()

	def run(self):
		global periodic_psd_peaks, cumulative_psd_peaks
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

			#cumulative log
			cumulative_psd_peaks = np.maximum(complex_data, cumulative_psd_peaks) 

			#periodic log
			periodic_psd_peaks = np.maximum(complex_data, periodic_psd_peaks) 


#queue wathcer to log statistics and max power per channel
class _queue0_watcher(_threading.Thread):
	def __init__(self, rcvd_data, sens_per_sec, tune_freq, channel_space,
		 search_bw, fft_len, sample_rate, thr_leveler, alpha_avg, test_duration, trunc_band, verbose):
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

		self.verbose = verbose
		self.keep_running = True
		self.start()


	def run(self):
		global periodic_statistic, n_measurements_period, cumulative_statistics, settings

		settings = {'date':time.strftime("%y%m%d"), 'time':time.strftime("%H%M%S"), 'tune_freq':self.tune_freq,
		 'sample_rate':self.sample_rate, 'fft_len':self.fft_len,'channel_space':self.channel_space, 'search_bw':self.search_bw,
		  'test_duration':self.test_duration, 'sens_per_sec':self.sens_per_sec, 'n_measurements':0, 'noise_estimate':self.noise_estimate,
		   'trunc_band':self.trunc_band, 'thr_leveler':self.thr_leveler}

		while self.keep_running:

			msg = self.rcvd_data.delete_head()
			itemsize = int(msg.arg1())
			nitems = int(msg.arg2())

			if nitems > 1:
				start = itemsize * (nitems - 1)
				s = s[start:start+itemsize]

			#convert received data to numpy vector
			payload = msg.to_string()
			complex_data = np.fromstring (payload, np.float32)
			#scann channels
			spectrum_constraint_hz = self.spectrum_scanner(complex_data)
			#count cumulative measurements
			settings['n_measurements'] += 1
			#count periodic measurements
			n_measurements_period += 1
			settings['n_measurements_period'] = n_measurements_period
			#get noise estimate
			settings['noise_estimate'] = self.noise_estimate

			#register data/time
			settings['date'] = time.strftime("%y%m%d")
			settings['time'] = time.strftime("%H%M%S")

			for el in spectrum_constraint_hz:
				#count occurrences -> cumulative
				if el in cumulative_statistics:
					cumulative_statistics[el] += 1
				else:
					cumulative_statistics[el] = 1
				#count occurrences -> periodic
				if el in periodic_statistic:
					periodic_statistic[el] += 1
				else:
					periodic_statistic[el] = 1

			if self.verbose:
				#print 'settings', self.settings
				print 'statistics', cumulative_statistics

	#function that scans channels and compares with threshold to determine occupied / not occupied
	def spectrum_scanner(self, samples):
		global periodic_max_power, cumulative_max_power

		#measure power for each channel
		power_level_ch = src_power(samples, self.fft_len, self.Fr, self.sample_rate, self.bb_freqs, self.srch_bins)

		#trunc channels outside useful band (filter curve) --> trunc band < sample_rate
		if self.trunc > 0:
			power_level_ch = power_level_ch[self.trunc_ch:-self.trunc_ch]

		#log maximum powers - cumulative
		cumulative_max_power = np.maximum(power_level_ch, cumulative_max_power)

		#log maximum powers - periodic
		periodic_max_power = np.maximum(power_level_ch, periodic_max_power)

		#compute noise estimate (averaged)
		min_power = np.amin (power_level_ch)
		self.noise_estimate = (1-self.alpha_avg) * self.noise_estimate + self.alpha_avg * min_power
		thr = self.noise_estimate * self.thr_leveler

		#compare channel power with detection threshold
		spectrum_constraint_hz = []
		i = 0
		for item in power_level_ch:
			if item>thr:
				spectrum_constraint_hz.append(self.ax_ch[i])
			i += 1

		return spectrum_constraint_hz

def src_power(psd, nFFT, Fr, Sf, bb_freqs, srch_bins):
	#apply a moving average across psd - softens noise effect
	psd = movingaverage(psd, 1*srch_bins)
	#fft_axis = Sf/2*np.linspace(-1, 1, nFFT) #fft_axis = np.fft.fftshift(f)
	power_level_ch_fft = []

	#compute power for left edge frequency
	f = bb_freqs[0]
	bin_n = (f+Sf/2)/Fr
	power_level = float(sum(psd[0:int(bin_n+srch_bins/2)]))
	power_level_ch_fft.append(power_level)

	#compute power per frequency
	for f in bb_freqs[1:]:
		bin_n = (f+Sf/2)/Fr #freq = bin_n*Fr-Sf/2
		power_level = float(sum(psd[int(bin_n-srch_bins/2):int(bin_n+srch_bins/2)]))
		power_level_ch_fft.append(power_level)
	return power_level_ch_fft
