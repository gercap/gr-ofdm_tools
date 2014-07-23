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

'''
A-from transmiter OS to receiver OS
B-from transmiter SENSE to receiver SENSE
C-from receiver OS to transmiter OS
D-from receiver SENSE to transmiter SENSE
'''

_ofdm_n_rcvd = 0
_ofdm_n_rcvd_ok = 0
_sync_bench_count = 0

day_hour = time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S")
f_name = '../logs/benchmarks/'+'benchmark_rx_Log'+'-'+ day_hour
f = open(f_name,'w')

######### SYNC RECEIVE CALLBACK #########
def sync_rx_callback(payload):
	output, tpe, nr = unmake_sync_packet(payload)
	if tpe == 'B':
		print 'received a sync packet ' + str(nr)
		f.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'Rxd_sync_packet_nr:' + str(nr) + '\n')
		mac.add_slave_sync_count(nr)
		mac.slave_raw_sync_data[nr] = output
		mac.state = 'sync'
		if all(mac.slave_sync_count):
			mac.new_slave_sync_count()
			mac.sync_nOK = False
			f.write('Time-'+ time.strftime("%H%M%S") + '-Evnt-'+ 'got_sync\n')
	print 'current sync status:', mac.slave_sync_count
	f.write('Time-'+ time.strftime("%H%M%S") + '-Evnt-'+ 'sync_status:' + str(mac.slave_sync_count) + '\n')
##########################################

######### SYNC BENCHMARK RECEIVE CALLBACK #########
def sync_bench_rx_callback(payload):
	output, tpe, nr = unmake_sync_packet(payload)
	print 'RxD sync packet type: ', tpe,' nr: ', nr 
##########################################

######### OFDM BENCHMARK RECEIVE CALLBACK ##
def ofdm_bench_rx_callback(payload):
	global _ofdm_n_rcvd, _ofdm_n_rcvd_ok
	_ofdm_n_rcvd += 1
	pld, tpe, ok = unmake_packet(payload, w_crc)
	if ok:
		_ofdm_n_rcvd_ok += 1
		print 'RxD OK ofdm packet number:', pld[0:4], ' type:', tpe, ' total rcvd:', _ofdm_n_rcvd, ' total ok:', _ofdm_n_rcvd_ok
		f.write('Time-' + time.strftime("%H%M%S") + '-Evnt-' + 'RxD_OK_ofdm_pkt_nr:' + str(pld[0:4]) + '-type:' + tpe + '-total_rcvd:' + str(_ofdm_n_rcvd) + '-total_ok:' + str(_ofdm_n_rcvd_ok) + '\n')
		if tpe == 'B':
			mac.state = 'exit'
	else:
		print 'RxD NOK ofdm packet, total rcvd ', str(_ofdm_n_rcvd), ' total ok ', str(_ofdm_n_rcvd_ok)
		f.write('Time-' + time.strftime("%H%M%S") + '-Evnt-' + 'RxD_NOK_ofdm_pkt-total_rcvd:' + str(_ofdm_n_rcvd) + '-total_ok_' + str(_ofdm_n_rcvd_ok) + '\n')
	print 'level:', 10*math.log10(mac.cs_probe_ofdm.level()+.1e-12)
##########################################

class throttled_sink(gr.hier_block2):
	def __init__(self, samp_rate):
		gr.hier_block2.__init__(self, "throttled_sink",  gr.io_signature(1, 1, gr.sizeof_gr_complex), gr.io_signature(0, 0, 0))

		self.throttle = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate)
		self.sink = blocks.udp_sink(gr.sizeof_gr_complex*1, "127.0.0.1", 9999, 1472, True) #OK

		self.connect(self, self.throttle, self.sink)

class throttled_source(gr.hier_block2):
	def __init__(self, samp_rate):
		gr.hier_block2.__init__(self, "throttled_source", gr.io_signature(0, 0, 0), gr.io_signature(1, 1, gr.sizeof_gr_complex))

		self.throttle = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate)
		self.source = grc_blks2.tcp_source(itemsize=gr.sizeof_gr_complex*1, addr="127.0.0.1", port=8888, server=False,) #OK

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
	address = address1
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

	n_test_packets = None

	'''
	call(['sudo', 'fuser', '-k', '9999/udp'])
	call(['sudo', 'fuser', '-k', '8888/tcp'])
	call(['sudo', 'fuser', '-k', '7777/tcp'])
	print 'shell commands ok'
	'''

	if hardware_type == 'usrp':
		try:
			rf_source_RX = uhd.usrp_source(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=range(1),),)
			rf_source_RX.set_gain(rx_gain, 0)

			rf_sink_TX = uhd.usrp_sink(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=range(1),),)
			rf_sink_TX.set_gain(tx_gain, 0)
			rf_sink_TX.set_antenna("TX/RX", 0)
			print 'hardware ok...'
			f.write('Time-'+time.strftime("%H%M%S")+ '-Evnt-'+ 'receiver_hw_ok\n')
		except:
			print 'hardware Nok. Exiting...'
			f.write('Time-'+time.strftime("%H%M%S")+ '-Evnt-'+ 'receiver_hw_Nok\n')
			sys.exit(0)

	if hardware_type == 'net':
		rf_source = throttled_source(1000000)
		rf_sink = throttled_sink(1000000)

	#spectrum sensor settings
	channel_rate = 0.1*1e6
	srch_bw = channel_rate / 2
	n_fft = 2048
	method = 'welch' # fft or welch
	time_sense = 0.01
	period_sense = 20
	sensing_settings = {'channel_rate':channel_rate, 'srch_bw':srch_bw, 'n_fft':n_fft, 'method':method , 'ed_threshold':0, 'time_sense':time_sense, 'period_sense':period_sense}

	print 'creating cs mac...'
	debug_mac = True
	agent = 'SLAVE'
	ofdm_settings = {}

	mac = benchmark(agent, n_test_packets, hardware_type, ofdm_clipping_factor,
	 sensing_settings, ofdm_settings, rf_source, rf_sink, sync_rx_callback, ofdm_bench_rx_callback, w_crc)

	f.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'starting_receiver\n')

	print 'starting...'
	mac.receive_bench()
	print 'the end...'



