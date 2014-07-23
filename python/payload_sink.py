#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 Germano Capela.
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

from gnuradio import gr, blocks
import gnuradio.gr.gr_threading as _threading

class payload_sink(gr.hier_block2):
	"""
	hierarchical block that triggers a receive callback each time a packet is received
	"""
	def __init__(self, callback = ''):
		gr.hier_block2.__init__(self, "payload_sink",
				gr.io_signature(1, 1, gr.sizeof_char*1),
				gr.io_signature(0, 0, 0))

		# initialize the message queue
		self.sink_queue = gr.msg_queue()
		self.callback = callback

		#data sink!
		self.msg_sink = blocks.message_sink(gr.sizeof_char*1, self.sink_queue, False)     

		# Connections
		self.connect(self, self.msg_sink)

		self._watcher = _queue_watcher_thread_mod(self.sink_queue, self.callback)

	def set_callback(self, callback):
		self.callback = callback

#listening thread for received packets - no CRC check
class _queue_watcher_thread_mod(_threading.Thread):
	def __init__(self, rcvd_pktq, callback):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_pktq = rcvd_pktq
		self.callback = callback
		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:
			msg = self.rcvd_pktq.delete_head()
			payload = msg.to_string()
			if self.callback:
				self.callback(payload)
