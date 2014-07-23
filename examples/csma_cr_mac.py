from ofdm_cr_tools import *
import gnuradio.gr.gr_threading as _threading
from random import randrange
from grc_gnuradio import wxgui as grc_wxgui
from gnuradio.digital import crc
import wx
from gnuradio.wxgui import forms
import SimpleXMLRPCServer
import threading
import ofdm_tools


_rand_bad_freqs = [158e6, 157.5e6, 157.9e6, 158.1e6, 158.34e6]

# 0.9-0.95-0.1-100

#_ofdm_iir_forward_OOB = [0.7876171623403406, 5.510681051370744, 16.526767546473486, 27.540217518309245, 27.540217518309273, 16.526767546473526, 5.510681051370761, 0.787617162340344]
#_ofdm_iir_feedback_OOB = [1.0, 6.521014243736465, 18.240696138603255, 28.36968109945311, 26.494069700252503, 14.855694326793557, 4.6305176483999, 0.6188933997487145]

_ofdm_iir_forward_OOB = [0.40789374966665903, 3.2351160543115207, 11.253435139165413, 22.423991613997735, 27.99555756436666, 22.423991613997735, 11.253435139165425, 3.235116054311531, 0.40789374966666014]
_ofdm_iir_feedback_OOB = [1.0, 6.170110168740749, 16.888669609673336, 26.73762881119027, 26.75444043101795, 17.322358010203928, 7.091659316015212, 1.682084643429639, 0.17795354282083842]

_sync_iir_forward_OOB = [0.005277622700213007, 0.03443705907448985, 0.1214101788557494, 0.29179662246081545, 0.52428014905364, 0.7350677973792328, 0.8210395030022875, 0.7350677973792348, 0.5242801490536404, 0.291796622460816, 0.1214101788557501, 0.03443705907448997, 0.005277622700213012]
_sync_iir_feedback_OOB = [1.0, -1.0455317889337852, 3.9201525346250072, -3.9114761684448958, 6.54266144224035, -5.737287389902878, 5.820328302284336, -4.134700802700442, 2.7949972248757664, -1.4584448495689168, 0.6358650797085171, -0.19847981428665007, 0.04200458351675313]

_probe_thresh = -44 #-50

_ofdm_rx_ant = 'TX/RX' # TX/RX / RX2
_sense_rx_ant = 'TX/RX' # TX/RX / RX2
_sync_rx_ant = 'TX/RX' # TX/RX / RX2

_record_samp_stream = True

class csma_cr_mac(object):
	"""
	by Germano March 14
	"""
	def __init__(self, hardware_type, sync_clipping_factor, ofdm_clipping_factor, tun_fd, agent,
	 sensing_settings, ofdm_settings, rf_source, rf_sink, sync_rx_callback, ofdm_rx_callback, w_crc):
