#!/usr/bin/env python
# 
# Copyright 2014 GermanoCapela at gmail.com
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

# Gnuradio Python Flow Graph
# Title: Ofdm Radio Hier Grc
# Author: Germano Capela
# An OFDM transceiver

from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
import ofdm_tools

class ofdm_tx_rx_hier(gr.hier_block2):

    def __init__(self, fft_len=64, payload_bps=2):
        gr.hier_block2.__init__(
            self, "OFDM TX RX Hier paths",
            gr.io_signaturev(2, 2, [gr.sizeof_char*1, gr.sizeof_gr_complex*1]),
            gr.io_signaturev(2, 2, [gr.sizeof_char*1, gr.sizeof_gr_complex*1]),
        )

        ##################################################
        # Parameters
        ##################################################
        self.fft_len = fft_len
        self.payload_bps = payload_bps

        ##################################################
        # Variables
        ##################################################
        self.len_tag_key = len_tag_key = "packet_len"

        ##################################################
        # Blocks
        ##################################################
        self.tag_gate_tx = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        self.ofdm_tx = ofdm_tools.ofdm_txrx_modules.ofdm_tx(
        	  fft_len=fft_len, cp_len=fft_len/4,
        	  packet_length_tag_key=len_tag_key,
        	  bps_header=1,
        	  bps_payload=payload_bps,
        	  rolloff=0,
        	  debug_log=False,
        	  scramble_bits=False
        	 )
        self.ofdm_rx = ofdm_tools.ofdm_txrx_modules.ofdm_rx(
        	  fft_len=fft_len, cp_len=fft_len/4,
        	  frame_length_tag_key='frame_'+"rx_len",
        	  packet_length_tag_key=len_tag_key,
        	  bps_header=1,
        	  bps_payload=payload_bps,
        	  debug_log=False,
        	  scramble_bits=False
        	 )
        self.multiply_const_tx = blocks.multiply_const_vcc((.01, ))
        self.agc_rx = analog.agc2_cc(1e-1, 1e-2, 1.0, 1.0)
        self.agc_rx.set_max_gain(65536)

        ##################################################
        # Connections
        ##################################################
        self.connect((self, 0), (self.ofdm_tx, 0))
        self.connect((self, 1), (self.agc_rx, 0))
        self.connect((self.agc_rx, 0), (self.ofdm_rx, 0))
        self.connect((self.ofdm_rx, 0), (self, 0))
        self.connect((self.multiply_const_tx, 0), (self, 1))
        self.connect((self.ofdm_tx, 0), (self.tag_gate_tx, 0))
        self.connect((self.tag_gate_tx, 0), (self.multiply_const_tx, 0))

    def get_fft_len(self):
        return self.fft_len

    def set_fft_len(self, fft_len):
        self.fft_len = fft_len

    def get_payload_bps(self):
        return self.payload_bps

    def set_payload_bps(self, payload_bps):
        self.payload_bps = payload_bps

    def get_len_tag_key(self):
        return self.len_tag_key

    def set_len_tag_key(self, len_tag_key):
        self.len_tag_key = len_tag_key

