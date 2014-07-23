#!/usr/bin/env python
##################################################
# NC-OFDM w/ cognitive capabilities
# Coded by Germano
##################################################

import os, math, sys, time
from gnuradio import uhd, gr, blocks
from grc_gnuradio import blks2 as grc_blks2
from ofdm_cr_tools import unmake_sync_packet, unmake_packet

from benchmarks import benchmark
from subprocess import call
from gnuradio.wxgui import stdgui2

'''
Daughter board TX gain range: (-20, 31, 0.1)
Daughter board RX gain range: (0, 51.5, 0.5)
Daughter board TX available antennas: ('TX/RX', 'CAL')
Daughter board RX available antennas: ('TX/RX', 'RX2', 'CAL')
Daughter board freq range: (4.875e+07, 2.22e+09, 0.0149012)
Daughter board RF filter: 40000000.0
'''

'''
A-from transmiter OS to SLAVE OS
B-from transmiter SENSE to SLAVE SENSE
C-from SLAVE OS to transmiter OS
D-from SLAVE SENSE to transmiter SENSE
'''

######### SYNC RECEIVE CALLBACK #########
def sync_rx_callback(payload):
	output, tpe, nr = unmake_sync_packet(payload)
	if tpe == 'B':
		print 'descarded own packet'
	if tpe == 'D':
		print 'received a sync packet'
		print 'sync is now ok'
		mac.sync_nOK = False
#########################################

class throttled_sink(gr.hier_block2):
	def __init__(self, samp_rate):
		gr.hier_block2.__init__(self, "throttled_sink",  gr.io_signature(1, 1, gr.sizeof_gr_complex), gr.io_signature(0, 0, 0))

		self.throttle = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate)
		self.sink = grc_blks2.tcp_sink(itemsize=gr.sizeof_gr_complex*1, addr="127.0.0.1", port=8888, server=True,) #OK

		self.connect(self, self.throttle, self.sink)

class throttled_source(gr.hier_block2):
	def __init__(self, samp_rate):
		gr.hier_block2.__init__(self, "throttled_source", gr.io_signature(0, 0, 0), gr.io_signature(1, 1, gr.sizeof_gr_complex))

		self.throttle = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate)
		self.source = blocks.udp_source(gr.sizeof_gr_complex*1, "127.0.0.1", 9999, 1472, True) #OK

		self.connect(self.source, self.throttle, self)

#In-flowgraph CRC?
w_crc = 0
# 0 - MAC layer adds CRC
# 1 - flowgraph adds CRC

if __name__ == '__main__':

	r = gr.enable_realtime_scheduling()
	if r != gr.RT_OK:
		print "Warning: failed to enable realtime scheduling" 

	#USRP settings
	address0 = "serial=E6R15U5B1"
	address1 = "serial=E7R15U0B1"
	address = address0

	tx_gain = 15 #frange(-20, 31, 0.1)
	rx_gain = 20 #frange(0, 51.5, 0.5)
	sync_clipping_factor = 0.12
	ofdm_clipping_factor = 0.2
	hardware_type = 'usrp'
	if len(sys.argv) > 1:
		hardware_type = sys.argv[1]

	if hardware_type != 'usrp':
		if hardware_type != 'net':
			print 'hardware source missing / error: usrp / net'
			sys.exit(0)

	n_test_packets = 50

	#OFDM transmitter initial settings
	ofdm_fc = 158e6 #87.6e6
	ofdm_samp_rate = 1000000
	ofdm_fft_len = 128 #64 128 1024 try not to use more than 1024
	#fft128+qam16->1596	fft128+qpsk->796	fft128+bpsk->396
	#fft64+qam16->1532	fft64+qpsk->764		fft64+bpsk->386
	ofdm_packet_len = 512 #500 
	payload_mod = 'qpsk'  # bpsk qpsk qam16
	ofdm_dc_offset = ofdm_samp_rate/2
	lobe_len = int(ofdm_fft_len/16)	#side lobe bins to cancel on each side
	cp_len = ofdm_fft_len/4
	roll_off = 0
	#frequency - fft bin ratio
	Fr = float(ofdm_samp_rate)/float(ofdm_fft_len)
	canc_band = 50e3 #band to cancel
	canc_bins = math.ceil(canc_band/Fr) #bins to cancel
	ofdm_settings  = {'ofdm_fc':ofdm_fc, 'ofdm_samp_rate':ofdm_samp_rate, 'ofdm_fft_len':ofdm_fft_len,
	 'ofdm_packet_len':ofdm_packet_len, 'payload_mod':payload_mod, 'ofdm_dc_offset':ofdm_dc_offset, 'lobe_len':lobe_len,
	  'cp_len':cp_len, 'roll_off':roll_off, 'canc_bins':canc_bins}

	data_to_load = ofdm_settings['ofdm_packet_len'] - 100

	call(['sudo', 'fuser', '-k', '9999/udp'])
	call(['sudo', 'fuser', '-k', '8888/tcp'])
	call(['sudo', 'fuser', '-k', '9999/tcp'])
	call(['sudo', 'fuser', '-k', '7777/tcp'])

	print 'shell commands ok'

	#spectrum sensor settings
	ofdm_band_start = ofdm_fc - ofdm_samp_rate / 2
	ofdm_band_finish = ofdm_fc + ofdm_samp_rate / 2
	channel_rate = 100000
	srch_bw = channel_rate / 2
	n_fft = 2048
	method = 'welch' # fft or welch
	time_sense = 0.01
	period_sense = 20
	sensing_settings = {'ofdm_band_start':ofdm_band_start, 'ofdm_band_finish':ofdm_band_finish, 'channel_rate':channel_rate,
	 'srch_bw':srch_bw, 'n_fft':n_fft, 'method':method , 'ed_threshold':0, 'time_sense':time_sense, 'period_sense':period_sense}

	if hardware_type == 'usrp':
		try:
			rf_source_RX = uhd.usrp_source(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=range(1),),)
			rf_source_RX.set_gain(rx_gain, 0)
			rf_sink_TX = uhd.usrp_sink(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=range(1),),)
			rf_sink_TX.set_gain(tx_gain, 0)
			rf_sink_TX.set_antenna("TX/RX", 0)
			print 'hardware ok...'
		except:
			print 'hardware Nok. Exiting...'
			sys.exit(0)

	if hardware_type == 'net':
		print 'waiting for a conenction...'
		rf_sink = throttled_sink(1000000)
		time.sleep(1)
		rf_source = throttled_source(1000000)
		print 'hardware ready...'

	print 'hardware ok...'
	print 'creating cs mac...'
	debug_mac = True
	agent = 'MASTER'

	mac = benchmark(agent, n_test_packets, hardware_type, ofdm_clipping_factor,
	 sensing_settings, ofdm_settings, rf_source, rf_sink, sync_rx_callback, None, w_crc)

	print 'starting...'

	mac.transmit_bench()    # don't expect this to return...

	print 'the end...'



