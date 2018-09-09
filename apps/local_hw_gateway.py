#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: GPL-3.0
#
##################################################
# GNU Radio Python Flow Graph
# Title: Local Hw Gateway
# Generated: Sun Sep  9 16:25:17 2018
# GNU Radio version: 3.7.12.0
##################################################

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print "Warning: failed to XInitThreads()"

from PyQt4 import Qt
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
import sys
import threading
import time
from gnuradio import qtgui


class local_hw_gateway(gr.top_block, Qt.QWidget):

    def __init__(self, freq_offset=0, nfft=int(2048*2), ppm=35, server_address="0.0.0.0", sr=int(1.2e6), udp_port=8888):
        gr.top_block.__init__(self, "Local Hw Gateway")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Local Hw Gateway")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "local_hw_gateway")
        self.restoreGeometry(self.settings.value("geometry").toByteArray())


        ##################################################
        # Parameters
        ##################################################
        self.freq_offset = freq_offset
        self.nfft = nfft
        self.ppm = ppm
        self.server_address = server_address
        self.sr = sr
        self.udp_port = udp_port

        ##################################################
        # Variables
        ##################################################
        self.max_tu = max_tu = 1472*20
        self.tune_freq = tune_freq = 103e6
        self.samp_rate = samp_rate = sr
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
        self.zeromq_pub_msg_sink_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:5005', 100)
        self.xmlrpc_server = SimpleXMLRPCServer.SimpleXMLRPCServer((server_address, 7658), allow_none=True)
        self.xmlrpc_server.register_instance(self)
        self.xmlrpc_server_thread = threading.Thread(target=self.xmlrpc_server.serve_forever)
        self.xmlrpc_server_thread.daemon = True
        self.xmlrpc_server_thread.start()
        self.tabs = Qt.QTabWidget()
        self.tabs_widget_0 = Qt.QWidget()
        self.tabs_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_0)
        self.tabs_grid_layout_0 = Qt.QGridLayout()
        self.tabs_layout_0.addLayout(self.tabs_grid_layout_0)
        self.tabs.addTab(self.tabs_widget_0, 'Main')
        self.tabs_widget_1 = Qt.QWidget()
        self.tabs_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_1)
        self.tabs_grid_layout_1 = Qt.QGridLayout()
        self.tabs_layout_1.addLayout(self.tabs_grid_layout_1)
        self.tabs.addTab(self.tabs_widget_1, 'L')
        self.tabs_widget_2 = Qt.QWidget()
        self.tabs_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_2)
        self.tabs_grid_layout_2 = Qt.QGridLayout()
        self.tabs_layout_2.addLayout(self.tabs_grid_layout_2)
        self.tabs.addTab(self.tabs_widget_2, 'R')
        self.top_grid_layout.addWidget(self.tabs)
        self.osmosdr_source_0_0 = osmosdr.source( args="numchan=" + str(1) + " " + '' )
        self.osmosdr_source_0_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0_0.set_center_freq(tune_freq+offset, 0)
        self.osmosdr_source_0_0.set_freq_corr(ppm_corr, 0)
        self.osmosdr_source_0_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0_0.set_gain_mode(False, 0)
        self.osmosdr_source_0_0.set_gain(rf_gain, 0)
        self.osmosdr_source_0_0.set_if_gain(if_gain, 0)
        self.osmosdr_source_0_0.set_bb_gain(bb_gain, 0)
        self.osmosdr_source_0_0.set_antenna('', 0)
        self.osmosdr_source_0_0.set_bandwidth(0, 0)

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
        self.connect((self.osmosdr_source_0_0, 0), (self.ofdm_tools_local_worker_0, 0))

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "local_hw_gateway")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

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

    def get_server_address(self):
        return self.server_address

    def set_server_address(self, server_address):
        self.server_address = server_address

    def get_sr(self):
        return self.sr

    def set_sr(self, sr):
        self.sr = sr
        self.set_samp_rate(self.sr)

    def get_udp_port(self):
        return self.udp_port

    def set_udp_port(self, udp_port):
        self.udp_port = udp_port

    def get_max_tu(self):
        return self.max_tu

    def set_max_tu(self, max_tu):
        self.max_tu = max_tu
        self.set_fragments_per_fft(int(math.ceil((self.nfft*4.0+2.0)/self.max_tu)))

    def get_tune_freq(self):
        return self.tune_freq

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq
        self.osmosdr_source_0_0.set_center_freq(self.tune_freq+self.offset, 0)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.osmosdr_source_0_0.set_sample_rate(self.samp_rate)
        self.ofdm_tools_local_worker_0.set_sample_rate(self.samp_rate)

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.osmosdr_source_0_0.set_gain(self.rf_gain, 0)

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
        self.osmosdr_source_0_0.set_freq_corr(self.ppm_corr, 0)

    def get_offset(self):
        return self.offset

    def set_offset(self, offset):
        self.offset = offset
        self.osmosdr_source_0_0.set_center_freq(self.tune_freq+self.offset, 0)

    def get_if_gain(self):
        return self.if_gain

    def set_if_gain(self, if_gain):
        self.if_gain = if_gain
        self.osmosdr_source_0_0.set_if_gain(self.if_gain, 0)

    def get_fragments_per_fft(self):
        return self.fragments_per_fft

    def set_fragments_per_fft(self, fragments_per_fft):
        self.fragments_per_fft = fragments_per_fft

    def get_bb_gain(self):
        return self.bb_gain

    def set_bb_gain(self, bb_gain):
        self.bb_gain = bb_gain
        self.osmosdr_source_0_0.set_bb_gain(self.bb_gain, 0)

    def get_av(self):
        return self.av

    def set_av(self, av):
        self.av = av
        self.ofdm_tools_local_worker_0.set_average(self.av)


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "-o", "--freq-offset", dest="freq_offset", type="eng_float", default=eng_notation.num_to_str(0),
        help="Set freq_offset [default=%default]")
    parser.add_option(
        "-f", "--nfft", dest="nfft", type="intx", default=int(2048*2),
        help="Set nfft [default=%default]")
    parser.add_option(
        "-p", "--ppm", dest="ppm", type="eng_float", default=eng_notation.num_to_str(35),
        help="Set ppm [default=%default]")
    parser.add_option(
        "-a", "--server-address", dest="server_address", type="string", default="0.0.0.0",
        help="Set server_address [default=%default]")
    parser.add_option(
        "-s", "--sr", dest="sr", type="intx", default=int(1.2e6),
        help="Set sr [default=%default]")
    parser.add_option(
        "-u", "--udp-port", dest="udp_port", type="intx", default=8888,
        help="Set udp_port [default=%default]")
    return parser


def main(top_block_cls=local_hw_gateway, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()
    if gr.enable_realtime_scheduling() != gr.RT_OK:
        print "Error: failed to enable real-time scheduling."

    from distutils.version import StrictVersion
    if StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(freq_offset=options.freq_offset, nfft=options.nfft, ppm=options.ppm, server_address=options.server_address, sr=options.sr, udp_port=options.udp_port)
    tb.start()
    tb.show()

    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()


if __name__ == '__main__':
    main()
