#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 Germano Capela at gmail.com
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

import numpy as np
from scipy import signal as sg
import time
from gnuradio import gr
import pmt
from ofdm_cr_tools import frange, fast_spectrum_scan


meta_dict = {'REQ':None,'ORIGIN':None}

class spectrum_sensor(gr.sync_block):
	"""
	docstring for block spectrum_sensor
	"""
	def __init__(self, block_length, sample_rate=1, fft_len=1, channel_space=1, search_bw=1, method='fft', thr_leveler = 10, tune_freq=0, alpha_avg=1, source=None, log=False):
		gr.sync_block.__init__(self,
			name="spectrum_sensor",
			in_sig=[np.complex64],
			out_sig=None)
		self.block_length = block_length
		self.sample_rate = sample_rate
		self.fft_len = fft_len
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.method = method
		self.thr_leveler = thr_leveler
		self.tune_freq = tune_freq
		self.vector_sample = [0, 0]
		self.parp = 1e-10
		self.spectrum_constraint_hz = []
		self.threshold = 0
		self.power_level_ch = []
		self.noise_estimate = 1e-11
		self.alpha_avg = alpha_avg
		self.source = source
		self.log = log
		if self.log:
			self.log_file = open('/tmp/ss_log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S"),'w')
			self.log_file.write('Time,'+time.strftime("%H%M%S") + ',sample_rate,' + str(sample_rate) +
			 ',channel_space,' + str(channel_space) + ',channel_bw,' + str(search_bw) +
			  ',tune_freq,' + str(tune_freq) + '\n')
			print 'successfully created log file'
			print self.log_file

		#message output
		self.message_port_register_out(pmt.intern('PDU spect_msg'))
		self.message_port_register_in(pmt.intern('PDU from_cogeng'))
		self.set_msg_handler(pmt.intern('PDU from_cogeng'), self.cogeng_rx)

	def work(self, input_items, output_items):
		in0 = input_items[0][0:self.block_length]
		#save a vector sample
		self.set_vector_sample(in0) #every time the scheduler calls this, i keep 1 vector
		return len(in0) #0 #len(input_items[0]) # 

	def cogeng_rx(self, msg):
		try:
			meta = pmt.car(msg)
			data = pmt.cdr(msg)
		except:
			print "Message is not a valid PDU"
			return
		meta_dict = pmt.to_python(meta)
		if not (type(meta_dict) is dict):
			meta_dict = {}
		#print '-------SS DEBUG-----'
		#print 'Received new request'

		#check what was asked by the received msg...
		if str(data) == 'PAPR': 
			#calc PAPR
			self.set_papr(self.get_vector_sample())
			#send msg w/ papr
			self.send_msg('papr', self.get_papr())
			if self.log:
				self.log_file.write('Time,'+time.strftime("%H%M%S") + ',tune_freq,' + str(self.get_tune_freq()) + '\n')
				self.log_file.write('Time,'+time.strftime("%H%M%S") + ',papr,' + str(self.get_papr()) + '\n')

		elif str(data) == 'SC': 
			#calc Spectrum Constraint
			self.set_spectrum_constraint_hz(self.get_vector_sample())
			#send msg w/ spec const
			self.send_msg('thre', self.get_threshold())
			self.send_msg('nois', self.get_noise_estimate())
			self.send_msg('cons', self.get_spectrum_constraint_hz())
			#print 'threshold', 10*np.log10(self.get_threshold()+1e-20), 'dB'
			#print 'noise',  10*np.log10(self.get_noise_estimate()+1e-20), 'dB'
			#print 'spectrum_constraint_hz: ' + str(self.get_spectrum_constraint_hz())

			#print 'level/channel', self.get_power_level_ch()
			
			if self.log:
				self.log_file.write('Time,'+time.strftime("%H%M%S") + ',tune_freq[Hz],' + str(self.get_tune_freq()) + '\n')
				self.log_file.write('Time,'+time.strftime("%H%M%S") + ',threshold[dB],' + str(10*np.log10(self.get_threshold()+1e-20)) + '\n')
				self.log_file.write('Time,'+time.strftime("%H%M%S") + ',noise[dB],' + str(10*np.log10(self.get_noise_estimate()+1e-20)) + '\n')
				self.log_file.write('Time,'+time.strftime("%H%M%S") + ',spectrum_constraint[Hz],' + str(self.get_spectrum_constraint_hz()) + '\n')
		else:
			self.send_msg('unkn', "received unknown request")
			if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',received unknown request' +'\n')

	def send_msg(self, meta, data):
		#construct pdu and publish to radio port
		#data = pmt.intern(str(data)) #convert from string
		meta = pmt.to_pmt(meta)
		data = pmt.to_pmt(data)
		pdu = pmt.cons(meta, data) #make the PDU
		#publish PDU to msg port
		self.message_port_pub(pmt.intern('PDU spect_msg'),pdu)

	def set_spectrum_constraint_hz(self, measure):
		self.threshold, self.power_level_ch, self.noise_estimate, self.spectrum_constraint_hz = fast_spectrum_scan(measure, self.tune_freq, self.channel_space,
		 self.search_bw, self.fft_len, self.sample_rate, self.method, self.thr_leveler, self.get_noise_estimate(), self.get_alpha_avg(), False)

	def get_spectrum_constraint_hz(self):
		return self.spectrum_constraint_hz

	def get_threshold(self):
		return self.threshold

	def get_noise_estimate(self):
		return self.noise_estimate

	def get_power_level_ch(self):
		return self.power_level_ch

	def set_papr(self, measure):
		meanSquareValue = np.vdot(measure,np.transpose(measure))/len(measure)
		peakValue = max(measure*np.conjugate(measure))
		paprSymbol = peakValue/meanSquareValue
		self.papr = 10*np.log10(paprSymbol.real+1e-20)

	def get_papr(self):
		return self.papr

	def set_vector_sample(self, vector_sample):
		self.vector_sample = vector_sample

	def get_vector_sample(self):
		return self.vector_sample

	def set_block_length(self, block_length):
		self.block_length = block_length

	def set_time_observation(self, time_observation):
		self.time_observation = time_observation

	def get_sample_rate(self):
		return self.sample_rate

	def set_sample_rate(self, sample_rate):
		self.sample_rate = sample_rate
		if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',set_samp_rate,' + str(sample_rate) + '\n')

	def set_fft_len(self, fft_len):
		self.fft_len = fft_len

	def set_tune_freq(self, tune_freq):
		self.tune_freq = tune_freq
		if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',set_tune_freq,' + str(tune_freq) + '\n')

	def get_tune_freq(self):
		return self.tune_freq

	def set_channel_space(self, channel_space):
		self.channel_space = channel_space
		if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',set_channel_space,' + str(channel_space) + '\n')

	def get_channel_space(self):
		return self.channel_space

	def set_search_bw(self, search_bw):
		self.search_bw = search_bw
		if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',set_search_bw,' + str(search_bw) + '\n')

	def get_search_bw(self):
		return self.search_bw

	def set_thr_leveler(self, thr_leveler):
		self.thr_leveler = thr_leveler
		if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',set_thr_leveler,' + str(thr_leveler) + '\n')

	def get_thr_leveler(self):
		return self.thr_leveler
	
	def set_alpha_avg(self, alpha_avg):
		self.alpha_avg = alpha_avg

	def get_alpha_avg(self):
		return self.alpha_avg
