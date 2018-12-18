#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2018 germanocapela.
# 
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

import sys, subprocess, tempfile, os, signal, time
from os.path import expanduser

from gnuradio import gr, gru, blocks

class dump1090_interface(gr.hier_block2):
	def __init__(self, decoder_path, interactive=False, quiet=True):
		
		gr.hier_block2.__init__(self, "dump1090_interface",
								gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
								gr.io_signature(0, 0, 0))
		
		buffered=True
		kill_on_del=True

		self.kill_on_del = kill_on_del

		fifo_name = 'dump1090_fifo'
		self.tmpdir = tempfile.mkdtemp()
		self.filename = os.path.join(self.tmpdir, fifo_name)
		print self.filename
		try:
			os.mkfifo(self.filename)
		except OSError, e:
			print "Failed to create FIFO: %s" % e
			raise

		decoder_base_options = " --aggressive --net --modeac --net-beast --net-ro-port 31001 "
		decoder_exec = [decoder_path + decoder_base_options]

		if interactive:
			decoder_exec += ["--interactive"]

		if interactive:
			decoder_exec += ["--quiet"]

		decoder_exec += ["--ifile - <", self.filename]  #decoder_exec = ["cat", self.filename, "|"] + decoder_exec

		decoder_exec = [" ".join(decoder_exec)]

		self.p = None
		#res = 0
		try:
			#res = subprocess.call(gp_exec)
			print decoder_exec
			self.p = subprocess.Popen(decoder_exec, shell=True)
		except Exception, e:
			print e
			raise

		#from complex samples to interleaved UChar samples (as accepted from dump1090)
		self.mul_const1 = blocks.multiply_const_vff((1/0.008, ))
		self.mul_const0 = blocks.multiply_const_vff((1/0.008, ))
		self.interleave = blocks.interleave(gr.sizeof_char*1, 1)
		self.f_to_uchar1 = blocks.float_to_uchar()
		self.f_to_uchar0 = blocks.float_to_uchar()
		self.c_to_f = blocks.complex_to_float(1)
		self.add_const1 = blocks.add_const_vff((127, ))
		self.add_const0 = blocks.add_const_vff((127, ))

		self.file_sink = blocks.file_sink(gr.sizeof_char*1, self.filename, False)
		self.file_sink.set_unbuffered(not buffered)

		##################################################
		# Connections
		##################################################

		self.connect(self, (self.c_to_f, 0))

		self.connect((self.c_to_f, 0), (self.mul_const0, 0))
		self.connect((self.c_to_f, 1), (self.mul_const1, 0))
		self.connect((self.mul_const0, 0), (self.add_const0, 0))
		self.connect((self.mul_const1, 0), (self.add_const1, 0))
		self.connect((self.add_const0, 0), (self.f_to_uchar0, 0))
		self.connect((self.add_const1, 0), (self.f_to_uchar1, 0))
		self.connect((self.f_to_uchar0, 0), (self.interleave, 0))
		self.connect((self.f_to_uchar1, 0), (self.interleave, 1))
		self.connect((self.interleave, 0), (self.file_sink, 0))
		
	def __del__(self):
		if self.p is not None:
			if self.kill_on_del:
				print "==> Killing dump1090_interface..."
				os.kill(self.p.pid, signal.SIGTERM)

def main():
	return 0

if __name__ == '__main__':
	main()
