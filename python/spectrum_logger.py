#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 germanocapela at gmail dot com
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
from gnuradio import gr
import time, sys, pmt

class spectrum_logger(gr.sync_block):
	def __init__(self, tune_freq=1, sample_rate=1, fft_len=1, channel_space=1, search_bw=1, log=False, verbose=False):
		gr.sync_block.__init__(self,
			name="spectrum_logger",
			in_sig=None,
			out_sig=[np.float32])
		self.sample_rate = sample_rate
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.tune_freq = tune_freq
		self.log = log
		self.verbose = verbose
		self.constraints = []
		self.spectrum_statistic = {}
		self.settings = {'date':time.strftime("%y%m%d"), 'time':time.strftime("%H%M%S"), 'tune_freq':tune_freq, 'sample_rate':sample_rate, 'fft_len':fft_len,'channel_space':channel_space, 'search_bw':search_bw}
		if self.log:
			self.log_file = open('/tmp/ss_log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S"),'w')
			self.log_file.write('Time,'+time.strftime("%H%M%S") + ',sample_rate,' + str(sample_rate) +
			 ',channel_space,' + str(channel_space) + ',search_bw,' + str(search_bw) +
			  ',tune_freq,' + str(tune_freq) + '\n')
			self.log_file.write('settings ' + str(self.settings) + '\n')
			self.log_file.write('statistics ' + str(self.spectrum_statistic) + '\n')
			print 'successfully created log file'
			print self.log_file
		else:
			print 'printing results'

		#message ports
		#self.message_port_register_out(pmt.intern('PDU spect_msg'))
		self.message_port_register_in(pmt.intern('PDU from_ss'))
		self.set_msg_handler(pmt.intern('PDU from_ss'), self.ss_rx_callback)

	def work(self, input_items, output_items):
		out = len(self.constraints)
		output_items[0][:out] = self.constraints
		self.constraints = []
		return out

	'''
	def work(self, input_items, output_items):
		return 0

	def work(self, input_items, output_items):
		if self.constraints == None:
			return 0
		else:
			out = len(self.constraints)
			output_items[0][:out] = self.constraints
			self.constraints = None
		return out
	'''


	def ss_rx_callback(self, msg):
		try:
			meta = pmt.car(msg)
			data = pmt.cdr(msg)
		except:
			print "Message is not a valid PDU"
			return
		#meta_dict = pmt.to_python(meta)
		#if not (type(meta_dict) is dict):
		#	meta_dict = {}
		#print 'meta', meta
		#print 'data', data
		data = pmt.to_python(data)

		#check what was asked by the received msg...
		#if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',' + str(meta) + ',' + str(data) + '\n')
		#else: print str(meta), str(data)

		self.settings['date'] = time.strftime("%y%m%d")
		self.settings['time'] = time.strftime("%H%M%S")
		#count occurrences
		if str(meta) == 'cons':
			self.constraints = data
			for el in data:
				if el in self.spectrum_statistic:
					self.spectrum_statistic[el] += 1
				else:
					self.spectrum_statistic[el] = 1

		if str(meta) == 'thre': self.settings['thre'] = data
		if str(meta) == 'nois': self.settings['nois'] = data

		if self.log:
			self.log_file.write('settings ' + str(self.settings) + '\n')
			self.log_file.write('statistics ' + str(self.spectrum_statistic) + '\n')

		if self.verbose:
			print 'settings', self.settings
			print 'statistics', self.spectrum_statistic

		'''
		else:
			self.send_msg('ss', "received unknown request")
			if self.log: self.log_file.write('Time,'+time.strftime("%H%M%S") + ',received unknown request' +'\n')
			else: print 'bad request'
		'''


	#def send_msg(self, meta, data):
		#construct pdu and publish to radio port
		#data = pmt.intern(str(data)) #convert from string
		#meta = pmt.to_pmt(meta)
		#data = pmt.to_pmt(data)
		#pdu = pmt.cons(meta, data) #make the PDU
		#publish PDU to msg port
		#self.message_port_pub(pmt.intern('PDU spect_msg'),pdu)


	def set_threshold(self, threshold):
		self.threshold = threshold

	def get_threshold(self):
		return self.threshold

	def get_sample_rate(self):
		return self.sample_rate

	def set_sample_rate(self, sample_rate):
		self.sample_rate = sample_rate
		self.settings['date'] = time.strftime("%y%m%d")
		self.settings['time'] = time.strftime("%H%M%S")
		self.settings['sample_rate'] = samp_rate

	def set_tune_freq(self, tune_freq):
		self.tune_freq = tune_freq
		self.settings['date'] = time.strftime("%y%m%d")
		self.settings['time'] = time.strftime("%H%M%S")
		self.settings['tune_freq'] = tune_freq

	def get_tune_freq(self):
		return self.tune_freq

	def set_channel_space(self, channel_space):
		self.channel_space = channel_space
		self.settings['date'] = time.strftime("%y%m%d")
		self.settings['time'] = time.strftime("%H%M%S")
		self.settings['channel_space'] = channel_space

	def get_channel_space(self):
		return self.channel_space

	def set_search_bw(self, search_bw):
		self.search_bw = search_bw
		self.settings['date'] = time.strftime("%y%m%d")
		self.settings['time'] = time.strftime("%H%M%S")
		self.settings['search_bw'] = search_bw

	def get_search_bw(self):
		return self.search_bw

	def set_alpha_avg(self, alpha_avg):
		self.alpha_avg = alpha_avg

	def get_alpha_avg(self):
		return self.alpha_avg

	def set_verbose(self, verbose):
		self.verbose = verbose

