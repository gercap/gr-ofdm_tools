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

import numpy
from gnuradio import gr
import gnuradio.gr.gr_threading as _threading
import time, ast, math
import pmt
from ofdm_cr_tools import spectrum_translator, spectrum_enforcer, chunks_of_word

#OFDM transmitter initial settings
ofdm_fc = 158e6 #87.6e6
ofdm_samp_rate = 1000000
ofdm_fft_len = 128 #64 128 1024 try not to use more than 1024
payload_mod = 'qpsk'  # bpsk qpsk qam16
ofdm_dc_offset = ofdm_samp_rate/2
lobe_len = int(ofdm_fft_len/16)	#side lobe bins to cancel on each side
cp_len = ofdm_fft_len/4
#frequency - fft bin ratio
Fr = float(ofdm_samp_rate)/float(ofdm_fft_len)
canc_band = 50e3 #band to cancel
canc_bins = math.ceil(canc_band/Fr) #bins to cancel
ofdm_settings  = {'ofdm_fc':ofdm_fc, 'ofdm_samp_rate':ofdm_samp_rate, 'ofdm_fft_len':ofdm_fft_len,
 'payload_mod':payload_mod, 'ofdm_dc_offset':ofdm_dc_offset, 'lobe_len':lobe_len,
  'cp_len':cp_len, 'canc_bins':canc_bins}

'''
keywords 
SC - spectrum constraint
PAPR - PAPR
'''
_sync_status_Nok = True

#main cognitive engine thread
class main_thread(_threading.Thread):
	def __init__(self, agent, sensing_periodicity, to_spec_sense, ofdm_radio, sync_radio, radio_selector):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.agent = agent
		self.sensing_periodicity = sensing_periodicity
		self.to_spec_sense = to_spec_sense

		self.ofdm_radio = ofdm_radio
		self.sync_radio = sync_radio
		self.radio_selector = radio_selector

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.start()

	def run(self):
		print 'main thread started'
		time.sleep(self.sensing_periodicity)
		#self.radio_selector.set_input_index(0) #OFDM
		#self.radio_selector.set_input_index(1) #SYNC
		while self.keep_running:
			#requesting SC
			self.to_spec_sense('ce', 'SC')
			#requesting PAPR
			#self.to_spec_sense('ce', 'PAPR')
			time.sleep(self.sensing_periodicity)


