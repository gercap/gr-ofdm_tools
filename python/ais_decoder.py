#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  ais_decoder.py
#  --> pipes audio stream from gnuradio flowgraph to gnuais-based decoder (http://www.aishub.net/aisdecoder-via-sound-card.html)
#  --> prints (stderr) or logs NMEA (to a file in /tmp ) sentences
#  Copyright 2014 germanocapela at gmail
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  


import sys, subprocess, tempfile, os, signal, time
from os.path import expanduser

from gnuradio import gr, gru, blocks

class ais_decoder(gr.hier_block2):
	def __init__(self, address="127.0.0.1", port=8888, verbose = True):
		
		gr.hier_block2.__init__(self, "ais_decoder",
								gr.io_signature(1, 1, gr.sizeof_short*1),
								gr.io_signature(0, 0, 0))
		
		decoder_path = gr.prefs().get_string('ais_decoder', 'path', 'ais_decoder')

		mode='fifo'
		buffered=True
		kill_on_del=True
		memory=None

		self.mode = mode
		self.kill_on_del = kill_on_del

		if mode == 'fifo':
			fifo_name = 'ais_fifo'
			self.tmpdir = tempfile.mkdtemp()
			self.filename = os.path.join(self.tmpdir, fifo_name)
			print self.filename
			try:
				os.mkfifo(self.filename)
			except OSError, e:
				print "Failed to create FIFO: %s" % e
				raise
		
		if verbose:
			print 'verbose mode'
			decoder_exec = [decoder_path + " -h " + str(address) + " -p "+ str(port) +" -a file"+" -f "+str(self.filename) + " -d"]
		else:
			print 'logging mode'
			start_dat = time.strftime("%y%m%d")
			start_tim = time.strftime("%H%M%S")

			home = expanduser("~")
			directory = home+'/sensing' + '-' + start_dat + '-' + time.strftime("%H%M") + '/'

			if not os.path.exists(directory):
				os.makedirs(directory)
			
			file_name = directory+'sdr_ais_log'+'-' + start_dat + '-' + start_tim
			print 'logging AIS NMEA sentences to', file_name
			
			decoder_exec = [decoder_path + " -h " + str(address) + " -p "+ str(port) +" -a file"+" -f "+str(self.filename) + " -d" + " 2>" + file_name]


		self.p = None
		#res = 0
		try:
			#res = subprocess.call(gp_exec)
			print decoder_exec
			self.p = subprocess.Popen(decoder_exec, shell=True)
		except Exception, e:
			print e
			raise

		self.file_sink = blocks.file_sink(gr.sizeof_short*1, self.filename)	# os.dup
		self.file_sink.set_unbuffered(not buffered)	# F

		self.connect(self, self.file_sink)
		
	def __del__(self):
		if self.p is not None:
			if self.kill_on_del:
				print "==> Killing ais_decoder..."
				os.kill(self.p.pid, signal.SIGTERM)

def main():
	
	return 0

if __name__ == '__main__':
	main()
