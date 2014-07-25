#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 <+YOU OR YOUR COMPANY+>.
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
import math
from gnuradio import gr
import pmt
from ofdm_cr_tools import frange, src_power_fft, src_power_welch, fast_spectrum_scan


meta_dict = {'ORDER':None,'ORIGIN':None}

class spectrum_sensor(gr.sync_block):
	"""
	docstring for block spectrum_sensor
	"""
	def __init__(self, vect_length, sample_rate=1, fft_len=1, threshold=1, channel_space=1, search_bw=1, tune_freq=0):
		gr.sync_block.__init__(self,
			name="spectrum_sensor",
			in_sig=[(np.complex64, vect_length)],
			out_sig=None)
		self.vct_len = vect_length
		self.sample_rate = sample_rate
		self.fft_len = fft_len
		self.threshold = threshold
		self.channel_space = channel_space
		self.search_bw = search_bw
		self.tune_freq = tune_freq
		
		#message output
		self.message_port_register_out(pmt.intern('PDU spect_msg'))
		self.message_port_register_in(pmt.intern('PDU from_cogeng'))
		self.set_msg_handler(pmt.intern('PDU from_cogeng'), self.cogeng_rx)
		self.i = 0
		self.vector_sample = [0, 0]
		self.parp = 0

	def work(self, input_items, output_items):
		in0 = input_items[0][:]
		#save a vector sample
		self.set_vector_sample(in0[0])
		return len(in0)

	def cogeng_rx(self, msg):
		try:
			meta = pmt.car(msg)
			data = pmt.cdr(msg)
		except:
			print "Message is not a PDU"
			return
		meta_dict = pmt.to_python(meta)
		if not (type(meta_dict) is dict):
			meta_dict = {}
		#deal with metadata...

		#check what was asked by the received msg...
		if str(data) == 'PAPR': 
			#calc PAPR
			self.set_papr(self.get_vector_sample())
			#send msg w/ papr
			self.send_msg(self.get_papr())
		elif str(data) == 'SC': 
			#calc Spectrum Constraint
			self.set_spectrum_constraint_hz(self.get_vector_sample())
			#send msg w/ spec const
			self.send_msg(self.get_spectrum_constraint_hz())
		else:
			self.send_msg("received unknown request")

	def send_msg(self, data):
		#construct pdu and publish to radio port
		#data = pmt.intern(str(data)) #convert from string
		data = pmt.to_pmt(data)
		meta = pmt.to_pmt({}) #crete empty metadata
		pdu = pmt.cons(meta, data) #make the PDU
		#publish PDU to msg port
		self.message_port_pub(pmt.intern('PDU spect_msg'),pdu)


	def set_spectrum_constraint_hz(self, measure):
		self.spectrum_constraint_hz = fast_spectrum_scan(measure, self.tune_freq, self.channel_space,
		 self.search_bw, self.fft_len, self.sample_rate, 'welch', 1e-9, False)

	def get_spectrum_constraint_hz(self):
		return self.spectrum_constraint_hz

	def set_tune_freq(self, tune_freq):
		self.tune_freq = tune_freq

	def get_tune_freq(self):
		return self.tune_freq

	def set_papr(self, measure):
		meanSquareValue = np.vdot(measure,np.transpose(measure))/len(measure)
		peakValue = max(measure*np.conjugate(measure))
		paprSymbol = peakValue/meanSquareValue
		self.papr = paprSymbol.real

	def get_papr(self):
		return self.papr

	def set_vector_sample(self, vector_sample):
		self.vector_sample = vector_sample

	def get_vector_sample(self):
		return self.vector_sample

	def set_vect_length(self, vect_length):
		self.vect_length = vect_length

	def set_time_observation(self, time_observation):
		self.time_observation = time_observation

	def set_sample_rate(self, sample_rate):
		self.sample_rate = sample_rate

	def set_fft_len(self, fft_len):
		self.fft_len = fft_len

	def set_threshold(self, threshold):
		self.threshold = threshold
