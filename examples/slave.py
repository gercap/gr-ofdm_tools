#!/usr/bin/env python
##################################################
# NC-OFDM w/ cognitive capabilities
# Coded by Germano
##################################################

import os, math, sys, time, baz
from gnuradio import uhd, gr, blocks
from grc_gnuradio import blks2 as grc_blks2
from ofdm_cr_tools import unmake_sync_packet
from ofdm_cr_tools import unmake_packet
from ofdm_cr_tools import open_tun_interface
from csma_cr_mac import csma_cr_mac
from subprocess import call

'''
A-from MASTER OS to SLAVE OS
B-from MASTER SENSE to SLAVE SENSE
C-from SLAVE OS to MASTER OS
D-from SLAVE SENSE to MASTER SENSE
'''

_ofdm_n_rcvd = 0
_ofdm_n_rcvd_ok = 0

day_hour = time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S")
f_name = '../logs/ofdm_comms/half_duplex/'+'slave_Log'+'-'+ day_hour
f = open(f_name,'w')

######### SYNC RECEIVE CALLBACK #########
def sync_rx_callback(payload):
	output, tpe, nr = unmake_sync_packet(payload)
	if tpe == 'B':
		print 'received a sync packet' + str(nr)
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

######### OFDM RECEIVE CALLBACK #########
def ofdm_rx_callback(payload):
	global _ofdm_n_rcvd, _ofdm_n_rcvd_ok
	_ofdm_n_rcvd += 1
	pld, tpe, ok = unmake_packet(payload, w_crc)
	if ok:
		if tpe == 'A':
			_ofdm_n_rcvd_ok += 1
			os.write(tun_fd, pld)
		elif tpe == 'B':
			_ofdm_n_rcvd_ok += 1
			print 'going to post_ofdm_pre_sync'
			mac.state = 'post_ofdm_pre_sync'
		else: _ofdm_n_rcvd -= 1 #means it receaved own packet!

	print 'Total rcvd:', _ofdm_n_rcvd, ' total OK:', _ofdm_n_rcvd_ok
	f.write('Time-' + time.strftime("%H%M%S") + '-Evnt-' + 'RxD_OK_ofdm_pkt-type:' + tpe + '-total_rcvd:' + str(_ofdm_n_rcvd) + '-total_ok:' + str(_ofdm_n_rcvd_ok) + '\n')
##########################################

# open the TUN/TAP interface
(tun_fd, tun_ifname) = open_tun_interface("/dev/net/tun")
print 'NIC for CR OFDM:', tun_ifname

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
	if len(sys.argv)>1:
		hardware_type = sys.argv[1]

	if hardware_type != 'usrp':
		if hardware_type != 'net':
			print 'hardware source missing / error: usrp / net'
			sys.exit(0)

	#data_to_load = ofdm_settings['ofdm_packet_len'] - 6
	call(['sudo', 'ifconfig', tun_ifname, '192.168.200.2'])
	#call(['sudo', 'ifconfig', tun_ifname, 'mtu', str(data_to_load)])
	call(['sudo', 'fuser', '-k', '9999/tcp'])
	print 'shell commands ok'

	if hardware_type == 'usrp':
		rf_source = uhd.usrp_source(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=range(1),),)
		rf_source.set_gain(rx_gain, 0)

		#rf_sink = uhd.usrp_sink(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc8", channels=range(1),),)
		rf_sink = uhd.usrp_sink(device_addr='', stream_args=uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=range(1),),)
		rf_sink.set_gain(tx_gain, 0)
		rf_sink.set_antenna("TX/RX", 0)
		print 'hardware ok...'

	if hardware_type == 'net':
		rf_source = throttled_source(1000000)
		rf_sink = throttled_sink(1000000)
		print 'hardware ready...'

	#spectrum sensor settings
	channel_rate = 0.1*1e6
	srch_bw = channel_rate / 2
	n_fft = 2048
	method = 'welch' # fft or welch
	time_sense = 0.01
	period_sense = 20
	sensing_settings = {'channel_rate':channel_rate, 'srch_bw':srch_bw, 'n_fft':n_fft, 'method':method , 'ed_threshold':0, 'time_sense':time_sense, 'period_sense':period_sense}

	print 'creating cs mac...'
	agent = 'SLAVE'
	ofdm_settings = {}
	mac = csma_cr_mac(hardware_type, sync_clipping_factor, ofdm_clipping_factor, tun_fd, agent,
	 sensing_settings, ofdm_settings, rf_source, rf_sink, sync_rx_callback, ofdm_rx_callback, w_crc)

	print 'starting...'
	mac.slave_main_loop()    # don't expect this to return...
	print 'the end...'



