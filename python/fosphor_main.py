#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 germanocapela at gmail.com
# an alternative sink to the "main" function of gr-phosphor
# compile the code in gr-fosphor/lib/fosphor/
# then copy the executable "main" to /usr/bin/ with the name fosphor_main

 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import sys, subprocess, tempfile, os, signal

from gnuradio import gr, gru, blocks

class fosphor_main(gr.hier_block2):
	def __init__(self):
		
		gr.hier_block2.__init__(self, "fosphor_main",
								gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
								gr.io_signature(0, 0, 0))
		
		decoder_path = gr.prefs().get_string('fosphor_main', 'path', 'fosphor_main')

		mode='fifo'
		buffered=True
		kill_on_del=True
		memory=None
		
		self.mode = mode
		self.kill_on_del = kill_on_del
		
		if mode == 'fifo':
			fifo_name = 'fosphor_fifo'
			self.tmpdir = tempfile.mkdtemp()
			self.filename = os.path.join(self.tmpdir, fifo_name)
			print self.filename
			try:
				os.mkfifo(self.filename)
			except OSError, e:
				print "Failed to create FIFO: %s" % e
				raise
		
		decoder_exec = [decoder_path + ' ' + str(self.filename)]

		self.p = None
		#res = 0
		try:
			#res = subprocess.call(gp_exec)
			print decoder_exec
			self.p = subprocess.Popen(decoder_exec, shell=True)
		except Exception, e:
			print e
			raise

		self.file_sink = blocks.file_sink(gr.sizeof_gr_complex*1, self.filename)	# os.dup
		self.file_sink.set_unbuffered(not buffered)	# F

		self.connect(self, self.file_sink)
		
	def __del__(self):
		if self.p is not None:
			if self.kill_on_del:
				print "==> Killing fosphor..."
				os.kill(self.p.pid, signal.SIGTERM)
