#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Ascii Sink
# Generated: Sun Sep 18 14:38:21 2016
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
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.qtgui import Range, RangeWidget
from optparse import OptionParser
import ofdm_tools
import osmosdr
import sys
import time


class ascii_sink(gr.top_block, Qt.QWidget):

    def __init__(self, nfft=8092, sr=int(1e6)):
        gr.top_block.__init__(self, "Ascii Sink")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Ascii Sink")
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

        self.settings = Qt.QSettings("GNU Radio", "ascii_sink")
        self.restoreGeometry(self.settings.value("geometry").toByteArray())

        ##################################################
        # Parameters
        ##################################################
        self.nfft = nfft
        self.sr = sr

        ##################################################
        # Variables
        ##################################################
        self.width = width = 65
        self.tune_freq = tune_freq = 97e6
        self.samp_rate = samp_rate = sr
        self.rf_gain = rf_gain = 5
        self.if_gain = if_gain = 10
        self.height = height = 30
        self.bb_gain = bb_gain = 10
        self.av = av = 0.8

        ##################################################
        # Blocks
        ##################################################
        self._width_range = Range(0, 200, 1, 65, 200)
        self._width_win = RangeWidget(self._width_range, self.set_width, "width", "counter_slider", int)
        self.top_grid_layout.addWidget(self._width_win, 0,0,1,1)
        self._tune_freq_range = Range(28e6, 1800e6, 1000, 97e6, 200)
        self._tune_freq_win = RangeWidget(self._tune_freq_range, self.set_tune_freq, "tune_freq", "counter_slider", float)
        self.top_layout.addWidget(self._tune_freq_win)
        self._samp_rate_range = Range(250e3, 8e6, 250e3, sr, 200)
        self._samp_rate_win = RangeWidget(self._samp_rate_range, self.set_samp_rate, "samp_rate", "counter_slider", float)
        self.top_layout.addWidget(self._samp_rate_win)
        self._rf_gain_range = Range(0, 50, 1, 5, 200)
        self._rf_gain_win = RangeWidget(self._rf_gain_range, self.set_rf_gain, "rf_gain", "counter_slider", float)
        self.top_grid_layout.addWidget(self._rf_gain_win, 1,0,1,1)
        self._if_gain_range = Range(0, 50, 1, 10, 200)
        self._if_gain_win = RangeWidget(self._if_gain_range, self.set_if_gain, "if_gain", "counter_slider", float)
        self.top_grid_layout.addWidget(self._if_gain_win, 1,1,1,1)
        self._height_range = Range(0, 200, 1, 30, 200)
        self._height_win = RangeWidget(self._height_range, self.set_height, "height", "counter_slider", int)
        self.top_grid_layout.addWidget(self._height_win, 0,1,1,1)
        self._bb_gain_range = Range(0, 50, 1, 10, 200)
        self._bb_gain_win = RangeWidget(self._bb_gain_range, self.set_bb_gain, "bb_gain", "counter_slider", float)
        self.top_grid_layout.addWidget(self._bb_gain_win, 1,2,1,1)
        self._av_range = Range(0, 1, 0.001, 0.8, 200)
        self._av_win = RangeWidget(self._av_range, self.set_av, "av", "counter_slider", float)
        self.top_layout.addWidget(self._av_win)
        self.osmosdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + '' )
        self.osmosdr_source_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0.set_center_freq(tune_freq, 0)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(2, 0)
        self.osmosdr_source_0.set_gain_mode(False, 0)
        self.osmosdr_source_0.set_gain(rf_gain, 0)
        self.osmosdr_source_0.set_if_gain(if_gain, 0)
        self.osmosdr_source_0.set_bb_gain(bb_gain, 0)
        self.osmosdr_source_0.set_antenna('', 0)
        self.osmosdr_source_0.set_bandwidth(0, 0)
          
        self.ofdm_tools_ascii_plot_0 = ofdm_tools.ascii_plot(
          fft_len=int(nfft),
          sample_rate=int(samp_rate), 
          tune_freq=tune_freq, 
          average=av, 
          rate=5,
          width=width,
          height=height,
          )

        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source_0, 0), (self.ofdm_tools_ascii_plot_0, 0))    

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "ascii_sink")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def get_nfft(self):
        return self.nfft

    def set_nfft(self, nfft):
        self.nfft = nfft

    def get_sr(self):
        return self.sr

    def set_sr(self, sr):
        self.sr = sr
        self.set_samp_rate(self.sr)

    def get_width(self):
        return self.width

    def set_width(self, width):
        self.width = width
        self.ofdm_tools_ascii_plot_0.set_width(self.width)

    def get_tune_freq(self):
        return self.tune_freq

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq
        self.osmosdr_source_0.set_center_freq(self.tune_freq, 0)
        self.ofdm_tools_ascii_plot_0.set_tune_freq(self.tune_freq)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.osmosdr_source_0.set_sample_rate(self.samp_rate)
        self.ofdm_tools_ascii_plot_0.set_sample_rate(int(self.samp_rate))

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.osmosdr_source_0.set_gain(self.rf_gain, 0)

    def get_if_gain(self):
        return self.if_gain

    def set_if_gain(self, if_gain):
        self.if_gain = if_gain
        self.osmosdr_source_0.set_if_gain(self.if_gain, 0)

    def get_height(self):
        return self.height

    def set_height(self, height):
        self.height = height
        self.ofdm_tools_ascii_plot_0.set_height(self.height)

    def get_bb_gain(self):
        return self.bb_gain

    def set_bb_gain(self, bb_gain):
        self.bb_gain = bb_gain
        self.osmosdr_source_0.set_bb_gain(self.bb_gain, 0)

    def get_av(self):
        return self.av

    def set_av(self, av):
        self.av = av
        self.ofdm_tools_ascii_plot_0.set_average(self.av)


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "-f", "--nfft", dest="nfft", type="intx", default=8092,
        help="Set nfft [default=%default]")
    parser.add_option(
        "-s", "--sr", dest="sr", type="intx", default=int(1e6),
        help="Set sr [default=%default]")
    return parser


def main(top_block_cls=ascii_sink, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()
    if gr.enable_realtime_scheduling() != gr.RT_OK:
        print "Error: failed to enable real-time scheduling."

    from distutils.version import StrictVersion
    if StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(nfft=options.nfft, sr=options.sr)
    tb.start()
    tb.show()

    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()


if __name__ == '__main__':
    main()