#ofdm_settings  = {'ofdm_fc':ofdm_fc, 'ofdm_samp_rate':ofdm_samp_rate, 'ofdm_fft_len':ofdm_fft_len,'ofdm_packet_len':ofdm_packet_len, 'payload_mod':payload_mod, 'ofdm_dc_offset':ofdm_dc_offset, 'lobe_len':lobe_len,'cp_len':cp_len, 'roll_off':roll_off, 'canc_bins':canc_bins}
#sensing_settings = {'ofdm_band_start':ofdm_band_start, 'ofdm_band_finish':ofdm_band_finish, 'channel_rate':channel_rate,'srch_bw':srch_bw, 'n_fft':n_fft, 'method':method , 'ed_threshold':ed_threshold, 'time_sense':time_sense, 'period_sense':period_sense}
#sync_settings = {'sync_samp_rate':sync_samp_rate, 'sync_fc':sync_fc, 'sync_packet_len':sync_packet_len, 'sync_dc_offset':sync_dc_offset}

		'''
		self.tx_gain = 10
		self.rx_gain = 15

		if agent == 'MASTER':
			self.xmlrpc_server = SimpleXMLRPCServer.SimpleXMLRPCServer(("localhost", 7777), allow_none=True)
			self.xmlrpc_server.register_instance(self)
			threading.Thread(target=self.xmlrpc_server.serve_forever).start()

		if agent == 'SLAVE':
			self.xmlrpc_server = SimpleXMLRPCServer.SimpleXMLRPCServer(("193.136.223.117", 7777), allow_none=True)
			self.xmlrpc_server.register_instance(self)
			threading.Thread(target=self.xmlrpc_server.serve_forever).start()
		'''

		self.log_file = open('../logs/ofdm_comms/half_duplex/'+ agent +'_mac_Log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S"),'w')

		self.hardware_type = hardware_type #what type of hardware is being used for TX/RX
		self.tun_fd = tun_fd	#descriptor for TUN/TAP interface

		self.sensing_settings = sensing_settings #spectrum sensing settings
		self.ofdm_settings = ofdm_settings #ofdm mod/demod settings
		self.sync_settings = {'sync_samp_rate':125000, 'sync_fc':155e6, 'sync_packet_len':400, 
		'sync_dc_offset':(125000/2)} #synchronizer mod/demod settings

		self.tb = gr.top_block() #THE gnuradio top block for sync and ofdm'ing
		self.rf_source = rf_source # rf receiver source
		self.rf_sink = rf_sink # rf transmitter sink
		self.payload_src = None
		self.payload_snk = None

		self.w_crc = w_crc #Use in flowgraph CRC

		self.ofdm_clipping_factor = ofdm_clipping_factor #clipping factor for ofdm
		self.sync_clipping_factor = sync_clipping_factor #clipping factor for sync
		self.data_to_load = None

		if agent == 'MASTER':
			self.sync_data = {'occupied_carriers':None, 'pilot_carriers':None, 'pilot_symbols':None,
			 'ofdm_fc':ofdm_settings['ofdm_fc'], 'ofdm_samp_rate':ofdm_settings['ofdm_samp_rate'],
			  'payload_mod':ofdm_settings['payload_mod'], 'ofdm_packet_len':ofdm_settings['ofdm_packet_len'],
			   'sync_word1':None, 'sync_word2':None}

		if agent == 'SLAVE':
			self.sync_data = {'occupied_carriers':None, 'pilot_carriers':None, 'pilot_symbols':None,
			 'ofdm_fc':None, 'ofdm_samp_rate':None,'payload_mod':None, 'ofdm_packet_len':None,
			   'sync_word1':None, 'sync_word2':None}

		self.sync_nOK = True # False Flag for sync process nOK=True --> not synced 
		self.sink_len = 10 #number of packets used to send sync data
		self.slave_raw_sync_data = [False] * self.sink_len #data container for received sync data
		self.slave_sync_count = [False] * self.sink_len #structure to control sync packets - slave
		self.master_sync_ack_count = [False] * self.sink_len #structure to control sync acks - master

		if self.hardware_type == 'usrp': self.probe_level = _probe_thresh #CSMA threshold
		else: self.probe_level = -10
		self.cs_probe_ofdm = analog.probe_avg_mag_sqrd_c(self.probe_level, 0.01) #CSMA probe
		self.cs_probe_sync = analog.probe_avg_mag_sqrd_c(self.probe_level, 0.01) #CSMA probe

		self.agent = agent # MASTER / SLAVE

		self.state = None #state machine for ofdm/sync control
		# ofdm - ofdm tx/rx
		# sync - sync tx/rx
		# post_sync_pre_ofdm - turn off sync fg turn on ofdm fg
		# post_ofdm_pre_sync - turn off ofdm fg turn on sync fg
		# idle - mute OFDM tx

		self.sync_rx_callback = sync_rx_callback #function to execute in case a sync packet is received --> master != slave
		self.ofdm_rx_callback = ofdm_rx_callback #function to execute in case an ofdm packet is received --> master != slave

		if self.agent == 'MASTER' and _record_samp_stream:  #logging files... multiple purposes, such as PAPR analisys
			self.ofdm_tx_file_sink = blocks.file_sink(gr.sizeof_gr_complex*1, "../logs/ofdm_comms/half_duplex/ofdm_tx.dat", True) #True->append instead of overwrite
			self.ofdm_tx_file_sink.set_unbuffered(False)

			self.ofdm_rx_file_sink = blocks.file_sink(gr.sizeof_gr_complex*1, "../logs/ofdm_comms/half_duplex/ofdm_rx.dat", True) #True->append instead of overwrite
			self.ofdm_rx_file_sink.set_unbuffered(False)

	def update_sync_data_callback(self, updated_sync_data):
		#MASTER function to update sync data after spectrum sensing
		self.sync_data = updated_sync_data #update sync data to send to slave
		self.update_ofdm_settings() #update MASTER's ofdm data
		self.sync_nOK = True #change sync state to not synced
		print 'going to post_ofdm_pre_sync'
		self.state = 'post_ofdm_pre_sync'
		self._master_spectrum_watcher.state = self.state #inform watcher thread of change of state
		return None

	def slave_unlock_callback(self):
		#SLAVE function to unlock state if it losts synchronism
		self.sync_nOK = True
		print 'forcing -> going to post_ofdm_pre_sync'
		self.state = 'post_ofdm_pre_sync'
		self._slave_timeout_unlock.state = self.state
		return None

	def idle_callback(self):
		self.state = 'idle'
		print 'idling master'
		return None

	def start_master_watch_thread(self):
		#MASTER starts spectrum watcher thread
		self._master_spectrum_watcher = _master_spectrum_watcher_thread(self.hardware_type, self.rf_source,
		 self.sense_rxpath, self.payload_src, self.w_crc, self.cs_probe_ofdm, self.sensing_settings,
		  self.ofdm_settings, self.sync_data, self.update_sync_data_callback, self.idle_callback, self.log_file)

	def start_slave_timeout_unlock_thread(self):
		#SLAVE starts slave unlock thread
		self._slave_timeout_unlock = _slave_timeout_unlock_thread(self.sensing_settings['period_sense']*1.5,
		 self.slave_unlock_callback, self.log_file) #-> unlock time (s)

	def new_slave_sync_count(self):
		#SLAVE restarts sync count
		self.slave_sync_count = [False for el in self.slave_sync_count]

	def add_slave_sync_count(self, nr):
		#SLAVE updates sync count
		self.slave_sync_count[int(nr)] = True

	def new_master_sync_ack_count(self):
		#MASTER restarts ack count
		self.master_sync_ack_count = [False for el in self.master_sync_ack_count]

	def add_master_sync_ack_count(self, nr):
		#MASTER updates ack count
		self.master_sync_ack_count[int(nr)] = True

	def pre_sync(self):
		# Prepares tb flowgraph for sync'ing
		self.tb.stop() #stop
		self.tb.wait() #wait
		self.tb.disconnect_all() #disconnect previous
		debug = False
		scramble = False
		#BLOCKS
		agc = analog.agc2_cc(1e-1, 1e-2, 1.0, 1.0)
		agc.set_max_gain(65536)
		self.sync_rxpath = sync_receive_path(debug, self.sync_settings['sync_samp_rate'], self.sync_rx_callback, scramble)
		self.sync_txpath = sync_transmit_path(self.sync_settings['sync_samp_rate'], self.sync_settings['sync_packet_len'], scramble)
		if self.hardware_type == 'usrp':
			self.rf_source.set_samp_rate(self.sync_settings['sync_samp_rate'])
			self.rf_source.set_center_freq(uhd.tune_request(self.sync_settings['sync_fc'], self.sync_settings['sync_dc_offset']))
			self.rf_source.set_antenna(_sync_rx_ant, 0)
			self.rf_sink.set_samp_rate(self.sync_settings['sync_samp_rate'])
			self.rf_sink.set_center_freq(uhd.tune_request(self.sync_settings['sync_fc'], self.sync_settings['sync_dc_offset']))
		#CLIPPING
		#sync_clipper = ofdm_tools.clipper_cc(self.sync_clipping_factor) #c++ version
		#TX filter
		tx_filter = filter.iir_filter_ccd((_sync_iir_forward_OOB), (_sync_iir_feedback_OOB), False) #tx_filter = iir_complex_filter(_sync_iir_forward_OOB, _sync_iir_feedback_OOB)

		#CONNECTIONS
		#RX
		self.tb.connect(self.rf_source, agc, self.sync_rxpath)
		self.tb.connect(self.rf_source, self.cs_probe_sync)
		#TX
		self.tb.connect(self.sync_txpath, tx_filter, self.rf_sink)
		#self.tb.connect(self.sync_txpath, sync_clipper, tx_filter, self.rf_sink)

		#if self.agent == 'MASTER':
		#	self.tb.connect(self.sync_txpath, self.sync_tx_file_sink)
		#	self.tb.connect(self.sync_txpath, sync_clipper, self.sync_tx_file_sink_clip)

		self.tb.start()

	def pre_ofdm(self):
		# Prepares tb flowgraph for ofdm'ing
		self.tb.stop()
		self.tb.wait()
		self.tb.disconnect_all()
		debug = False
		#BLOCKS
		self.sense_rxpath = spectrum_probe(self.sensing_settings['time_sense'], self.ofdm_settings['ofdm_samp_rate'])
		#self.ne = noise_estimator(samp_rate, channel_rate, t_obs)

		self.payload_src = ofdm_tools.payload_source(self.ofdm_settings['ofdm_packet_len'],) # gerenates frames from TUN/TAP packets
		self.payload_snk = ofdm_tools.payload_sink(self.ofdm_rx_callback) # gerenates packets from received frames
		self.ofdm_transceiver = ofdm_tools.ofdm_radio_hier(
			pilot_carriers = self.sync_data['pilot_carriers'], pilot_symbols = self.sync_data['pilot_symbols'],
			occupied_carriers = self.sync_data['occupied_carriers'], samp_rate = self.ofdm_settings['ofdm_samp_rate'],
			packet_len = self.ofdm_settings['ofdm_packet_len'], payload_mod = digital.constellation_qpsk() ,
			sync_word1 = self.sync_data['sync_word1'], sync_word2 = self.sync_data['sync_word2'],
			 scramble_mode=0, crc_mode=self.w_crc, clipper_mode=0, clipping_factor=10)

		if self.hardware_type == 'usrp':
			self.rf_source.set_samp_rate(self.ofdm_settings['ofdm_samp_rate'])
			self.rf_source.set_center_freq(uhd.tune_request(self.ofdm_settings['ofdm_fc'], self.ofdm_settings['ofdm_dc_offset']))
			self.rf_source.set_antenna(_ofdm_rx_ant, 0)
			self.rf_sink.set_samp_rate(self.ofdm_settings['ofdm_samp_rate'])
			self.rf_sink.set_center_freq(uhd.tune_request(self.ofdm_settings['ofdm_fc'], self.ofdm_settings['ofdm_dc_offset']))

		#CONNECTIONS
		self.tb.connect(self.payload_src, (self.ofdm_transceiver, 0))
		self.tb.connect(self.rf_source, (self.ofdm_transceiver, 1))
		self.tb.connect(self.rf_source, self.cs_probe_ofdm)
		self.tb.connect(self.rf_source, self.sense_rxpath)

		self.tb.connect((self.ofdm_transceiver, 0), self.payload_snk)
		self.tb.connect((self.ofdm_transceiver, 1), self.rf_sink)

		if self.agent == 'MASTER' and _record_samp_stream:
			self.tb.connect((self.ofdm_transceiver, 1), self.ofdm_tx_file_sink)
		#	self.tb.connect(self.rf_source, self.ofdm_rx_file_sink)

		self.tb.start()
		self.data_to_load = self.ofdm_settings['ofdm_packet_len'] - 40

	def update_master_spectrum_watcher(self):
		#MASTER updates spectrum watcher data
		self._master_spectrum_watcher.payload_src = self.payload_src
		self._master_spectrum_watcher.cs_probe_ofdm = self.cs_probe_ofdm
		self._master_spectrum_watcher.rf_source = self.rf_source
		self._master_spectrum_watcher.rf_sink = self.rf_sink

	def update_ofdm_settings(self):
		#MASTER / SLAVE update ofdm data after spectrum sensing and or received sync data
		self.ofdm_settings['ofdm_fc'] = self.sync_data['ofdm_fc']
		self.ofdm_settings['ofdm_samp_rate'] = self.sync_data['ofdm_samp_rate']
		self.ofdm_settings['ofdm_fft_len'] = (len(self.sync_data['sync_word1'])+len(self.sync_data['sync_word2'])) / 2
		self.ofdm_settings['ofdm_packet_len'] = self.sync_data['ofdm_packet_len']
		self.ofdm_settings['payload_mod'] = self.sync_data['payload_mod']
		self.ofdm_settings['ofdm_dc_offset'] = self.ofdm_settings['ofdm_samp_rate'] / 2 #fixed value for master/slave
		#self.ofdm_settings['lobe_len'] = self.ofdm_settings['ofdm_fft_len'] / 32
		self.ofdm_settings['cp_len'] = self.ofdm_settings['ofdm_fft_len'] / 4 #fixed value for master/slave
		self.ofdm_settings['roll_off'] = 0 #self.ofdm_settings['cp_len'] / 32 #fixed value for master/slave

	def sync_channel_available(self, delay):
		# CSMA back-off for sync
		while self.cs_probe_sync.unmuted(): #10*math.log10(self.cs_probe_ofdm.level()) > self.cs_probe_ofdm.threshold(): #
			sys.stderr.write('SYNC Back-off')
			time.sleep(delay)
			if delay < 0.050:
				delay = delay * 2	# exponential back-off
			print 'level:', 10*math.log10(self.cs_probe_sync.level())
		time.sleep(0.01)
		return None

	def ofdm_channel_available(self, delay, forced_delay):
		# CSMA back-off for ofdm
		time.sleep(randrange(1,10,1)*forced_delay)
		while self.cs_probe_ofdm.unmuted(): #10*math.log10(self.cs_probe_ofdm.level()) > self.cs_probe_ofdm.threshold(): #
			sys.stderr.write('OFDM Back-off')
			time.sleep(delay)
			if delay < 0.050:
				delay = delay * 2	# exponential back-off
			print 'level:', 10*math.log10(self.cs_probe_ofdm.level())
		return None

	def signal_handler(self, signum, frame):
		#exception to handle with the os.read function when it gets stuck waiting for packets...
		raise Exception("Timed out!")

	def set_tx_gain(self, val):
		self.tx_gain = val
		self.rf_sink.set_gain(val, 0)
		print 'tx_gain set to', val

	def set_rx_gain(self, val):
		self.rx_gain = val
		self.rf_source.set_gain(val, 0)
		print 'rx_gain set to', val

	def safe_quit(self):
		self.tb.stop()
		self.tb.wait()
		self.tb.disconnect_all()

	def check_sync_words(self, slave_ack):
		if len(self.sync_data['sync_word1']) != len(self.sync_data['sync_word2']):
			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sync_word_len_error\n')
			return False
		else:
			return (True and slave_ack)

	def generate_sync_data(self, spectrum_constraint_hz):
		#convert constraint from hz to fft bins
		spectrum_constraint_fft = spectrum_translator(spectrum_constraint_hz, self.ofdm_settings['ofdm_fc'],
		 self.ofdm_settings['ofdm_samp_rate'], self.ofdm_settings['ofdm_fft_len'], self.ofdm_settings['canc_bins'])
		#build sync data
		self.sync_data['occupied_carriers'], self.sync_data['pilot_carriers'], self.sync_data['pilot_symbols'], self.sync_data['sync_word1'], self.sync_data['sync_word2'] = spectrum_enforcer(self.ofdm_settings['ofdm_fft_len'], 
		 spectrum_constraint_fft, self.ofdm_settings['lobe_len'])

		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'spectrum_constraint_hz-' + str(spectrum_constraint_hz) + '\n')
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'spectrum_constraint_fft-' + str(spectrum_constraint_fft) + '\n')
		return None

	def estimate_noise_level(self, noise_band, n_time, offset):
		self.noise_estimator = noise_estimator(self.ofdm_settings['ofdm_samp_rate'], noise_band, n_time, offset)
		self.tb.stop()
		self.tb.wait()
		self.tb.disconnect_all()
		self.tb.connect(self.rf_source, self.noise_estimator)
		self.tb.run()
		self.tb.disconnect_all() 

		self.sensing_settings['ed_threshold'] = self.noise_estimator.get_noise_estimate()*1
		return None

	def sync_slave(self, sync_data_s, delay):
		while self.sync_nOK:
			nr = 0
			for msg in sync_data_s:
				self.sync_channel_available(delay)
				self.sync_txpath.send_pkt_s(make_sync_packet(msg, self.sync_settings['sync_packet_len'], 'B', nr))
				print 'sent msg nr', nr
				nr += 1
			time.sleep(1)
		return None

	def master_main_loop(self):
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'main_loop_started\n')
		min_delay = 1e-6	# seconds
		forced_delay = 1e-6
		_ofdm_n_txd = 0

		#1ST Sensing
		if self.hardware_type == 'usrp': #because it could be a 'net' source (tcp / udp)
			self.rf_source.set_samp_rate(self.ofdm_settings['ofdm_samp_rate'])
			self.rf_source.set_center_freq(uhd.tune_request(self.ofdm_settings['ofdm_fc'], self.ofdm_settings['ofdm_dc_offset']))
			self.rf_source.set_antenna(_sense_rx_ant, 0)

			#noise estimate
			offset = 0
			noise_band = 20000
			n_time = 1
			self.estimate_noise_level(noise_band, n_time, offset) #----> receice FG must be / will be stopped!!!

			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'noise_estimate:' + str(self.sensing_settings['ed_threshold']) + '\n')
			print self.sensing_settings['ed_threshold']

			self.sense_rxpath = spectrum_probe(self.sensing_settings['time_sense'], self.ofdm_settings['ofdm_samp_rate'])
			self.tb.connect(self.rf_source, self.sense_rxpath)
			self.tb.start() #start
			time.sleep(0.5)
		else: self.sense_rxpath = blocks.null_sink(gr.sizeof_gr_complex*1)

		if self.hardware_type == 'usrp':
			#Compute the spectrum constraint based on the spectrum
			spectrum_constraint_hz = spectrum_scan(self.sensing_settings['ofdm_band_start'], self.sensing_settings['ofdm_band_finish'],
			 self.sensing_settings['channel_rate'], self.sensing_settings['srch_bw'], self.sensing_settings['n_fft'], self.rf_source, self.sense_rxpath, 
			 self.sensing_settings['method'], self.sensing_settings['ed_threshold'], self.sensing_settings['time_sense']*4, True) # 0.1 -> wait time before get samples, True = show plot
		else:
			spectrum_constraint_hz = []

		#self.safe_quit()
		#plots.show()
		#sys.exit(0)

		#spectrum_constraint_hz = [_rand_bad_freqs[randrange(5)]] #force some spectrum constraint...
		#spectrum_constraint_hz = []

		self.generate_sync_data(spectrum_constraint_hz) #generate sync data based on spectrum_constraint_hz
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'occupied_carriers-' + str(len(self.sync_data['occupied_carriers'][0])) + '\n')

		#end initial sense -> set tb flowgraph for sync
		self.pre_sync()

		#sync data --> occupied_carriers pilot_carriers pilot_symbols sync_word1 sync_word2 ofdm_fc ofdm_samp_rate ofdm_packet_len payload_mod
		#slice sync data in sync data packets
		temp = chunks_of_word(str(self.sync_data),  self.sync_settings['sync_packet_len']-10)
		sync_data_s = [''] * self.sink_len
		#fill sync packets w/ sync data --> the number of packets must be larger than the number of sync data slices...
		sync_data_s[:len(temp)] = temp
		print 'sd', len(str(self.sync_data))
		print 'sync data avail', self.sync_settings['sync_packet_len'] * self.sink_len
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sync_data_len-' + str(len(str(self.sync_data))) + '-sync_data_space_available-' + str(self.sync_settings['sync_packet_len'] * self.sink_len) + '\n')

		self.sync_nOK = True #self.sync_nOK = False
		self.sync_slave(sync_data_s, min_delay)

		print 'going to post_sync_pre_ofdm'
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + '1st_sync_ok\n')
		self.state = 'post_sync_pre_ofdm' #jump to post_sync_pre_ofdm and then ofdm loop
		#Start spectrum watch thread
		self.start_master_watch_thread() #update thread value: self._spectrum_watcher.value = new_value
		self._master_spectrum_watcher.state = self.state

		while 1: # master loop
			if self.state == 'ofdm':
				payload = None
				signal.signal(signal.SIGALRM, self.signal_handler) #initiate os.read execution monitor
				signal.alarm(2) #set trigger time to 1s
				try:
					payload = os.read(self.tun_fd, self.data_to_load)
					if not payload:
						self.payload_src.send_pkt_s(eof=True)
						break
				except Exception:
					print 'TIMEOUT'
				finally:
					signal.alarm(0) # disable alarm

				if payload != None:
					print "Tx: len(payload) = %4d" % (len(payload),)
					self.ofdm_channel_available(min_delay, forced_delay) #CSMA - back off
					if self.w_crc == 1: 
						frame = make_packet(payload, self.ofdm_settings['ofdm_packet_len'], 'A')
						self.payload_src.send_pkt_s(frame)
					else: 
						frame = crc.gen_and_append_crc32(make_packet(payload, self.ofdm_settings['ofdm_packet_len']-4, 'A'))
						#crc32 adds 4 bytes
						self.payload_src.send_pkt_s(frame)
					_ofdm_n_txd += 1
				self._master_spectrum_watcher.state = self.state

			else:
				if self.state == 'sync':
					print 'state:', self.state
					temp = chunks_of_word(str(self.sync_data),  self.sync_settings['sync_packet_len']-10) #header adds 10 bytes
					sync_data_s = [''] * self.sink_len
					sync_data_s[:len(temp)] = temp
					self.sync_slave(sync_data_s, min_delay)

					print 'sync done'
					print 'going to post_sync_pre_ofdm'
					self.state = 'post_sync_pre_ofdm'
					self._master_spectrum_watcher.state = self.state

				if self.state == 'post_sync_pre_ofdm': #allways before ofdm
					print 'state:', self.state
					#sync off ofdm on
					self.pre_ofdm()
					#update master_watch_thread
					self.update_master_spectrum_watcher()
					print 'going to ofdm!'
					self.state = 'ofdm'
					self._master_spectrum_watcher.state = self.state

				if self.state == 'post_ofdm_pre_sync': #only the watcher can call this one... turn off ofdm flowgraph
					print 'state:', self.state
					self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-total_ofdm_txd_packets-' + str(_ofdm_n_txd) + '\n')
					# ofdm off sync on
					self.pre_sync()
					print 'going to sync...'
					self.state = 'sync'
					self._master_spectrum_watcher.state = self.state

				if self.state == 'stop':
					print 'state:', self.state
					print 'exiting...'
					sys.exit(0)

				if self.state == 'idle':
					print 'state', self.state
					time.sleep(.001)

		'''
		A-from MASTER OS to SLAVE OS
		B-from MASTER SENSE to SLAVE SENSE
		C-from SLAVE OS to MASTER OS
		D-from SLAVE SENSE to MASTER SENSE
		U- UNKNOWN
		'''

	def slave_main_loop(self):
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'main_loop_started\n')
		min_delay = 1e-6	# seconds
		forced_delay = 1e-6
		_ofdm_n_txd = 0

		self.pre_sync()

		#1st sync...
		print 'waiting for 1st sync'
		self.sync_nOK = True
		while self.sync_nOK:
			time.sleep(0.5)
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + '1st_sync_end(ok/Nok)\n')

		#rebuild sync data
		temp = ''
		for data in self.slave_raw_sync_data:
			temp += data
		slave_ack = True
		try: 
			self.sync_data = ast.literal_eval(temp)
			#make sure MASTER received ack...
		except: #catch any error that might occour
			slave_ack = False
			print 'error while recovering sync data'
			print 'going to sync again'
			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'bad_1st_sync_data\n')
			self.state = 'sync' #jump to post_sync_pre_ofdm and then ofdm loop

		slave_ack = self.check_sync_words(slave_ack) # check if sync words are correct

		if slave_ack:
			for i in range(3):
				self.sync_channel_available(min_delay)
				self.sync_txpath.send_pkt_s(make_sync_packet('ACK', self.sync_settings['sync_packet_len'], 'D', i))
				time.sleep(0.2)
				self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sent_ack_to_master\n')
			self.update_ofdm_settings()
			print 'end 1st sync, going to post_sync_pre_ofdm'
			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + '1st_sync_ok\n')
			self.state = 'post_sync_pre_ofdm'

		self.start_slave_timeout_unlock_thread()
		self._slave_timeout_unlock.state = self.state

		while 1: #slave loop
			if self.state == 'ofdm':
				payload = None
				signal.signal(signal.SIGALRM, self.signal_handler) #initiate os.read execution monitor
				signal.alarm(2) #set trigger time to 1s
				try:
					payload = os.read(self.tun_fd, self.data_to_load)
					if not payload:
						self.payload_src.send_pkt_s(eof=True)
						break
				except Exception:
					print 'TIMEOUT'
				finally:
					signal.alarm(0) # disable alarm

				if payload != None:
					print "Tx: len(payload) = %4d" % (len(payload),)
					self.ofdm_channel_available(min_delay, forced_delay) #CSMA - back off
					if self.w_crc == 1: 
						frame = make_packet(payload, self.ofdm_settings['ofdm_packet_len'], 'C')
						self.payload_src.send_pkt_s(frame)
					else: 
						frame = crc.gen_and_append_crc32(make_packet(payload, self.ofdm_settings['ofdm_packet_len']-4, 'C'))
						#crc32 adds 4 bytes
						self.payload_src.send_pkt_s(frame)
					_ofdm_n_txd += 1
				self._slave_timeout_unlock.state = self.state

			else:
				if self.state == 'sync':
					print 'state:', self.state
					self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'state=sync\n')
					self.sync_nOK = True
					while self.sync_nOK:
						time.sleep(0.5)

					#rebuild sync data
					temp = ''
					for data in self.slave_raw_sync_data:
						temp += data
					slave_ack = True
					try: #try to recover sync data
						self.sync_data = ast.literal_eval(temp)
					except: #catch any error that might occour
						slave_ack = False
						print 'error while recovering sync data'
						print 'going to sync again'
						self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'bad_sync_data\n')
						self.state = 'sync' #jump to post_sync_pre_ofdm and then ofdm loop
						self._slave_timeout_unlock.state = self.state

					slave_ack = self.check_sync_words(slave_ack) # check if sync words are correct

					if slave_ack:
						#make sure MASTER received ack...
						for i in range(3):
							self.sync_channel_available(min_delay)
							self.sync_txpath.send_pkt_s(make_sync_packet('ACK', 512, 'D', i))
							time.sleep(0.2)
						self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'told_master_ack(sync)\n')
						self.update_ofdm_settings()
						print 'going to post_sync_pre_ofdm'
						self.state = 'post_sync_pre_ofdm' #jump to post_sync_pre_ofdm and then ofdm loop

				if self.state == 'post_sync_pre_ofdm': #allways before ofdm
					print 'state:', self.state
					#sync off ofdm on
					self.pre_ofdm()
					print 'going to ofdm!'
					self.state = 'ofdm'
					self._slave_timeout_unlock.state = self.state

				if self.state == 'post_ofdm_pre_sync': #only the watcher can call this one... turn off ofdm flowgraph
					print 'state:', self.state
					self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-total_ofdm_txd_packets-' + str(_ofdm_n_txd) + '\n')
					# ofdm off sync on
					self.pre_sync()
					print 'going to sync...'
					self.state = 'sync'
					self._slave_timeout_unlock.state = self.state


				if self.state == 'stop':
					print 'state:', self.state
					print self.sync_data
					sys.exit(0)

				if self.state == 'idle':
					print 'state', self.state
					time.sleep(.001)

		'''
		A-from MASTER OS to SLAVE OS
		B-from MASTER SENSE to SLAVE SENSE
		C-from SLAVE OS to MASTER OS
		D-from SLAVE SENSE to MASTER SENSE
		U- UNKNOWN
		'''

