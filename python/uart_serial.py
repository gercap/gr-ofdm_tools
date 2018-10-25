#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2018 germanocapela at gmail.com.
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
import time, serial, string
from gnuradio import gr
import pmt
import gnuradio.gr.gr_threading as _threading

flow_control_def = {'HARDWARE':(False, True),'XONXOFF':(True, False),'NO':(False, False)}
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in xrange(0, len(l), n):
		yield l[i:i + n]

class uart_serial(gr.basic_block):
	"""
	docstring for block uart_serial
	"""
	def __init__(self, com_id, baud_rate, parity, stop_bits, char_size, flow_control, max_pkt_size):
		gr.basic_block.__init__(self,
			name="uart_serial",
			in_sig=None,
			out_sig=None
		)
		self.max_pkt_size = int(max_pkt_size)	

		self.settings = {}
		self.settings['com_id'] = com_id
		self.settings['baud_rate'] = int(baud_rate)
		self.settings['parity'] = parity
		self.settings['stop_bits'] = float(stop_bits)
		self.settings['char_size'] = int(char_size)
		self.settings['flow_control'] = flow_control
		self.xon_xoff, self.rts_cts = flow_control_def[(self.settings['flow_control'])]

		self.serial_com_interface = self.open_serial()

		self.message_port_register_out(pmt.intern('out'))
		self.message_port_register_in(pmt.intern('in'))
		self.set_msg_handler(pmt.intern('in'), self.handle_rx_msg)

		####THREADS####
		self._main = tx_thread(self.serial_com_interface, self.handle_tx_msg, self.max_pkt_size)

	#handle message comming from flowgraph  - send to serial
	def handle_rx_msg(self, msg):
		_msg = pmt.to_python(msg)
		#print "from flowgraph to serial", "".join([chr(item) for item in _msg[1]])
		self.serial_com_interface.write("".join([chr(item) for item in _msg[1]]))

	#handle message comming from serial - send to flowgraph
	def handle_tx_msg(self, msg):
		_pmt = pmt.cons(pmt.make_dict(), pmt.pmt_to_python.numpy_to_uvector(np.array([ord(c) for c in msg], np.uint8)))
		self.message_port_pub(pmt.intern('out'), _pmt)

	def open_serial(self):
		try:
			serial_com_interface = serial.Serial(
				port=self.settings['com_id'],
				baudrate=self.settings['baud_rate'],
				parity=self.settings['parity'],
				stopbits=int(self.settings['stop_bits']),
				bytesize=int(self.settings['char_size']),
				xonxoff = self.xon_xoff,
				rtscts = self.rts_cts,
				writeTimeout = 0,
			)
			print("serial %s open? %s" % (str(serial_com_interface.port), serial_com_interface.isOpen()) )
			print("serial settings %s" % (str(serial_com_interface.getSettingsDict())) )

		except:
			print("failed to open serial port")
			print("check %s port definition" % (self.settings['com_id']) )
			self.port_is_open = False
			return None
		else:
			serial_com_interface.flushInput()
			serial_com_interface.flushOutput()
			self.port_is_open = True
			self.active_port_settings = serial_com_interface.getSettingsDict()
			self.active_port_id = serial_com_interface.port
			return serial_com_interface

#read serial - send to flowgraph
class tx_thread(_threading.Thread):
	def __init__(self, serial_com_interface, handle_tx_msg_callback, max_pkt_size):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.serial_com_interface = serial_com_interface
		self.handle_tx_msg_callback = handle_tx_msg_callback
		self.max_pkt_size = max_pkt_size

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.start()
	
	def run(self):
		while self.keep_running:
			msg = ""
			while self.serial_com_interface.inWaiting():  # Or: while ser.inWaiting():
				msg += self.serial_com_interface.read(1)

			if len(msg)>0:
				#avoid gnuradio's complaints abou buffer size or number of symbols
				for chunk in chunks(msg, self.max_pkt_size):
					self.handle_tx_msg_callback(chunk)
			time.sleep(.001)
