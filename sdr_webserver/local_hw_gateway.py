#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: GPL-3.0
#
##################################################
# GNU Radio Python Flow Graph
# Title: Local Hw Gateway
# Generated: Sun Sep 16 17:11:21 2018
# GNU Radio version: 3.7.12.0
##################################################

from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import zeromq
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import SimpleXMLRPCServer
import math
import ofdm_tools
import osmosdr
import threading
import time


class local_hw_gateway(gr.top_block):

    def __init__(self, arg="", freq_offset=0, nfft=int(2048), ppm=0, sr=int(2.4e6), zmq_port=5005):
        gr.top_block.__init__(self, "Local Hw Gateway")

        ##################################################
        # Parameters
        ##################################################
        self.arg = arg
        self.freq_offset = freq_offset
        self.nfft = nfft
        self.ppm = ppm
        self.sr = sr
        self.zmq_port = zmq_port

        ##################################################
        # Variables
        ##################################################
        self.max_tu = max_tu = 1472*20
        self.tune_freq = tune_freq = 103e6
        self.samp_rate = samp_rate = sr
        self.rf_gain_stop = rf_gain_stop = 0
        self.rf_gain_step = rf_gain_step = 0
        self.rf_gain_start = rf_gain_start = 0
        self.rf_gain = rf_gain = 45
        self.req_mtu = req_mtu = nfft*4
        self.rate = rate = 1
        self.precision = precision = True
        self.ppm_corr = ppm_corr = ppm
        self.offset = offset = freq_offset
        self.if_gain = if_gain = 20
        self.fragments_per_fft = fragments_per_fft = int(math.ceil((nfft*4.0+2.0)/max_tu))
        self.bb_gain = bb_gain = 20
        self.av = av = 0.8

        ##################################################
        # Blocks
        ##################################################
        self.rf_source = osmosdr.source( args="numchan=" + str(1) + " " + arg )
        self.rf_source.set_sample_rate(samp_rate)
        self.rf_source.set_center_freq(tune_freq+offset, 0)
        self.rf_source.set_freq_corr(ppm_corr, 0)
        self.rf_source.set_dc_offset_mode(0, 0)
        self.rf_source.set_iq_balance_mode(0, 0)
        self.rf_source.set_gain_mode(False, 0)
        self.rf_source.set_gain(rf_gain, 0)
        self.rf_source.set_if_gain(if_gain, 0)
        self.rf_source.set_bb_gain(bb_gain, 0)
        self.rf_source.set_antenna('', 0)
        self.rf_source.set_bandwidth(samp_rate, 0)

        self.zeromq_pub_msg_sink_0 = zeromq.pub_msg_sink("tcp://0.0.0.0:"+str(zmq_port), 100)
        self.xmlrpc_server = SimpleXMLRPCServer.SimpleXMLRPCServer(("0.0.0.0", 7658), allow_none=True)
        self.xmlrpc_server.register_instance(self)
        self.xmlrpc_server_thread = threading.Thread(target=self.xmlrpc_server.serve_forever)
        self.xmlrpc_server_thread.daemon = True
        self.xmlrpc_server_thread.start()

        def _rf_gain_stop_probe():
            while True:
                val = self.rf_source.get_gain_range().stop()
                try:
                    self.set_rf_gain_stop(val)
                except AttributeError:
                    pass
                time.sleep(1.0 / (0.001))
        _rf_gain_stop_thread = threading.Thread(target=_rf_gain_stop_probe)
        _rf_gain_stop_thread.daemon = True
        _rf_gain_stop_thread.start()


        def _rf_gain_step_probe():
            while True:
                val = self.rf_source.get_gain_range().step()
                try:
                    self.set_rf_gain_step(val)
                except AttributeError:
                    pass
                time.sleep(1.0 / (0.001))
        _rf_gain_step_thread = threading.Thread(target=_rf_gain_step_probe)
        _rf_gain_step_thread.daemon = True
        _rf_gain_step_thread.start()


        def _rf_gain_start_probe():
            while True:
                val = self.rf_source.get_gain_range().start()
                try:
                    self.set_rf_gain_start(val)
                except AttributeError:
                    pass
                time.sleep(1.0 / (0.001))
        _rf_gain_start_thread = threading.Thread(target=_rf_gain_start_probe)
        _rf_gain_start_thread.daemon = True
        _rf_gain_start_thread.start()

        self.ofdm_tools_local_worker_0 = ofdm_tools.local_worker(
          fft_len=nfft,
          sample_rate=samp_rate,
          average=av,
          rate=rate,
          max_tu=max_tu,
          data_precision=precision,
          )



        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.ofdm_tools_local_worker_0, 'pdus'), (self.zeromq_pub_msg_sink_0, 'in'))
        self.connect((self.rf_source, 0), (self.ofdm_tools_local_worker_0, 0))

    def get_arg(self):
        return self.arg

    def set_arg(self, arg):
        self.arg = arg

    def get_freq_offset(self):
        return self.freq_offset

    def set_freq_offset(self, freq_offset):
        self.freq_offset = freq_offset
        self.set_offset(self.freq_offset)

    def get_nfft(self):
        return self.nfft

    def set_nfft(self, nfft):
        self.nfft = nfft
        self.set_req_mtu(self.nfft*4)
        self.set_fragments_per_fft(int(math.ceil((self.nfft*4.0+2.0)/self.max_tu)))

    def get_ppm(self):
        return self.ppm

    def set_ppm(self, ppm):
        self.ppm = ppm
        self.set_ppm_corr(self.ppm)

    def get_sr(self):
        return self.sr

    def set_sr(self, sr):
        self.sr = sr
        self.set_samp_rate(self.sr)

    def get_zmq_port(self):
        return self.zmq_port

    def set_zmq_port(self, zmq_port):
        self.zmq_port = zmq_port

    def get_max_tu(self):
        return self.max_tu

    def set_max_tu(self, max_tu):
        self.max_tu = max_tu
        self.set_fragments_per_fft(int(math.ceil((self.nfft*4.0+2.0)/self.max_tu)))

    def get_tune_freq(self):
        return self.tune_freq

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq
        self.rf_source.set_center_freq(self.tune_freq+self.offset, 0)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rf_source.set_sample_rate(self.samp_rate)
        self.rf_source.set_bandwidth(self.samp_rate, 0)
        self.ofdm_tools_local_worker_0.set_sample_rate(self.samp_rate)

    def get_rf_gain_stop(self):
        return self.rf_gain_stop

    def set_rf_gain_stop(self, rf_gain_stop):
        self.rf_gain_stop = rf_gain_stop

    def get_rf_gain_step(self):
        return self.rf_gain_step

    def set_rf_gain_step(self, rf_gain_step):
        self.rf_gain_step = rf_gain_step

    def get_rf_gain_start(self):
        return self.rf_gain_start

    def set_rf_gain_start(self, rf_gain_start):
        self.rf_gain_start = rf_gain_start

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.rf_source.set_gain(self.rf_gain, 0)

    def get_req_mtu(self):
        return self.req_mtu

    def set_req_mtu(self, req_mtu):
        self.req_mtu = req_mtu

    def get_rate(self):
        return self.rate

    def set_rate(self, rate):
        self.rate = rate
        self.ofdm_tools_local_worker_0.set_rate(self.rate)

    def get_precision(self):
        return self.precision

    def set_precision(self, precision):
        self.precision = precision
        self.ofdm_tools_local_worker_0.set_data_precision(self.precision)

    def get_ppm_corr(self):
        return self.ppm_corr

    def set_ppm_corr(self, ppm_corr):
        self.ppm_corr = ppm_corr
        self.rf_source.set_freq_corr(self.ppm_corr, 0)

    def get_offset(self):
        return self.offset

    def set_offset(self, offset):
        self.offset = offset
        self.rf_source.set_center_freq(self.tune_freq+self.offset, 0)

    def get_if_gain(self):
        return self.if_gain

    def set_if_gain(self, if_gain):
        self.if_gain = if_gain
        self.rf_source.set_if_gain(self.if_gain, 0)

    def get_fragments_per_fft(self):
        return self.fragments_per_fft

    def set_fragments_per_fft(self, fragments_per_fft):
        self.fragments_per_fft = fragments_per_fft

    def get_bb_gain(self):
        return self.bb_gain

    def set_bb_gain(self, bb_gain):
        self.bb_gain = bb_gain
        self.rf_source.set_bb_gain(self.bb_gain, 0)

    def get_av(self):
        return self.av

    def set_av(self, av):
        self.av = av
        self.ofdm_tools_local_worker_0.set_average(self.av)


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "-a", "--arg", dest="arg", type="string", default="",
        help="Set osmocom device arg [default=%default]")
    parser.add_option(
        "-o", "--freq-offset", dest="freq_offset", type="eng_float", default=eng_notation.num_to_str(0),
        help="Set freq_offset [default=%default]")
    parser.add_option(
        "-f", "--nfft", dest="nfft", type="intx", default=int(2048),
        help="Set nfft [default=%default]")
    parser.add_option(
        "-p", "--ppm", dest="ppm", type="eng_float", default=eng_notation.num_to_str(0),
        help="Set ppm [default=%default]")
    parser.add_option(
        "-s", "--sr", dest="sr", type="intx", default=int(2.4e6),
        help="Set sr [default=%default]")
    parser.add_option(
        "-u", "--zmq-port", dest="zmq_port", type="intx", default=5005,
        help="Set zmq_port [default=%default]")
    return parser


def main(top_block_cls=local_hw_gateway, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()
    if gr.enable_realtime_scheduling() != gr.RT_OK:
        print "Error: failed to enable real-time scheduling."

    tb = top_block_cls(arg=options.arg, freq_offset=options.freq_offset, nfft=options.nfft, ppm=options.ppm, sr=options.sr, zmq_port=options.zmq_port)
    tb.start()
    try:
        raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