#master thread for sensing during execution
class _master_spectrum_watcher_thread(_threading.Thread):
	def __init__(self, hardware_type, rf_source, sense_rxpath, payload_src, w_crc,
	 cs_probe_ofdm, sensing_settings, ofdm_settings, sync_data, update_sync_data_callback, idle_callback, log_file):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.hardware_type = hardware_type
		self.rf_source = rf_source
		self.sense_rxpath = sense_rxpath
		self.payload_src = payload_src
		self.w_crc = w_crc
		self.cs_probe_ofdm = cs_probe_ofdm
		self.sensing_settings = sensing_settings
		self.ofdm_settings = ofdm_settings
		self.sync_data = sync_data
		self.update_sync_data_callback = update_sync_data_callback
		self.keep_running = True #set to False to stop thread
		self.state = None
		self.idle_callback = idle_callback
		self.log_file = log_file
		self.start()

	def ofdm_channel_available(self, delay):
		while self.cs_probe_ofdm.unmuted(): #10*math.log10(self.cs_probe_ofdm.level()) > self.cs_probe_ofdm.threshold(): #
			sys.stderr.write('OFDM Back-off')
			time.sleep(delay)
			if delay < 0.050:
				delay = delay * 2	# exponential back-off
			print 'level:', 10*math.log10(self.cs_probe_ofdm.level())
		return None

	def generate_sync_data(self, spectrum_constraint_hz):
		#convert constraint from hz to fft bins
		spectrum_constraint_fft = spectrum_translator(spectrum_constraint_hz, self.ofdm_settings['ofdm_fc'],
		 self.ofdm_settings['ofdm_samp_rate'], self.ofdm_settings['ofdm_fft_len'], self.ofdm_settings['canc_bins'])
		#build sync data
		self.sync_data['occupied_carriers'], self.sync_data['pilot_carriers'], self.sync_data['pilot_symbols'], self.sync_data['sync_word1'], self.sync_data['sync_word2'] = spectrum_enforcer(self.ofdm_settings['ofdm_fft_len'], 
		 spectrum_constraint_fft, self.ofdm_settings['lobe_len'])

		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'spectrum_constraint_hz-' + str(spectrum_constraint_hz) + '\n')
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'spectrum_constraint_fft-' + str(spectrum_constraint_fft) + '\n')

		return None

	def run(self):
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'spectrum_watcher_thread_started\n')
		min_delay = 0.001 #min delay for CSMA implementation
		previous_spectrum_constraint_hz = []
		print 'master spectrum watch thread started'
		time.sleep(1)
		while self.keep_running:
			if self.state == 'ofdm': #triggers sync mode if we're in ofdm mode...
				time.sleep(self.sensing_settings['period_sense']) #start timer for sensing
				self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sensing_triggered_watcher\n')

				for a in range(3): #trigger slave to go to sync mode - this way slave mutes TX
					self.ofdm_channel_available(min_delay)
					if self.w_crc == 1: 
						frame = make_packet('sync mode', self.ofdm_settings['ofdm_packet_len'], 'B')
						self.payload_src.send_pkt_s(frame)
					else: 
						frame = crc.gen_and_append_crc32(make_packet('sync mode', self.ofdm_settings['ofdm_packet_len']-4, 'B'))
						#crc32 adds 4 bytes
						self.payload_src.send_pkt_s(frame)
					#self.payload_src.send_pkt_s(make_packet('sync mode', self.ofdm_settings['ofdm_packet_len'], 'B'))
					time.sleep(0.2)
					print 'sending order to slave: switch to sync mode'

				self.idle_callback() #switch MASTER to idle mode - we can only conduct spectrum sensing if the slave is already out of OFDM mode

				if self.hardware_type == 'usrp':
					spectrum_constraint_hz = spectrum_scan(self.sensing_settings['ofdm_band_start'], self.sensing_settings['ofdm_band_finish'],
					 self.sensing_settings['channel_rate'], self.sensing_settings['srch_bw'], self.sensing_settings['n_fft'], self.rf_source, 
					 self.sense_rxpath, self.sensing_settings['method'], self.sensing_settings['ed_threshold'], self.sensing_settings['time_sense']*4, False) #True - plots results
				else: #test purposes w/ TCP/UDP
					spectrum_constraint_hz = []

				#spectrum_constraint_hz = [_rand_bad_freqs[randrange(5)]] #force some spectrum constraint...

				#if there is any change in spectrum analysis:
				if previous_spectrum_constraint_hz != spectrum_constraint_hz:
					previous_spectrum_constraint_hz = spectrum_constraint_hz

					self.generate_sync_data(spectrum_constraint_hz) #generate sync data based on spectrum_constraint_hz
					self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'occupied_carriers-' + str(len(self.sync_data['occupied_carriers'][0])))

					#chage the state to post_ofdm_pre_sync and update sync data and ofdm data!
					if self.update_sync_data_callback:
						self.update_sync_data_callback(self.sync_data)

				#if there is NO change in spectrum analysis:
				else:
					#chage the state to post_ofdm_pre_sync and update sync data and ofdm data!
					if self.update_sync_data_callback:
						self.update_sync_data_callback(self.sync_data)

			#if we are not in OFDM mode, there is no need to trigger anything
			else:
				time.sleep(.1)

#slave thread to unlock slave from "ofdm" state if it gets out of sync with master
class _slave_timeout_unlock_thread(_threading.Thread):
	def __init__(self, unlock_time, slave_unlock_callback, log_file):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.slave_unlock_callback = slave_unlock_callback
		self.unlock_time = unlock_time
		self.log_file = log_file
		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.start()

	def run(self):
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'timeout_unlock_thread_started\n')
		counter = 0
		max_count = self.unlock_time * 10
		while self.keep_running:
			if self.state == 'ofdm':
				counter += 1
				time.sleep(0.1)
				if self.slave_unlock_callback and counter > max_count:
					self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'timeout_triggered\n')
					print 'TIMEOUT - lost MASTER - going to sync'
					self.slave_unlock_callback() #forces slave to post ofdm pre sync mode
					counter = 0
			if self.state != 'ofdm':
				counter = 0
				time.sleep(0.1)
