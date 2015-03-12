#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Ascii Sink
# Generated: Thu Mar 12 21:43:55 2015
##################################################

from PyQt4 import Qt
from PyQt4.QtCore import QObject, pyqtSlot
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import PyQt4.Qwt5 as Qwt
import ofdm_tools
import osmosdr
import sys
import time

from distutils.version import StrictVersion
class ascii_sink(gr.top_block, Qt.QWidget):

    def __init__(self, nfft=1024, samp_rate=2e6):
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
        self.samp_rate = samp_rate

        ##################################################
        # Variables
        ##################################################
        self.tune_freq = tune_freq = 97e6
        self.rf_gain = rf_gain = 5
        self.ln = ln = 30
        self.if_gain = if_gain = 10
        self.ht = ht = 30
        self.bb_gain = bb_gain = 10
        self.av = av = 0.8

        ##################################################
        # Blocks
        ##################################################
        self._tune_freq_layout = Qt.QVBoxLayout()
        self._tune_freq_tool_bar = Qt.QToolBar(self)
        self._tune_freq_layout.addWidget(self._tune_freq_tool_bar)
        self._tune_freq_tool_bar.addWidget(Qt.QLabel("tune_freq"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._tune_freq_counter = qwt_counter_pyslot()
        self._tune_freq_counter.setRange(28e6, 1800e6, 5000)
        self._tune_freq_counter.setNumButtons(2)
        self._tune_freq_counter.setValue(self.tune_freq)
        self._tune_freq_tool_bar.addWidget(self._tune_freq_counter)
        self._tune_freq_counter.valueChanged.connect(self.set_tune_freq)
        self._tune_freq_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._tune_freq_slider.setRange(28e6, 1800e6, 5000)
        self._tune_freq_slider.setValue(self.tune_freq)
        self._tune_freq_slider.setMinimumWidth(200)
        self._tune_freq_slider.valueChanged.connect(self.set_tune_freq)
        self._tune_freq_layout.addWidget(self._tune_freq_slider)
        self.top_layout.addLayout(self._tune_freq_layout)
        self._rf_gain_layout = Qt.QVBoxLayout()
        self._rf_gain_tool_bar = Qt.QToolBar(self)
        self._rf_gain_layout.addWidget(self._rf_gain_tool_bar)
        self._rf_gain_tool_bar.addWidget(Qt.QLabel("rf_gain"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._rf_gain_counter = qwt_counter_pyslot()
        self._rf_gain_counter.setRange(0, 50, 1)
        self._rf_gain_counter.setNumButtons(2)
        self._rf_gain_counter.setValue(self.rf_gain)
        self._rf_gain_tool_bar.addWidget(self._rf_gain_counter)
        self._rf_gain_counter.valueChanged.connect(self.set_rf_gain)
        self._rf_gain_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._rf_gain_slider.setRange(0, 50, 1)
        self._rf_gain_slider.setValue(self.rf_gain)
        self._rf_gain_slider.setMinimumWidth(200)
        self._rf_gain_slider.valueChanged.connect(self.set_rf_gain)
        self._rf_gain_layout.addWidget(self._rf_gain_slider)
        self.top_grid_layout.addLayout(self._rf_gain_layout, 1,0,1,1)
        self._ln_layout = Qt.QVBoxLayout()
        self._ln_tool_bar = Qt.QToolBar(self)
        self._ln_layout.addWidget(self._ln_tool_bar)
        self._ln_tool_bar.addWidget(Qt.QLabel("ln"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._ln_counter = qwt_counter_pyslot()
        self._ln_counter.setRange(0, 200, 1)
        self._ln_counter.setNumButtons(2)
        self._ln_counter.setValue(self.ln)
        self._ln_tool_bar.addWidget(self._ln_counter)
        self._ln_counter.valueChanged.connect(self.set_ln)
        self._ln_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._ln_slider.setRange(0, 200, 1)
        self._ln_slider.setValue(self.ln)
        self._ln_slider.setMinimumWidth(200)
        self._ln_slider.valueChanged.connect(self.set_ln)
        self._ln_layout.addWidget(self._ln_slider)
        self.top_grid_layout.addLayout(self._ln_layout, 0,0,1,1)
        self._if_gain_layout = Qt.QVBoxLayout()
        self._if_gain_tool_bar = Qt.QToolBar(self)
        self._if_gain_layout.addWidget(self._if_gain_tool_bar)
        self._if_gain_tool_bar.addWidget(Qt.QLabel("if_gain"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._if_gain_counter = qwt_counter_pyslot()
        self._if_gain_counter.setRange(0, 50, 1)
        self._if_gain_counter.setNumButtons(2)
        self._if_gain_counter.setValue(self.if_gain)
        self._if_gain_tool_bar.addWidget(self._if_gain_counter)
        self._if_gain_counter.valueChanged.connect(self.set_if_gain)
        self._if_gain_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._if_gain_slider.setRange(0, 50, 1)
        self._if_gain_slider.setValue(self.if_gain)
        self._if_gain_slider.setMinimumWidth(200)
        self._if_gain_slider.valueChanged.connect(self.set_if_gain)
        self._if_gain_layout.addWidget(self._if_gain_slider)
        self.top_grid_layout.addLayout(self._if_gain_layout, 1,1,1,1)
        self._ht_layout = Qt.QVBoxLayout()
        self._ht_tool_bar = Qt.QToolBar(self)
        self._ht_layout.addWidget(self._ht_tool_bar)
        self._ht_tool_bar.addWidget(Qt.QLabel("ht"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._ht_counter = qwt_counter_pyslot()
        self._ht_counter.setRange(0, 200, 1)
        self._ht_counter.setNumButtons(2)
        self._ht_counter.setValue(self.ht)
        self._ht_tool_bar.addWidget(self._ht_counter)
        self._ht_counter.valueChanged.connect(self.set_ht)
        self._ht_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._ht_slider.setRange(0, 200, 1)
        self._ht_slider.setValue(self.ht)
        self._ht_slider.setMinimumWidth(200)
        self._ht_slider.valueChanged.connect(self.set_ht)
        self._ht_layout.addWidget(self._ht_slider)
        self.top_grid_layout.addLayout(self._ht_layout, 0,1,1,1)
        self._bb_gain_layout = Qt.QVBoxLayout()
        self._bb_gain_tool_bar = Qt.QToolBar(self)
        self._bb_gain_layout.addWidget(self._bb_gain_tool_bar)
        self._bb_gain_tool_bar.addWidget(Qt.QLabel("bb_gain"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._bb_gain_counter = qwt_counter_pyslot()
        self._bb_gain_counter.setRange(0, 50, 1)
        self._bb_gain_counter.setNumButtons(2)
        self._bb_gain_counter.setValue(self.bb_gain)
        self._bb_gain_tool_bar.addWidget(self._bb_gain_counter)
        self._bb_gain_counter.valueChanged.connect(self.set_bb_gain)
        self._bb_gain_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._bb_gain_slider.setRange(0, 50, 1)
        self._bb_gain_slider.setValue(self.bb_gain)
        self._bb_gain_slider.setMinimumWidth(200)
        self._bb_gain_slider.valueChanged.connect(self.set_bb_gain)
        self._bb_gain_layout.addWidget(self._bb_gain_slider)
        self.top_grid_layout.addLayout(self._bb_gain_layout, 1,2,1,1)
        self._av_layout = Qt.QVBoxLayout()
        self._av_tool_bar = Qt.QToolBar(self)
        self._av_layout.addWidget(self._av_tool_bar)
        self._av_tool_bar.addWidget(Qt.QLabel("av"+": "))
        class qwt_counter_pyslot(Qwt.QwtCounter):
            def __init__(self, parent=None):
                Qwt.QwtCounter.__init__(self, parent)
            @pyqtSlot('double')
            def setValue(self, value):
                super(Qwt.QwtCounter, self).setValue(value)
        self._av_counter = qwt_counter_pyslot()
        self._av_counter.setRange(0, 1, 0.001)
        self._av_counter.setNumButtons(2)
        self._av_counter.setValue(self.av)
        self._av_tool_bar.addWidget(self._av_counter)
        self._av_counter.valueChanged.connect(self.set_av)
        self._av_slider = Qwt.QwtSlider(None, Qt.Qt.Horizontal, Qwt.QwtSlider.BottomScale, Qwt.QwtSlider.BgSlot)
        self._av_slider.setRange(0, 1, 0.001)
        self._av_slider.setValue(self.av)
        self._av_slider.setMinimumWidth(200)
        self._av_slider.valueChanged.connect(self.set_av)
        self._av_layout.addWidget(self._av_slider)
        self.top_layout.addLayout(self._av_layout)
        self.osmosdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + "" )
        self.osmosdr_source_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0.set_center_freq(tune_freq, 0)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(2, 0)
        self.osmosdr_source_0.set_gain_mode(False, 0)
        self.osmosdr_source_0.set_gain(rf_gain, 0)
        self.osmosdr_source_0.set_if_gain(if_gain, 0)
        self.osmosdr_source_0.set_bb_gain(bb_gain, 0)
        self.osmosdr_source_0.set_antenna("", 0)
        self.osmosdr_source_0.set_bandwidth(0, 0)
          
        self.ofdm_tools_ascii_plot_0 = ofdm_tools.ascii_plot(
          fft_len=int(nfft),
          sample_rate=int(samp_rate), 
          tune_freq=tune_freq, 
          average=av, 
          rate=5,
          length=ln,
          height=ht,
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

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.ofdm_tools_ascii_plot_0.set_sample_rate(int(self.samp_rate))
        self.osmosdr_source_0.set_sample_rate(self.samp_rate)

    def get_tune_freq(self):
        return self.tune_freq

    def set_tune_freq(self, tune_freq):
        self.tune_freq = tune_freq
        Qt.QMetaObject.invokeMethod(self._tune_freq_counter, "setValue", Qt.Q_ARG("double", self.tune_freq))
        Qt.QMetaObject.invokeMethod(self._tune_freq_slider, "setValue", Qt.Q_ARG("double", self.tune_freq))
        self.ofdm_tools_ascii_plot_0.set_tune_freq(self.tune_freq)
        self.osmosdr_source_0.set_center_freq(self.tune_freq, 0)

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        Qt.QMetaObject.invokeMethod(self._rf_gain_counter, "setValue", Qt.Q_ARG("double", self.rf_gain))
        Qt.QMetaObject.invokeMethod(self._rf_gain_slider, "setValue", Qt.Q_ARG("double", self.rf_gain))
        self.osmosdr_source_0.set_gain(self.rf_gain, 0)

    def get_ln(self):
        return self.ln

    def set_ln(self, ln):
        self.ln = ln
        Qt.QMetaObject.invokeMethod(self._ln_counter, "setValue", Qt.Q_ARG("double", self.ln))
        Qt.QMetaObject.invokeMethod(self._ln_slider, "setValue", Qt.Q_ARG("double", self.ln))
        self.ofdm_tools_ascii_plot_0.set_length(self.ln)

    def get_if_gain(self):
        return self.if_gain

    def set_if_gain(self, if_gain):
        self.if_gain = if_gain
        Qt.QMetaObject.invokeMethod(self._if_gain_counter, "setValue", Qt.Q_ARG("double", self.if_gain))
        Qt.QMetaObject.invokeMethod(self._if_gain_slider, "setValue", Qt.Q_ARG("double", self.if_gain))
        self.osmosdr_source_0.set_if_gain(self.if_gain, 0)

    def get_ht(self):
        return self.ht

    def set_ht(self, ht):
        self.ht = ht
        Qt.QMetaObject.invokeMethod(self._ht_counter, "setValue", Qt.Q_ARG("double", self.ht))
        Qt.QMetaObject.invokeMethod(self._ht_slider, "setValue", Qt.Q_ARG("double", self.ht))
        self.ofdm_tools_ascii_plot_0.set_height(self.ht)

    def get_bb_gain(self):
        return self.bb_gain

    def set_bb_gain(self, bb_gain):
        self.bb_gain = bb_gain
        Qt.QMetaObject.invokeMethod(self._bb_gain_counter, "setValue", Qt.Q_ARG("double", self.bb_gain))
        Qt.QMetaObject.invokeMethod(self._bb_gain_slider, "setValue", Qt.Q_ARG("double", self.bb_gain))
        self.osmosdr_source_0.set_bb_gain(self.bb_gain, 0)

    def get_av(self):
        return self.av

    def set_av(self, av):
        self.av = av
        Qt.QMetaObject.invokeMethod(self._av_counter, "setValue", Qt.Q_ARG("double", self.av))
        Qt.QMetaObject.invokeMethod(self._av_slider, "setValue", Qt.Q_ARG("double", self.av))
        self.ofdm_tools_ascii_plot_0.set_average(self.av)

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print "Warning: failed to XInitThreads()"
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    parser.add_option("", "--nfft", dest="nfft", type="intx", default=1024,
        help="Set nfft [default=%default]")
    parser.add_option("-s", "--samp-rate", dest="samp_rate", type="eng_float", default=eng_notation.num_to_str(2e6),
        help="Set samp_rate [default=%default]")
    (options, args) = parser.parse_args()
    if gr.enable_realtime_scheduling() != gr.RT_OK:
        print "Error: failed to enable realtime scheduling."
    if(StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0")):
        Qt.QApplication.setGraphicsSystem(gr.prefs().get_string('qtgui','style','raster'))
    qapp = Qt.QApplication(sys.argv)
    tb = ascii_sink(nfft=options.nfft, samp_rate=options.samp_rate)
    tb.start()
    tb.show()
    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()
    tb = None #to clean up Qt widgets