class cognitive_engine_mac(gr.basic_block):
	"""
	cognitive_engine_mac = mac + cognitive radio
	"""
	def __init__(self, agent, address, sample_rate, sensing_periodicity, ofdm_radio, sync_radio, radio_selector):
		gr.basic_block.__init__(self,
			name="cognitive_engine_mac",
			in_sig = None,
			out_sig = None)
		self.address = address
		self.agent = agent
		self.sync_data = {}

		self.ofdm_radio = ofdm_radio
		self.sync_radio = sync_radio
		self.radio_selector = radio_selector

		self.main = main_thread(self.agent, sensing_periodicity, self.to_spec_sense, self.ofdm_radio, self.sync_radio, self.radio_selector)

		#OFDM RADIO
		self.message_port_register_out(pmt.intern('to_ofdm_radio'))
		self.message_port_register_in(pmt.intern('from_ofdm_radio'))
		self.set_msg_handler(pmt.intern('from_ofdm_radio'), self.ofdm_radio_rx)

		#SYNC RADIO
		self.message_port_register_out(pmt.intern('to_sync_radio'))
		self.message_port_register_in(pmt.intern('from_sync_radio'))
		self.set_msg_handler(pmt.intern('from_sync_radio'), self.sync_radio_rx)

		#APP
		self.message_port_register_out(pmt.intern('to_app'))
		self.message_port_register_in(pmt.intern('from_app'))
		self.set_msg_handler(pmt.intern('from_app'), self.app_rx)

		#SPEC SENSOR
		self.message_port_register_out(pmt.intern('to_spect_sens'))
		self.message_port_register_in(pmt.intern('from_spect_sens'))
		self.set_msg_handler(pmt.intern('from_spect_sens'), self.spect_sens_rx)



	def general_work(self, input_items, output_items):
		return 0

	#handle received spectrum constraints from spectrum sensor
	def spect_sens_rx(self, msg):
		meta_dict, data = self.check_msg(msg)
		data = pmt.to_python(data)
		#deal with metadata...
		print '---------CE DEBUG--------'
		print 'received from spect sense'
		print 'meta_dict', meta_dict
		print 'data', data
		#generate sync data!
		#spectrum_constraint_hz = data
		#self.generate_sync_data(spectrum_constraint_hz) #updates self.sync_data
		#temp = chunks_of_word(str(self.sync_data),  400)
		pdu_tuple = (str(data), {})
		self.to_sync_radio(pdu_tuple)
		return None

	def ofdm_radio_rx(self, msg):
		meta_dict, data = self.check_msg(msg)
		#deal with metadata...
		print '----CE DEBUG-OFDM-RX----'
		print 'data', data
		#send to ofdm
		return None

	def sync_radio_rx(self, msg):
		meta_dict, data = self.check_msg(msg)
		str_data = pmt.to_python(data) #recover from u8vector
		str_data = ''.join([chr(el) for el in str_data]) #recover from map ord
		#data = ast.literal_eval(str_data) # recover from str
		#deal with metadata...
		print '----CE DEBUG-SYNC-RX----'
		print 'data', str_data
		return None

	def app_rx(self, msg):
		return None

	def check_msg(self, msg):
		try:
			meta = pmt.car(msg)
			data = pmt.cdr(msg)
		except:
			print "Message is not a valid PDU"
			return
		#meta_dict = pmt.to_python(meta)
		#if not (type(meta_dict) is dict):
		#	meta_dict = {}
		#if pmt.is_u8vector(data):
		#	data = pmt.u8vector_elements(data)
		#else:
		#	print "Data is not a u8vector"
		#	return meta_dict, data
		return meta, data

	#pediodically send a msg to spectrum sensor
	def to_spec_sense(self, meta, data):
		meta = pmt.to_pmt(meta)
		data = pmt.to_pmt(data)
		pdu = pmt.cons(meta, data) #make the PDU
		#publish PDU to msg port
		self.message_port_pub(pmt.intern('to_spect_sens'),pdu)
		return None

	def to_ofdm_radio(self, pdu_tuple):
		print 'sending new ofdm msg'
		meta_data = pdu_tuple[1]
		payload = pdu_tuple[0]
		if payload is None:
			payload = []
		elif isinstance(payload, str):
			payload = map(ord, list(payload))
		elif not isinstance(payload, list):
			payload = list(payload)
		#data = [1, self.address, 2, 3, 4]
		#data += payload
		data = payload
		data = pmt.init_u8vector(len(data), data)
		meta = pmt.to_pmt(meta_data)

		#construct pdu and publish to radio port
		pdu = pmt.cons(meta, data)
		#publish to msg port
		self.message_port_pub(pmt.intern('to_ofdm_radio'),pdu)
		return None

	def to_sync_radio(self, pdu_tuple):
		print 'sending new sync msg'
		meta_data = pdu_tuple[1]
		payload = pdu_tuple[0]
		if payload is None:
			payload = []
		elif isinstance(payload, str):
			payload = map(ord, list(payload))
		elif not isinstance(payload, list):
			payload = list(payload)
		#data = [1, self.address, 2, 3, 4]
		data = payload
		data = pmt.init_u8vector(len(data), data)
		meta = pmt.to_pmt(meta_data)

		#construct pdu and publish to radio port
		pdu = pmt.cons(meta, data)
		#publish to msg port
		self.message_port_pub(pmt.intern('to_sync_radio'),pdu)
		return None

	def get_sample_rate(self):
		return self.sample_rate

	def set_sample_rate(self, sample_rate):
		self.sample_rate = sample_rate

	def get_sensing_periodicity(self):
		return self.sensing_periodicity

	def set_sensing_periodicity(self, sensing_periodicity):
		self.sensing_periodicity = sensing_periodicity
		self.main.sensing_periodicity = sensing_periodicity


    #transmit data example - msg is numpy array
	def _to_ofdm_radio(self, pdu_tuple, pkt_cnt, protocol_id, control):
		meta_data = pdu_tuple[1]
		payload = pdu_tuple[0]
		if payload is None:
			payload = []
		elif isinstance(payload, str):
			payload = map(ord, list(payload))
		elif not isinstance(payload, list):
			payload = list(payload)

		dest_addr = meta_data['EM_DEST_ADDR']
		if dest_addr == -1:
			dest_addr = BROADCAST_ADDR
		elif dest_addr < -1 or dest_addr > BROADCAST_ADDR:
			print "Invalid address:", dest_addr
			return
        
		#create header, merge with payload, convert to pmt for message_pub
		data = [pkt_cnt, self.address, dest_addr, protocol_id, control]

		data += payload

		data = pmt.init_u8vector(len(data), data)
		meta = pmt.to_pmt({})

		#construct pdu and publish to radio port
		pdu = pmt.cons(meta, data)
		#publish to msg port
		self.message_port_pub(pmt.intern('to_ofdm_radio'),pdu)

	def generate_sync_data(self, spectrum_constraint_hz):
		#convert constraint from hz to fft bins
		spectrum_constraint_fft = spectrum_translator(spectrum_constraint_hz, ofdm_settings['ofdm_fc'],
		 ofdm_settings['ofdm_samp_rate'], ofdm_settings['ofdm_fft_len'], ofdm_settings['canc_bins'])
		#build sync data
		#self.sync_data['occupied_carriers'], self.sync_data['pilot_carriers'], self.sync_data['pilot_symbols'], self.sync_data['sync_word1'], self.sync_data['sync_word2'] = spectrum_enforcer(ofdm_settings['ofdm_fft_len'], spectrum_constraint_fft, ofdm_settings['lobe_len'])
		self.sync_data['occupied_carriers'], self.sync_data['pilot_carriers'], self.sync_data['pilot_symbols'], dump1, dump2 = spectrum_enforcer(ofdm_settings['ofdm_fft_len'], spectrum_constraint_fft, ofdm_settings['lobe_len'])
		return None

	def send_string_message(self, msg_str):
		""" Take a string, remove all non-printable characters,
		prepend the prefix and post to the next block. """
		# Do string sanitization:
		msg_str = filter(lambda x: x in string.printable, msg_str)
		send_str = "[{}] {}".format(self.prefix, msg_str)
		# Create an empty PMT (contains only spaces):
		send_pmt = pmt.make_u8vector(len(send_str), ord(' '))
		# Copy all characters to the u8vector:
		for i in range(len(send_str)):
			pmt.u8vector_set(send_pmt, i, ord(send_str[i]))
		# Send the message:
		self.message_port_pub(pmt.intern('out'), pmt.cons(pmt.PMT_NIL, send_pmt))

    def handle_string_msg(self, msg_pmt):
		""" Receiver a u8vector on the input port, and print it out. """
		# Collect metadata, convert to Python format:
		meta = pmt.to_python(pmt.car(msg_pmt))
		# Collect message, convert to Python format:
		msg = pmt.cdr(msg_pmt)
		# Make sure it's a u8vector
		if not pmt.is_u8vector(msg):
			print "[ERROR] Received invalid message type.\n"
			return
		# Convert to string:
		msg_str = "".join([chr(x) for x in pmt.u8vector_elements(msg)])
		# Just for good measure, and to avoid attacks, let's filter again:
		msg_str = filter(lambda x: x in string.printable, msg_str)
		# Print string, and if available, the metadata:
		print msg_str
		if meta is not None:
			print "[METADATA]: ", meta

