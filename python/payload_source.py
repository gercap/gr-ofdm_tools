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

class payload_source(gr.hier_block2):
	"""
	hierarchical block that generates a tagged stream from a message source
	"""
	def __init__(self, packet_len = 500):
		gr.hier_block2.__init__(self,
			"payload_source",
			gr.io_signature(0, 0, 0),
			gr.io_signature(1, 1, gr.sizeof_char*1))

		self.packet_len = packet_len

		# initialize the message queues
		self.source_queue = gr.msg_queue()

		##################################################
		# Blocks
		self.msg_source = blocks.message_source(gr.sizeof_char*1, self.source_queue)
		self.stream_to_tagged_stream_txpath = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, packet_len, "packet_len")

		##################################################
		# Connections
		#Data source
		self.connect(self.msg_source, self.stream_to_tagged_stream_txpath, self)

	def send_pkt_s(self, payload='', eof=False):
		if eof:
			msg = gr.message(1) # tell self._pkt_input we're not sending any more packets
		else:
			msg = gr.message_from_string(payload)
		self.source_queue.insert_tail(msg)

	def get_packet_len(self):
		return self.packet_len

	def set_packet_len(self, packet_len):
		self.packet_len = packet_len
