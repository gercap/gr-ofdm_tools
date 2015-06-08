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

from gnuradio import gr, blocks, digital
import ofdm_tools, ofdm_cr_tools

class payload_source_pdu(gr.hier_block2):
	"""
	hierarchical block that generates a tagged stream from a message source
	"""
	def __init__(self, callback):
		gr.hier_block2.__init__(self,
			"payload_source_pdu",
			gr.io_signature(0, 0, 0),
			gr.io_signature(1, 1, gr.sizeof_char*1))
		self.callback = callback
		##################################################
		# Blocks
		self.msg_source = ofdm_cr_tools.message_handler(self.callback)
		self.generate_crc = digital.crc32_async_bb(False)
		self.pdu_to_tagged_stream = blocks.pdu_to_tagged_stream(blocks.byte_t, "packet_len")

		##################################################
		# Connections
		self.msg_connect((self.msg_source, 'out'), (self.generate_crc, 'in'))
		self.msg_connect((self.generate_crc, 'out'), (self.pdu_to_tagged_stream, 'pdus'))
		self.connect((self.pdu_to_tagged_stream, 0), (self, 0))
