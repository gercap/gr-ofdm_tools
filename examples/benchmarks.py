from ofdm_cr_tools import *
import gnuradio.gr.gr_threading as _threading
from random import randrange
from grc_gnuradio import wxgui as grc_wxgui
import wx
from gnuradio.wxgui import forms
import SimpleXMLRPCServer
import threading, random
import ofdm_tools

_rand_bad_freqs = [158e6, 157.5e6, 157.9e6, 158.1e6, 158.34e6]

_sync_iir_forward_OOB = [0.005277622700213007, 0.03443705907448985, 0.1214101788557494, 0.29179662246081545, 0.52428014905364, 0.7350677973792328, 0.8210395030022875, 0.7350677973792348, 0.5242801490536404, 0.291796622460816, 0.1214101788557501, 0.03443705907448997, 0.005277622700213012]
_sync_iir_feedback_OOB = [1.0, -1.0455317889337852, 3.9201525346250072, -3.9114761684448958, 6.54266144224035, -5.737287389902878, 5.820328302284336, -4.134700802700442, 2.7949972248757664, -1.4584448495689168, 0.6358650797085171, -0.19847981428665007, 0.04200458351675313]

_probe_thresh = -35 #-35

_ofdm_rx_ant = 'RX2' # TX/RX / RX2
_sense_rx_ant = 'RX2' # TX/RX / RX2
_sync_rx_ant = 'TX/RX' # TX/RX / RX2

_record_samp_stream = False
_discontinuous = True

class benchmark(object):
	"""
	by Germano Jun 14
	"""
	def __init__(self, agent, n_test_packets, hardware_type, clipping_factor,
	 sensing_settings, ofdm_settings, rf_source, rf_sink, sync_rx_callback, bench_rx_callback, w_crc):
