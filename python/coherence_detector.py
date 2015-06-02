
	def set_subject_channels_outcome(self, subject_channels_outcome):
		self.subject_channels_outcome = subject_channels_outcome

	def get_subject_channels_outcome(self):
		return self.subject_channels_outcome

#ascii thread
class output_data(_threading.Thread):
	def __init__(self, data_queue0, sample_rate, tune_freq, N,
	 search_bw, output, subject_channels, get_subject_channels_outcome):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.data_queue0 = data_queue0
		self.N = N
		self.sample_rate = sample_rate
		self.tune_freq = tune_freq
		self.search_bw = search_bw
		self.output = output
		self.get_subject_channels_outcome = get_subject_channels_outcome

		self.Fr = float(self.sample_rate)/float(self.N) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.srch_bins = self.search_bw/self.Fr #binwidth for search
		self.ax_ch = np.array(range(-self.N/2, self.N/2)) * self.Fr + self.tune_freq #subject channels

		self.subject_channels = subject_channels
		self.idx_subject_channels = [0]*len(self.subject_channels)
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = find_nearest_index(self.ax_ch, channel)
			k += 1

		self.state = None
		self.keep_running = True #set to False to stop thread's main loop
		self.gnuplot = subprocess.Popen(["/usr/bin/gnuplot"], stdin=subprocess.PIPE)
		self.start()

	def run(self):
		if self.output == 't':
			while self.keep_running:
				data = self.data_queue0.get()
				left_column = np.array([['Freq [Hz]'],['Coherence']])
				table0 = np.vstack((self.ax_ch, data))
				table =  np.hstack((left_column, table0))
				table_plot = AsciiTable(np.ndarray.tolist(table.T))
				print '\n'
				print table_plot.table
				print '\n'
				sys.stdout.flush()

		if self.output == 'g':
			while self.keep_running:
				data = self.data_queue0.get()
				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'Spectral Coherence' \n")

				for i,j in zip(self.ax_ch, data):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				self.gnuplot.stdin.write("e\n")
				self.gnuplot.stdin.flush()

				print(chr(27) + "[2J")

		if self.output == 't_o':
			while self.keep_running:
				print 'Freq [Hz]			Outcome'
				print self.subject_channels
				print self.get_subject_channels_outcome()
				#for a, b in zip((self.subject_channels, self.get_subject_channels_outcome())):
				#	print a, '			', b
				print '\n'
				sys.stdout.flush()
				'''
				left_column = np.array([['Freq [Hz]'],['Outcome']])
				table0 = np.vstack((self.subject_channels, self.get_subject_channels_outcome))
				table =  np.hstack((left_column, table0))
				table_plot = AsciiTable(np.ndarray.tolist(table.T))
				print '\n'
				print table_plot.table
				print '\n'
				sys.stdout.flush()
				'''

		if self.output == 'g_o':
			while self.keep_running:
				self.gnuplot.stdin.write("set term dumb "+str(140)+" "+str(30)+ " \n")
				self.gnuplot.stdin.write("plot '-' using 1:2 title 'Spectral Coherence Outcome' \n")

				for i,j in zip(self.subject_channels, self.get_subject_channels_outcome):
					self.gnuplot.stdin.write("%f %f\n" % (i,j))

				self.gnuplot.stdin.write("e\n")
				self.gnuplot.stdin.flush()

				print(chr(27) + "[2J")


#queue wathcer to log statistics and max power per channel
class watcher(_threading.Thread):
	def __init__(self, rcvd_data, tune_freq, threshold,
		 search_bw, N, sample_rate, data_queue0, subject_channels, set_subject_channels_outcome, rate):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_data = rcvd_data

		self.tune_freq = tune_freq
		self.threshold = threshold
		self.search_bw = search_bw
		self.N = N
		self.sample_rate = sample_rate
		self.rate = rate

		self.Fr = float(self.sample_rate)/float(self.N) #freq resolution
		self.Fstart = self.tune_freq - self.sample_rate/2 #start freq
		self.Ffinish = self.tune_freq + self.sample_rate/2 #end freq
		self.srch_bins = int(self.search_bw/self.Fr/2) #binwidth for search
		self.ax_ch = np.array(range(-self.N/2, self.N/2)) * self.Fr + self.tune_freq #all channels

		# ax_ch - all channels available from bins
		# subject_channels - channels to analyze
		# idx_subject_channels - index CLOSEST subject_channels in ax_ch
		# subject_channels_outcome - outcome for subject_channels

		self.subject_channels = subject_channels
		self.n_chans = len(self.subject_channels)
		self.idx_subject_channels = [0]*self.n_chans
		k = 0
		for channel in subject_channels: 
			self.idx_subject_channels[k] = find_nearest_index(self.ax_ch, channel)
			k += 1

		self.set_subject_channels_outcome = set_subject_channels_outcome
		self.subject_channels_outcome = [0]*self.n_chans

		self.plc = np.array([0.0]*len(self.ax_ch))
		self.data_queue0 = data_queue0

		#file out
		start_dat = time.strftime("%y%m%d")
		start_tim = time.strftime("%H%M%S")
		
		self.coherence_path = './coherence_log' + '-' + start_dat + '-' + start_tim + '.log'
		self.coherence_file = open(self.coherence_path,'w')

		self.coherence_file.write('Freqs' + '\n')
		self.coherence_file.write(str(self.subject_channels) + '\n')
		self.coherence_file.write('Coherences at ' + str(self.rate) + ' measurements per second' + '\n')

		self.keep_running = True
		self.start()

	def run(self):
		while self.keep_running:
			msg = self.rcvd_data.delete_head()

			itemsize = int(msg
