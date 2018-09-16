#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: GPL-3.0
#
##################################################
# GNU Radio Python Flow Graph
# Title: Remote Monitor
# Generated: Sun Sep 16 16:25:19 2018
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
from gnuradio.qtgui import Range, RangeWidget
from optparse import OptionParser
import ofdm_tools
import sys
import xmlrpclib
from gnuradio import qtgui


class remote_monitor(gr.top_block, Qt.QWidget):

    def __init__(self, server_address="127.0.0.1", udp_port=8888):
        gr.top_block.__init__(self, "Remote Monitor")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Remote Monitor")
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

        self.settings = Qt.QSettings("GNU Radio", "remote_monitor")
        self.restoreGeometry(self.settings.value("geometry").toByteArray())


        ##################################################
        # Parameters
        ##################################################
        self.server_address = server_address
        self.udp_port = udp_port

        ##################################################
        # Variables
        ##################################################
        self.tune_freq = tune_freq = 100e6
        self.samp_rate = samp_rate = 1800000
        self.rf_gain = rf_gain = 5
        self.reset_max = reset_max = False
        self.rate = rate = 1
        self.precision = precision = True
        self.max_mtu = max_mtu = 10000
        self.av = av = 0.8

        ##################################################
        # Blocks
        ##################################################
        self._tune_freq_range = Range(0, 2000e6, 500, 100e6, 200)
        self._tune_freq_win = RangeWidget(self._tune_freq_range, self.set_tune_freq, 'Tuning Frequency', "counter_slider", float)
        self.top_grid_layout.addWidget(self._tune_freq_win, 1, 0, 1, 2)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._samp_rate_tool_bar = Qt.QToolBar(self)
        self._samp_rate_tool_bar.addWidget(Qt.QLabel("samp_rate"+": "))
        self._samp_rate_line_edit = Qt.QLineEdit(str(self.samp_rate))
        self._samp_rate_tool_bar.addWidget(self._samp_rate_line_edit)
        self._samp_rate_line_edit.returnPressed.connect(
        	lambda: self.set_samp_rate(int(str(self._samp_rate_line_edit.text().toAscii()))))
        self.top_grid_layout.addWidget(self._samp_rate_tool_bar, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        _precision_check_box = Qt.QCheckBox('32bit FFT (or 16b)')
        self._precision_choices = {True: True, False: False}
        self._precision_choices_inv = dict((v,k) for k,v in self._precision_choices.iteritems())
        self._precision_callback = lambda i: Qt.QMetaObject.invokeMethod(_precision_check_box, "setChecked", Qt.Q_ARG("bool", self._precision_choices_inv[i]))
        self._precision_callback(self.precision)
        _precision_check_box.stateChanged.connect(lambda i: self.set_precision(self._precision_choices[bool(i)]))
        self.top_grid_layout.addWidget(_precision_check_box, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.zeromq_sub_msg_source_0 = zeromq.sub_msg_source('tcp://127.0.0.1:5005', 100)
        self.xmlrpc_client5 = xmlrpclib.Server('http://127.0.0.1:7658')
        self.xmlrpc_client4_0_1 = xmlrpclib.Server('http://127.0.0.1:7658')
        self.xmlrpc_client4 = xmlrpclib.Server('http://127.0.0.1:7658')
        self.xmlrpc_client3 = xmlrpclib.Server('http://127.0.0.1:7658')
        self.xmlrpc_client2 = xmlrpclib.Server('http://127.0.0.1:7658')
        self.xmlrpc_client0_0 = xmlrpclib.Server('http://127.0.0.1:7658')
        self._rf_gain_range = Range(0, 50, 1, 5, 200)
        self._rf_gain_win = RangeWidget(self._rf_gain_range, self.set_rf_gain, "rf_gain", "counter_slider", float)
        self.top_grid_layout.addWidget(self._rf_gain_win, 2, 0, 1, 2)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        _reset_max_check_box = Qt.QCheckBox('Max Reset')
        self._reset_max_choices = {True: True, False: False}
        self._reset_max_choices_inv = dict((v,k) for k,v in self._reset_max_choices.iteritems())
        self._reset_max_callback = lambda i: Qt.QMetaObject.invokeMethod(_reset_max_check_box, "setChecked", Qt.Q_ARG("bool", self._reset_max_choices_inv[i]))
        self._reset_max_callback(self.reset_max)
        _reset_max_check_box.stateChanged.connect(lambda i: self.set_reset_max(self._reset_max_choices[bool(i)]))
        self.top_grid_layout.addWidget(_reset_max_check_box, 1, 3, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._rate_range = Range(1, 50, 1, 1, 200)
        self._rate_win = RangeWidget(self._rate_range, self.set_rate, "rate", "counter_slider", int)
        self.top_grid_layout.addWidget(self._rate_win, 0, 1, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.ofdm_tools_remote_client_qt_0_0 = ofdm_tools.remote_client_qt(
        tune_freq=tune_freq,
        sample_rate=samp_rate,
        show_axes='str(axes)',
        precision=precision,
        hold_max=False,
        label='Complex PSD Plot')
        self._ofdm_tools_remote_client_qt_0_0_win = self.ofdm_tools_remote_client_qt_0_0;
        self.top_grid_layout.addWidget(self._ofdm_tools_remote_client_qt_0_0_win, 3, 0, 1, 4)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)


        self._av_range = Range(0, 1, 0.001, 0.8, 200)
        self._av_win = RangeWidget(self._av_range, self.set_av, "av", "counter_slider", float)
        self.top_grid_layout.addWidget(self._av_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)



        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.zeromq_sub_msg_source_0, 'out'), (self.ofdm_tools_remote_client_qt_0_0, 'pdus'))

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "remote_monitor")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def get_server_address(self):
        return self.server_address

    def set_server_address(self, server_address):
        self.server_address = server_address

    def get_udp_port(self):
        return self.udp_port

    def set_udp_port(self, udp_port):
        self.udp_port = udp_port

    def get_tune_freq(self):
        return self.tune_freq

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq
        self.xmlrpc_client3.set_tune_freq(self.tune_freq)
        self.ofdm_tools_remote_client_qt_0_0.set_tune_freq(self.tune_freq)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        Qt.QMetaObject.invokeMethod(self._samp_rate_line_edit, "setText", Qt.Q_ARG("QString", str(self.samp_rate)))
        self.xmlrpc_client0_0.set_samp_rate(self.samp_rate)
        self.ofdm_tools_remote_client_qt_0_0.set_sample_rate(self.samp_rate)

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.xmlrpc_client2.set_rf_gain(self.rf_gain)

    def get_reset_max(self):
        return self.reset_max

    def set_reset_max(self, reset_max):
        self.reset_max = reset_max
        self._reset_max_callback(self.reset_max)
        self.ofdm_tools_remote_client_qt_0_0.set_reset_max(self.reset_max)

    def get_rate(self):
        return self.rate

    def set_rate(self, rate):
        self.rate = rate
        self.xmlrpc_client5.set_rate(self.rate)

    def get_precision(self):
        return self.precision

    def set_precision(self, precision):
        self.precision = precision
        self._precision_callback(self.precision)
        self.xmlrpc_client4_0_1.set_precision(self.precision)
        self.ofdm_tools_remote_client_qt_0_0.set_precision(self.precision)

    def get_max_mtu(self):
        return self.max_mtu

    def set_max_mtu(self, max_mtu):
        self.max_mtu = max_mtu

    def get_av(self):
        return self.av

    def set_av(self, av):
        self.av = av
        self.xmlrpc_client4.set_av(self.av)


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "-a", "--server-address", dest="server_address", type="string", default="127.0.0.1",
        help="Set server_address [default=%default]")
    parser.add_option(
        "-u", "--udp-port", dest="udp_port", type="intx", default=8888,
        help="Set udp_port [default=%default]")
    return parser


def main(top_block_cls=remote_monitor, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()
    if gr.enable_realtime_scheduling() != gr.RT_OK:
        print "Error: failed to enable real-time scheduling."

    from distutils.version import StrictVersion
    if StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(server_address=options.server_address, udp_port=options.udp_port)
    tb.start()
    tb.show()

    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()


if __name__ == '__main__':
    main()