#ofdm_settings  = {'ofdm_fc':ofdm_fc, 'ofdm_samp_rate':ofdm_samp_rate, 'ofdm_fft_len':ofdm_fft_len,'ofdm_packet_len':ofdm_packet_len, 'payload_mod':payload_mod, 'ofdm_dc_offset':ofdm_dc_offset, 'lobe_len':lobe_len,'cp_len':cp_len, 'roll_off':roll_off, 'canc_bins':canc_bins}
#sensing_settings = {'ofdm_band_start':ofdm_band_start, 'ofdm_band_finish':ofdm_band_finish, 'channel_rate':channel_rate,'srch_bw':srch_bw, 'n_fft':n_fft, 'method':method , 'ed_threshold':ed_threshold, 'time_sense':time_sense, 'period_sense':period_sense}
#sync_settings = {'sync_samp_rate':sync_samp_rate, 'sync_fc':sync_fc, 'sync_packet_len':sync_packet_len, 'sync_dc_offset':sync_dc_offset}


		self.log_file = open('../logs/benchmarks/'+ agent +'_mac_bench_Log'+'-'+ time.strftime("%y%m%d") + '-' + time.strftime("%H%M%S"),'w')

		self.hardware_type = hardware_type #what type of hardware is being used for TX/RX
		self.n_test_packets = n_test_packets

		self.sensing_settings = sensing_settings #spectrum sensing settings
		self.ofdm_settings = ofdm_settings #ofdm mod/demod settings
		if agent == 'MASTER':
			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'ofdm_settings-' + str(self.ofdm_settings) + '\n')
		self.sync_settings = {'sync_samp_rate':125000, 'sync_fc':155e6, 'sync_packet_len':400, 
		'sync_dc_offset':(125000/2)} #synchronizer mod/demod settings

		self.tb = gr.top_block() #THE gnuradio top block for sync and ofdm'ing
		self.rf_source = rf_source # rf receiver source
		self.rf_sink = rf_sink # rf transmitter sink

		self.w_crc = w_crc

		self.clipping_factor = clipping_factor
		self.data_to_load = None

		if agent == 'MASTER':
			self.sync_data = {'occupied_carriers':None, 'pilot_carriers':None, 'pilot_symbols':None,
			 'ofdm_fc':ofdm_settings['ofdm_fc'], 'ofdm_samp_rate':ofdm_settings['ofdm_samp_rate'],
			  'payload_mod':ofdm_settings['payload_mod'], 'ofdm_packet_len':ofdm_settings['ofdm_packet_len'],
			   'sync_word1':None, 'sync_word2':None}

		if agent == 'SLAVE':
			self.sync_data = {'occupied_carriers':(), 'pilot_carriers':(), 'ofdm_fc':None, 'ofdm_samp_rate':None,
			'payload_mod':None, 'ofdm_packet_len':None, 'sync_word1':(), 'sync_word2':()}

		self.sync_nOK = True # False Flag for sync process nOK=True --> not synced 
		self.sink_len = 10 #number of packets used to send sync data
		self.slave_raw_sync_data = [False] * self.sink_len #data container for received sync data
		self.slave_sync_count = [False] * self.sink_len #structure to control sync packets - slave
		self.master_sync_ack_count = [False] * self.sink_len #structure to control sync acks - master

		if self.hardware_type == 'usrp': self.probe_level = _probe_thresh #40 CSMA threshold
		else: self.probe_level = -10
		self.cs_probe_ofdm = analog.probe_avg_mag_sqrd_c(self.probe_level, 0.01) #CSMA probe
		self.cs_probe_sync = analog.probe_avg_mag_sqrd_c(self.probe_level, 0.01) #CSMA probe

		self.agent = agent # MASTER / SLAVE
		self.state = None # syncOK / syncNOK

		self.bench_rx_callback = bench_rx_callback
		self.sync_rx_callback = sync_rx_callback

		if self.agent == 'MASTER' and _record_samp_stream:  #logging files... multiple purposes, such as PAPR analisys
			self.ofdm_tx_file_sink = blocks.file_sink(gr.sizeof_gr_complex*1, "../logs/benchmarks/ofdm_tx_bench.dat", True) #True->append instead of overwrite
			self.ofdm_tx_file_sink.set_unbuffered(False)
		if self.agent == 'SLAVE' and _record_samp_stream:  #logging files... multiple purposes, such as PAPR analisys
			self.ofdm_rx_file_sink = blocks.file_sink(gr.sizeof_gr_complex*1, "../logs/benchmarks/ofdm_rx_bench.dat", True) #True->append instead of overwrite
			self.ofdm_rx_file_sink.set_unbuffered(False)

	def update_sync_data_callback(self, updated_sync_data):
		#MASTER function to update sync data after spectrum sensing
		self.sync_data = updated_sync_data #update sync data to send to slave
		self.update_ofdm_settings() #update MASTER's ofdm data
		self.sync_nOK = True #change sync state to not synced
		print 'going to post_ofdm_pre_sync'
		return None

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
		self.sync_rxpath = sync_receive_path(debug, self.sync_settings['sync_samp_rate'], self.sync_rx_callback, scramble)
		self.sync_txpath = sync_transmit_path(self.sync_settings['sync_samp_rate'], self.sync_settings['sync_packet_len'], scramble)
		agc = analog.agc2_cc(1e-1, 1e-2, 1.0, 1.0)
		agc.set_max_gain(65536)
		if self.hardware_type == 'usrp':
			self.rf_source.set_samp_rate(self.sync_settings['sync_samp_rate'])
			self.rf_source.set_center_freq(uhd.tune_request(self.sync_settings['sync_fc'], self.sync_settings['sync_dc_offset']))
			self.rf_source.set_antenna(_sync_rx_ant, 0)
			self.rf_sink.set_samp_rate(self.sync_settings['sync_samp_rate'])
			self.rf_sink.set_center_freq(uhd.tune_request(self.sync_settings['sync_fc'], self.sync_settings['sync_dc_offset']))
		#CLIPPING
		#sync_clipper = ofdm_tools.clipper_cc(self.sync_clipping_factor) #c++ version
		#TX filter
		tx_filter = filter.iir_filter_ccd((_sync_iir_forward_OOB), (_sync_iir_feedback_OOB), False)

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

	def pre_ofdm_benchmark(self):
		# Prepares tb flowgraph for ofdm'ing
		self.tb.stop()
		self.tb.wait()
		self.tb.disconnect_all()
		debug = False
		#BLOCKS
		self.sense_rxpath = spectrum_probe(self.sensing_settings['time_sense'], self.ofdm_settings['ofdm_samp_rate'])
		#self.ne = noise_estimator(samp_rate, channel_rate, t_obs)

		self.pyload_src = ofdm_tools.payload_source(self.ofdm_settings['ofdm_packet_len'],) # gerenates frames from TUN/TAP packets
		self.pyload_snk = ofdm_tools.payload_sink(self.bench_rx_callback) # gerenates packets from received frames
		self.ofdm_transceiver = ofdm_tools.ofdm_radio_hier(
			pilot_carriers = self.sync_data['pilot_carriers'], pilot_symbols = self.sync_data['pilot_symbols'],
			occupied_carriers = self.sync_data['occupied_carriers'], samp_rate = self.ofdm_settings['ofdm_samp_rate'],
			payload_mod = digital.constellation_qpsk() ,
			sync_word1 = self.sync_data['sync_word1'], sync_word2 = self.sync_data['sync_word2'],
			 scramble_mode=0, crc_mode=self.w_crc, clipper_mode=0, clipping_factor=10)

		if self.hardware_type == 'usrp':
			self.rf_source.set_samp_rate(self.ofdm_settings['ofdm_samp_rate'])
			self.rf_source.set_center_freq(uhd.tune_request(self.ofdm_settings['ofdm_fc'], self.ofdm_settings['ofdm_dc_offset']))
			self.rf_source.set_antenna(_ofdm_rx_ant, 0)
			self.rf_sink.set_samp_rate(self.ofdm_settings['ofdm_samp_rate'])
			self.rf_sink.set_center_freq(uhd.tune_request(self.ofdm_settings['ofdm_fc'], self.ofdm_settings['ofdm_dc_offset']))

		#CONNECTIONS
		self.tb.connect(self.pyload_src, (self.ofdm_transceiver, 0))
		self.tb.connect(self.rf_source, (self.ofdm_transceiver, 1))
		self.tb.connect(self.rf_source, self.cs_probe_ofdm)
		#self.tb.connect(self.rf_source, self.sense_rxpath)

		self.tb.connect((self.ofdm_transceiver, 0), self.pyload_snk)
		self.tb.connect((self.ofdm_transceiver, 1), self.rf_sink)

		if self.agent == 'MASTER' and _record_samp_stream:
			self.tb.connect((self.ofdm_transceiver, 1), self.ofdm_tx_file_sink)
		if self.agent == 'SLAVE' and _record_samp_stream:
			self.tb.connect(self.rf_source, self.ofdm_rx_file_sink)

		self.tb.start()
		self.data_to_load = self.ofdm_settings['ofdm_packet_len'] - 40
		print 'data_to_load', self.data_to_load

	def update_ofdm_settings(self):
		#MASTER / SLAVE update ofdm data after spectrum sensing and or received sync data
		self.ofdm_settings['ofdm_fc'] = self.sync_data['ofdm_fc']
		self.ofdm_settings['ofdm_samp_rate'] = self.sync_data['ofdm_samp_rate']
		self.ofdm_settings['ofdm_fft_len'] = (len(self.sync_data['sync_word1'])+len(self.sync_data['sync_word2'])) / 2
		self.ofdm_settings['ofdm_packet_len'] = self.sync_data['ofdm_packet_len']
		self.ofdm_settings['payload_mod'] = self.sync_data['payload_mod']
		self.ofdm_settings['ofdm_dc_offset'] = self.ofdm_settings['ofdm_samp_rate'] / 2 #fixed value for master/slave

	def sync_channel_available(self, delay):
		# CSMA back-off for sync
		while self.cs_probe_sync.unmuted(): #10*math.log10(self.cs_probe_ofdm.level()) > self.cs_probe_ofdm.threshold(): #
			sys.stderr.write('SYNC Back-off')
			time.sleep(delay)
			if delay < 0.050:
				delay = delay * 2	# exponential back-off
			print 'RX level:', 10*math.log10(self.cs_probe_sync.level())
		time.sleep(0.01)
		return None

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

	def transmit_bench(self):
		min_delay = 10e-6	# seconds
		forced_delay = 1e-6

		#1ST Sensing
		if self.hardware_type == 'usrp': #because it could be a 'net' source (tcp / udp)
			self.rf_source.set_samp_rate(self.ofdm_settings['ofdm_samp_rate'])
			self.rf_source.set_center_freq(uhd.tune_request(self.ofdm_settings['ofdm_fc'], self.ofdm_settings['ofdm_dc_offset']))
			self.rf_source.set_antenna(_sense_rx_ant, 0)

		if self.hardware_type == 'usrp':
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

		if self.hardware_type == 'usrp':
			#Compute the spectrum constraint based on the spectrum
			spectrum_constraint_hz = spectrum_scan(self.sensing_settings['ofdm_band_start'], self.sensing_settings['ofdm_band_finish'],
			 self.sensing_settings['channel_rate'], self.sensing_settings['srch_bw'], self.sensing_settings['n_fft'], self.rf_source, self.sense_rxpath, 
			 self.sensing_settings['method'], self.sensing_settings['ed_threshold'], self.sensing_settings['time_sense']*4, True) # 0.1 -> wait time before get samples, True = show plot
		else:
			spectrum_constraint_hz = []

		spectrum_constraint_hz = [_rand_bad_freqs[randrange(5)]] #force some spectrum constraint...
		#spectrum_constraint_hz = []

		self.generate_sync_data(spectrum_constraint_hz) #generate sync data based on spectrum_constraint_hz
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sync_data-' + str(self.sync_data) + '\n')
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'occupied_carriers-' + str(len(self.sync_data['occupied_carriers'][0])) + '\n')

		#end initial sense -> set tb flowgraph for sync

		#plots.show()

		#sync data --> occupied_carriers pilot_carriers pilot_symbols sync_word1 sync_word2 ofdm_fc ofdm_samp_rate ofdm_packet_len payload_mod
		#slice sync data in sync data packets
		temp = chunks_of_word(str(self.sync_data),  self.sync_settings['sync_packet_len']-10)
		sync_data_s = [''] * self.sink_len
		#fill sync packets w/ sync data --> the number of packets must be larger than the number of sync data slices...
		sync_data_s[:len(temp)] = temp
		print 'nr sync packets', len(sync_data_s)
		print 'sd', len(str(self.sync_data))
		print 'sync data avail', self.sync_settings['sync_packet_len'] * self.sink_len
		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sync_data_len-' + str(len(str(self.sync_data))) + '-sync_data_space_available-' + str(self.sync_settings['sync_packet_len'] * self.sink_len) + '\n')

		###############
		self.pre_sync()
		###############

		self.sync_nOK = True #self.sync_nOK = False
		self.sync_slave(sync_data_s, min_delay)

		time.sleep(2)
		print 'starting tx benchmark!'


		self.pre_ofdm_benchmark()
		for numb in range(1, self.n_test_packets+1):
			N = str(numb)
			Nr = (4-len(N))*'0' + N #force 4 digits
			payload = Nr + ('%030x' % random.randrange(16**(self.data_to_load - 4)))
			if self.w_crc == 1: 
				frame = make_packet(payload, self.ofdm_settings['ofdm_packet_len'], 'A')
				self.pyload_src.send_pkt_s(frame)
			else: 
				frame = digital.crc.gen_and_append_crc32(make_packet(payload, self.ofdm_settings['ofdm_packet_len']-4, 'A'))
				#crc32 adds 4 bytes
				self.pyload_src.send_pkt_s(frame)
			if _discontinuous and numb % 5 == 4:
				time.sleep(1)

			print 'Txd OFDM packet nr: ' + Nr
			#time.sleep(0.001)
		for i in range(5):
			if self.w_crc == 1: 
				frame = make_packet('end', self.ofdm_settings['ofdm_packet_len'], 'B')
				self.pyload_src.send_pkt_s(frame)
			else: 
				frame = digital.crc.gen_and_append_crc32(make_packet('end', self.ofdm_settings['ofdm_packet_len']-4, 'B'))
				#crc32 adds 4 bytes
				self.pyload_src.send_pkt_s(frame)
			time.sleep(0.1)
			print 'Tx END'
		time.sleep(2)
		self.safe_quit()
		print 'fg stoped'
		print 'done OFDM benchmarking'
		sys.exit(0)

		'''
		A-from MASTER OS to SLAVE OS
		B-from MASTER SENSE to SLAVE SENSE
		C-from SLAVE OS to MASTER OS
		D-from SLAVE SENSE to MASTER SENSE
		U- UNKNOWN
		'''

	def receive_bench(self):
		min_delay = 10e-6	# seconds
		forced_delay = 1e-6

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
		try: #try to recover sync data
			self.sync_data = ast.literal_eval(temp)
		except: #catch any error that might occour
			slave_ack = False
			print 'error while recovering sync data'
			print 'going to sync again'
			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'bad_1st_sync_data\n')
			self.state = 'syncNOK' #jump to post_sync_pre_ofdm and then ofdm loop

		slave_ack = self.check_sync_words(slave_ack) # check if sync words are correct

		if slave_ack:
			#send ack to MASTER...
			for i in range(5):
				delay = min_delay
				self.sync_channel_available(delay)
				self.sync_txpath.send_pkt_s(make_sync_packet('ACK', self.sync_settings['sync_packet_len'], 'D', i))
				time.sleep(0.2)
				self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'sent_ack_to_master\n')
			self.update_ofdm_settings()
			print 'end 1st sync'
			self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + '1st_sync_ok\n')
			self.state = 'syncOK' #jump to post_sync_pre_ofdm and then ofdm loop

		self.log_file.write('Time-'+time.strftime("%H%M%S") + '-Evnt-' + 'end_1st_sync_data(ok/Nok)-' + str(self.sync_data) + '\n')

		while 1: #sync OK loop
			if self.state == 'syncOK':
				print '1st sync ok'

				self.pre_ofdm_benchmark()
				while(self.state == 'syncOK'):
					try:
						time.sleep(0.1)
					except KeyboardInterrupt:
						print 'done OFDM benchmarking'
						self.safe_quit()
						print 'fg stoped'
						raise
				self.safe_quit()
				print 'fg stoped'
				print 'done OFDM benchmarking'
				sys.exit(0)

			elif self.state == 'syncNOK':
				print 'state:', self.state
				self.sync_nOK = True
				while self.sync_nOK:
					time.sleep(0.5)
				#rebuild sync data
				temp = ''
				for data in self.slave_raw_sync_data:
					temp += data
				try:
					self.sync_data = ast.literal_eval(temp)
					#make sure MASTER received ack...
					for i in range(5):
						delay = min_delay
						self.sync_channel_available(delay)
						self.sync_txpath.send_pkt_s(make_sync_packet('ACK', 512, 'D', i))
						time.sleep(0.2)
					#sync data --> occupied_carriers pilot_carriers pilot_symbols sync_word1 sync_word2 ofdm_fc ofdm_samp_rate ofdm_packet_len payload_mod
					self.update_ofdm_settings()
					print 'got sync'
					self.state = 'syncOK'
				except: #catch any error that might occour
					print 'error while recovering sync data'
					print 'going to sync again'
					self.state = 'syncNOK'

			else:
				print 'exiting'
				self.safe_quit()
				print 'fg stoped'
				sys.exit(0)
