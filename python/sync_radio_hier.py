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


from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import fft
from gnuradio import filter
from gnuradio import gr
from gnuradio.digital.utils import tagged_streams
from gnuradio.fft import window
from gnuradio.filter import firdes

class sync_radio_hier(gr.hier_block2):

    def __init__(self, samp_rate=10000):
        gr.hier_block2.__init__(
            self, "Sync Radio Hier Grc",
            gr.io_signaturev(2, 2, [gr.sizeof_char*1, gr.sizeof_gr_complex*1]),
            gr.io_signaturev(2, 2, [gr.sizeof_char*1, gr.sizeof_gr_complex*1]),
        )

        ##################################################
        # Parameters
        ##################################################
        self.samp_rate = samp_rate

        ##################################################
        # Variables
        ##################################################
        self.sync_word2 = sync_word2 = [0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,(1+0j),(-1+0j),(-1+0j),(-1+0j),(1+0j),(-1+0j),(1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(1+0j),0j,(1+0j),(-1+0j),(1+0j),(1+0j),(1+0j),(-1+0j),(1+0j),(1+0j),(1+0j),(-1+0j),(1+0j),(1+0j),(1+0j),(1+0j),(-1+0j),0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j]
        self.sync_word1 = sync_word1 = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,1.42,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
        self.pilot_symbols = pilot_symbols = ((1, -1,),)
        self.pilot_carriers = pilot_carriers = ((-13, 12,),)
        self.payload_mod = payload_mod = digital.constellation_qpsk() 
        self.packet_length_tag_key = packet_length_tag_key = "packet_len"
        self.occupied_carriers = occupied_carriers = ([-16, -15, -14, -12, -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15],)
        self.length_tag_key = length_tag_key = "frame_len"
        self.header_mod = header_mod = digital.constellation_bpsk()
        self.fft_len = fft_len = (len(sync_word1)+len(sync_word2))/2
        self.rolloff = rolloff = 0
        self.payload_equalizer = payload_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, payload_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols, 1)
        self.len_ocup_carr = len_ocup_carr = len(occupied_carriers[0])
        self.header_formatter = header_formatter = digital.packet_header_ofdm(occupied_carriers, n_syms=1, len_tag_key=packet_length_tag_key, frame_len_tag_key=length_tag_key, bits_per_header_sym=header_mod.bits_per_symbol(), bits_per_payload_sym=payload_mod.bits_per_symbol(), scramble_header=True)
        self.header_equalizer = header_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, header_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols)
        self.forward_OOB = forward_OOB = [0.005277622700213007, 0.03443705907448985, 0.1214101788557494, 0.29179662246081545, 0.52428014905364, 0.7350677973792328, 0.8210395030022875, 0.7350677973792348, 0.5242801490536404, 0.291796622460816, 0.1214101788557501, 0.03443705907448997, 0.005277622700213012]
        self.feedback_OOB = feedback_OOB = [1.0, -1.0455317889337852, 3.9201525346250072, -3.9114761684448958, 6.54266144224035, -5.737287389902878, 5.820328302284336, -4.134700802700442, 2.7949972248757664, -1.4584448495689168, 0.6358650797085171, -0.19847981428665007, 0.04200458351675313]
        self.cp_len = cp_len = fft_len/4
        self.active_carriers = active_carriers = len(occupied_carriers[0])+4

        ##################################################
        # Blocks
        ##################################################
        self.iir_filter_xxx_1 = filter.iir_filter_ccd((forward_OOB), (feedback_OOB), False)
        self.fft_vxx_txpath = fft.fft_vcc(fft_len, False, (()), True, 1)
        self.fft_vxx_2_rxpath = fft.fft_vcc(fft_len, True, (), True, 1)
        self.fft_vxx_1_rxpath = fft.fft_vcc(fft_len, True, (()), True, 1)
        self.digital_packet_headerparser_b_rxpath = digital.packet_headerparser_b(header_formatter.base())
        self.digital_packet_headergenerator_bb_txpath = digital.packet_headergenerator_bb(header_formatter.formatter(), "packet_len")
        self.digital_ofdm_sync_sc_cfb_rxpath = digital.ofdm_sync_sc_cfb(fft_len, fft_len/4, False)
        self.digital_ofdm_serializer_vcc_payload_rxpath = digital.ofdm_serializer_vcc(fft_len, occupied_carriers, length_tag_key, packet_length_tag_key, 1, "", True)
        self.digital_ofdm_serializer_vcc_header_rxpath = digital.ofdm_serializer_vcc(fft_len, occupied_carriers, length_tag_key, "", 0, "", True)
        self.digital_ofdm_frame_equalizer_vcvc_2_rxpath = digital.ofdm_frame_equalizer_vcvc(payload_equalizer.base(), cp_len, length_tag_key, True, 0)
        self.digital_ofdm_frame_equalizer_vcvc_1_rxpath = digital.ofdm_frame_equalizer_vcvc(header_equalizer.base(), cp_len, length_tag_key, True, 1)
        self.digital_ofdm_cyclic_prefixer_txpath = digital.ofdm_cyclic_prefixer(fft_len, fft_len+cp_len, rolloff, packet_length_tag_key)
        (self.digital_ofdm_cyclic_prefixer_txpath).set_min_output_buffer(24000)
        self.digital_ofdm_chanest_vcvc_rxpath = digital.ofdm_chanest_vcvc((sync_word1), (sync_word2), 1, 0, 3, False)
        self.digital_ofdm_carrier_allocator_cvc_txpath = digital.ofdm_carrier_allocator_cvc(fft_len, occupied_carriers, pilot_carriers, pilot_symbols, (sync_word1, sync_word2), packet_length_tag_key)
        (self.digital_ofdm_carrier_allocator_cvc_txpath).set_min_output_buffer(16000)
        self.digital_header_payload_demux_rxpath = digital.header_payload_demux(
        	  3,
        	  fft_len,
        	  cp_len,
        	  length_tag_key,
        	  "",
        	  True,
        	  gr.sizeof_gr_complex,
        	  "rx_time",
                  samp_rate,
                  (),
            )
        #self.digital_crc32_bb_txpath = digital.crc32_bb(False, packet_length_tag_key)
        #self.digital_crc32_bb_rxpath = digital.crc32_bb(True, packet_length_tag_key)
        self.digital_constellation_decoder_cb_1_rxpath = digital.constellation_decoder_cb(payload_mod.base())
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(header_mod.base())
        self.digital_chunks_to_symbols_x_txpath = digital.chunks_to_symbols_bc((payload_mod.points()), 1)
        self.digital_chunks_to_symbols_txpath = digital.chunks_to_symbols_bc((header_mod.points()), 1)
        self.blocks_tagged_stream_mux_txpath = blocks.tagged_stream_mux(gr.sizeof_gr_complex*1, packet_length_tag_key, 0)
        (self.blocks_tagged_stream_mux_txpath).set_min_output_buffer(16000)
        self.blocks_tag_gate_txpath = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        self.blocks_repack_bits_bb_txpath = blocks.repack_bits_bb(8, payload_mod.bits_per_symbol(), packet_length_tag_key, False)
        self.blocks_repack_bits_bb_rxpath = blocks.repack_bits_bb(payload_mod.bits_per_symbol(), 8, packet_length_tag_key, True)
        self.blocks_multiply_xx_rxpath = blocks.multiply_vcc(1)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vcc((.01, ))
        self.blocks_delay_rxpath = blocks.delay(gr.sizeof_gr_complex*1, fft_len+fft_len/4)
        self.analog_frequency_modulator_fc_rxpath = analog.frequency_modulator_fc(-2.0/fft_len)
        self.analog_agc2_xx_0 = analog.agc2_cc(1e-1, 1e-2, 1.0, 1.0)
        self.analog_agc2_xx_0.set_max_gain(65536)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.digital_ofdm_sync_sc_cfb_rxpath, 0), (self.analog_frequency_modulator_fc_rxpath, 0))
        self.connect((self.analog_agc2_xx_0, 0), (self.digital_ofdm_sync_sc_cfb_rxpath, 0))
        self.connect((self.analog_agc2_xx_0, 0), (self.blocks_delay_rxpath, 0))
        self.connect((self.digital_packet_headergenerator_bb_txpath, 0), (self.digital_chunks_to_symbols_txpath, 0))
        self.connect((self.blocks_repack_bits_bb_txpath, 0), (self.digital_chunks_to_symbols_x_txpath, 0))
        self.connect((self.digital_chunks_to_symbols_txpath, 0), (self.blocks_tagged_stream_mux_txpath, 0))
        self.connect((self.digital_chunks_to_symbols_x_txpath, 0), (self.blocks_tagged_stream_mux_txpath, 1))
        self.connect((self.digital_ofdm_cyclic_prefixer_txpath, 0), (self.blocks_tag_gate_txpath, 0))
        self.connect((self.fft_vxx_txpath, 0), (self.digital_ofdm_cyclic_prefixer_txpath, 0))
        self.connect((self.blocks_tagged_stream_mux_txpath, 0), (self.digital_ofdm_carrier_allocator_cvc_txpath, 0))
        self.connect((self.digital_ofdm_carrier_allocator_cvc_txpath, 0), (self.fft_vxx_txpath, 0))
        self.connect((self.digital_header_payload_demux_rxpath, 0), (self.fft_vxx_1_rxpath, 0))
        self.connect((self.fft_vxx_1_rxpath, 0), (self.digital_ofdm_chanest_vcvc_rxpath, 0))
        self.connect((self.digital_ofdm_frame_equalizer_vcvc_1_rxpath, 0), (self.digital_ofdm_serializer_vcc_header_rxpath, 0))
        self.connect((self.digital_ofdm_chanest_vcvc_rxpath, 0), (self.digital_ofdm_frame_equalizer_vcvc_1_rxpath, 0))
        self.connect((self.digital_header_payload_demux_rxpath, 1), (self.fft_vxx_2_rxpath, 0))
        self.connect((self.digital_ofdm_frame_equalizer_vcvc_2_rxpath, 0), (self.digital_ofdm_serializer_vcc_payload_rxpath, 0))
        self.connect((self.fft_vxx_2_rxpath, 0), (self.digital_ofdm_frame_equalizer_vcvc_2_rxpath, 0))
        self.connect((self.digital_ofdm_serializer_vcc_payload_rxpath, 0), (self.digital_constellation_decoder_cb_1_rxpath, 0))
        self.connect((self.digital_constellation_decoder_cb_1_rxpath, 0), (self.blocks_repack_bits_bb_rxpath, 0))
        self.connect((self.digital_ofdm_serializer_vcc_header_rxpath, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.analog_frequency_modulator_fc_rxpath, 0), (self.blocks_multiply_xx_rxpath, 0))
        self.connect((self.digital_ofdm_sync_sc_cfb_rxpath, 1), (self.digital_header_payload_demux_rxpath, 1))
        self.connect((self.blocks_multiply_xx_rxpath, 0), (self.digital_header_payload_demux_rxpath, 0))
        self.connect((self.blocks_delay_rxpath, 0), (self.blocks_multiply_xx_rxpath, 1))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_packet_headerparser_b_rxpath, 0))
        self.connect((self, 1), (self.analog_agc2_xx_0, 0))
        self.connect((self.blocks_tag_gate_txpath, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.iir_filter_xxx_1, 0), (self, 1))
        '''
        self.connect((self, 0), (self.digital_crc32_bb_txpath, 0))
        self.connect((self.digital_crc32_bb_txpath, 0), (self.blocks_repack_bits_bb_txpath, 0))
        self.connect((self.digital_crc32_bb_txpath, 0), (self.digital_packet_headergenerator_bb_txpath, 0))
        '''
        self.connect((self, 0), (self.blocks_repack_bits_bb_txpath, 0))
        self.connect((self, 0), (self.digital_packet_headergenerator_bb_txpath, 0))

        '''
        self.connect((self.blocks_repack_bits_bb_rxpath, 0), (self.digital_crc32_bb_rxpath, 0))
        self.connect((self.digital_crc32_bb_rxpath, 0), (self, 0))
        '''
        self.connect((self.blocks_repack_bits_bb_rxpath, 0), (self, 0))

        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.iir_filter_xxx_1, 0))

        ##################################################
        # Asynch Message Connections
        ##################################################
        self.msg_connect(self.digital_packet_headerparser_b_rxpath, "header_data", self.digital_header_payload_demux_rxpath, "header_data")


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_sync_word2(self):
        return self.sync_word2

    def set_sync_word2(self, sync_word2):
        self.sync_word2 = sync_word2
        self.set_fft_len((len(self.sync_word1)+len(self.sync_word2))/2)

    def get_sync_word1(self):
        return self.sync_word1

    def set_sync_word1(self, sync_word1):
        self.sync_word1 = sync_word1
        self.set_fft_len((len(self.sync_word1)+len(self.sync_word2))/2)

    def get_pilot_symbols(self):
        return self.pilot_symbols

    def set_pilot_symbols(self, pilot_symbols):
        self.pilot_symbols = pilot_symbols
        self.set_payload_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.payload_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols, 1))
        self.set_header_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.header_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols))

    def get_pilot_carriers(self):
        return self.pilot_carriers

    def set_pilot_carriers(self, pilot_carriers):
        self.pilot_carriers = pilot_carriers
        self.set_payload_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.payload_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols, 1))
        self.set_header_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.header_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols))

    def get_payload_mod(self):
        return self.payload_mod

    def set_payload_mod(self, payload_mod):
        self.payload_mod = payload_mod
        self.set_header_formatter(digital.packet_header_ofdm(self.occupied_carriers, n_syms=1, len_tag_key=self.packet_length_tag_key, frame_len_tag_key=self.length_tag_key, bits_per_header_sym=self.header_mod.bits_per_symbol(), bits_per_payload_sym=self.payload_mod.bits_per_symbol(), scramble_header=True))
        self.set_payload_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.payload_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols, 1))

    def get_packet_length_tag_key(self):
        return self.packet_length_tag_key

    def set_packet_length_tag_key(self, packet_length_tag_key):
        self.packet_length_tag_key = packet_length_tag_key
        self.set_header_formatter(digital.packet_header_ofdm(self.occupied_carriers, n_syms=1, len_tag_key=self.packet_length_tag_key, frame_len_tag_key=self.length_tag_key, bits_per_header_sym=self.header_mod.bits_per_symbol(), bits_per_payload_sym=self.payload_mod.bits_per_symbol(), scramble_header=True))

    def get_occupied_carriers(self):
        return self.occupied_carriers

    def set_occupied_carriers(self, occupied_carriers):
        self.occupied_carriers = occupied_carriers
        self.set_header_formatter(digital.packet_header_ofdm(self.occupied_carriers, n_syms=1, len_tag_key=self.packet_length_tag_key, frame_len_tag_key=self.length_tag_key, bits_per_header_sym=self.header_mod.bits_per_symbol(), bits_per_payload_sym=self.payload_mod.bits_per_symbol(), scramble_header=True))
        self.set_len_ocup_carr(len(self.occupied_carriers[0]))
        self.set_payload_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.payload_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols, 1))
        self.set_header_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.header_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols))
        self.set_active_carriers(len(self.occupied_carriers[0])+4)

    def get_length_tag_key(self):
        return self.length_tag_key

    def set_length_tag_key(self, length_tag_key):
        self.length_tag_key = length_tag_key
        self.set_header_formatter(digital.packet_header_ofdm(self.occupied_carriers, n_syms=1, len_tag_key=self.packet_length_tag_key, frame_len_tag_key=self.length_tag_key, bits_per_header_sym=self.header_mod.bits_per_symbol(), bits_per_payload_sym=self.payload_mod.bits_per_symbol(), scramble_header=True))

    def get_header_mod(self):
        return self.header_mod

    def set_header_mod(self, header_mod):
        self.header_mod = header_mod
        self.set_header_formatter(digital.packet_header_ofdm(self.occupied_carriers, n_syms=1, len_tag_key=self.packet_length_tag_key, frame_len_tag_key=self.length_tag_key, bits_per_header_sym=self.header_mod.bits_per_symbol(), bits_per_payload_sym=self.payload_mod.bits_per_symbol(), scramble_header=True))
        self.set_header_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.header_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols))

    def get_fft_len(self):
        return self.fft_len

    def set_fft_len(self, fft_len):
        self.fft_len = fft_len
        self.set_payload_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.payload_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols, 1))
        self.set_header_equalizer(digital.ofdm_equalizer_simpledfe(self.fft_len, self.header_mod.base(), self.occupied_carriers, self.pilot_carriers, self.pilot_symbols))
        self.set_cp_len(self.fft_len/4)
        self.analog_frequency_modulator_fc_rxpath.set_sensitivity(-2.0/self.fft_len)
        self.blocks_delay_rxpath.set_dly(self.fft_len+self.fft_len/4)

    def get_rolloff(self):
        return self.rolloff

    def set_rolloff(self, rolloff):
        self.rolloff = rolloff

    def get_payload_equalizer(self):
        return self.payload_equalizer

    def set_payload_equalizer(self, payload_equalizer):
        self.payload_equalizer = payload_equalizer

    def get_len_ocup_carr(self):
        return self.len_ocup_carr

    def set_len_ocup_carr(self, len_ocup_carr):
        self.len_ocup_carr = len_ocup_carr

    def get_header_formatter(self):
        return self.header_formatter

    def set_header_formatter(self, header_formatter):
        self.header_formatter = header_formatter

    def get_header_equalizer(self):
        return self.header_equalizer

    def set_header_equalizer(self, header_equalizer):
        self.header_equalizer = header_equalizer

    def get_forward_OOB(self):
        return self.forward_OOB

    def set_forward_OOB(self, forward_OOB):
        self.forward_OOB = forward_OOB
        self.iir_filter_xxx_1.set_taps((self.forward_OOB), (self.feedback_OOB))

    def get_feedback_OOB(self):
        return self.feedback_OOB

    def set_feedback_OOB(self, feedback_OOB):
        self.feedback_OOB = feedback_OOB
        self.iir_filter_xxx_1.set_taps((self.forward_OOB), (self.feedback_OOB))

    def get_cp_len(self):
        return self.cp_len

    def set_cp_len(self, cp_len):
        self.cp_len = cp_len

    def get_active_carriers(self):
        return self.active_carriers

    def set_active_carriers(self, active_carriers):
        self.active_carriers = active_carriers
