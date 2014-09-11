#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 Germano Capela
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

from gnuradio import analog, blocks, digital, audio, filter, eng_notation, fft, gr, uhd, gru
from gnuradio.digital.utils import tagged_streams
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2
import gnuradio.gr.gr_threading as _threading
import osmosdr


import xmlrpclib, math, random, string
import numpy as np
from scipy import signal as sg
import matplotlib.pyplot as plots
import sys, time, os, struct, ast, signal
from subprocess import call

#defs
_seq_seed = 42
#_1024_occupied_carriers = (range(-460, -300) + range(-299, -150) + range(-149, 0) + range(1, 150) + range(151, 300) + range(301, 460),)
_1024_pilot_carriers = ((-300, -150, 150, 300,),)
#_128_occupied_carriers = (range(-52, -35) + range(-34, -20) + range(-19, 0) + range(1, 20) + range(21, 35) + range(36, 53),)
_128_pilot_carriers = ((-35, -20, 20, 35,),)
#_64_occupied_carriers = (range(-26, -21) + range(-20, -7) + range(-6, 0) + range(1, 7) + range(8, 21) + range(22, 27),)
_64_pilot_carriers = ((-21, -7, 7, 21,),)
_pilot_symbols = ((1, 1, 1, -1,),)

_sync_sync_word1 = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,1.42,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,1.42,0.0,-1.42,0.0,1.42,0.0,1.42,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
_sync_sync_word2 = [0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,(1+0j),(-1+0j),(-1+0j),(-1+0j),(1+0j),(-1+0j),(1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(-1+0j),(1+0j),0j,(1+0j),(-1+0j),(1+0j),(1+0j),(1+0j),(-1+0j),(1+0j),(1+0j),(1+0j),(-1+0j),(1+0j),(1+0j),(1+0j),(1+0j),(-1+0j),0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j,0j]
_sync_pilot_symbols = ((1, -1,),)
_sync_pilot_carriers = ((-13, 12,),)
_sync_occupied_carriers = ([-16, -15, -14, -12, -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15],)
_sync_fft_len = (len(_sync_sync_word1)+len(_sync_sync_word2))/2
_sync_cp_len = _sync_fft_len / 4

#PAPR calc
def calc_papr(measure):
	meanSquareValue = np.vdot(measure,np.transpose(measure))/len(measure)
	peakValue = max(measure*np.conjugate(measure))
	paprSymbol = peakValue/meanSquareValue
	return paprSymbol.real

#tcp client
def tcp_clt(ip, port, buff):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((ip, port))
	s.send('ok')
	rx = pickle.loads(s.recv(buff))
	print 'ok'
	s.close()
	time.sleep(0.001)
	return rx
	'''
	#RECEIVE SYNC DATA FROM TCP/IP
	IP = '193.136.223.117' #IP = '127.0.0.1' #
	PORT = 8888
	BUFF = 1024

	sync_data =  tcp_clt(IP, 8888, BUFF)
	sw1r = tcp_clt(IP, 8889, BUFF)
	sw1i = tcp_clt(IP, 8890, BUFF)
	sw2r = tcp_clt(IP, 8891, BUFF)
	sw2i = tcp_clt(IP, 8892, BUFF)

	occupied_carriers = sync_data[0]
	pilot_carriers = sync_data[1]
	pilot_symbols = sync_data[2]
	fc = sync_data[3]
	ofdm_samp_freq = sync_data[4]
	sync_word1 = np.array(map(complex, sw1r, sw1i))
	sync_word2 = np.array(map(complex, sw2r, sw2i))
	payload_modulation = sync_data[5]  # bpsk qpsk qam16
	'''

#tcp server
def tcp_srv(ip, port, buff, data):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind((ip, port))
	s.listen(1)

	conn, addr = s.accept()
	print 'Connection address:', addr

	while 1:
		rx = conn.recv(buff)
		if not rx: break
		print "received request 1:", rx
		conn.send(pickle.dumps(data))
	conn.close()
	'''
	IP = '193.136.223.117' #IP = '127.0.0.1' #
	PORT = 8888
	BUFF = 1024
	print 'Ready to send sync data to receiver via TCP/IP'

	tcp_srv(IP, 8888, BUFF, sd)
	tcp_srv(IP, 8889, BUFF, s_w1_r)
	tcp_srv(IP, 8890, BUFF, s_w1_i)
	tcp_srv(IP, 8891, BUFF, s_w2_r)
	tcp_srv(IP, 8892, BUFF, s_w2_i)
	print 'DONE sending sync data to receiver'   
	'''

#decompose complex number in real
def get_real(vect):
	vectr = [item.real for item in vect]
	return vectr

#decompose complex number in imag
def get_imag(vect):
	vecti = [item.imag for item in vect]
	return vecti

#range floats
def frange(x, y, jump):
	out =[]	
	while x < y:
		out.append(x)
		x += jump
	return out

#TD power estimate
def clc_power_time(vector):
	pt = float(sum((np.absolute(vector))**2))/len(vector)
	return pt

#computes welch based psd power
def clc_power_freq(vector, nFFT, Sf):
	n = len(vector)
	psd_fft = np.fft.fftshift(((np.absolute(np.fft.fft(vector, nFFT)))**2)/n)/Sf
	power_level = float(sum(psd_fft))
	return power_level

def xcorr(a, b, length):
	"""FFT based autocorrelation function, which is faster than numpy.correlate"""
	e = np.fft.fft(a, length);
	f = np.fft.fft(b, length);
	g = f * np.conj(e);
	h = np.fft.fftshift(np.fft.ifft(g, length));
	return np.abs(h[len(h)/2:])

def fac(data, length):
	b = np.abs(np.fft.fft(data, length))
	b = np.fft.fftshift(np.fft.fft(b, length))
	return np.abs(b[len(b)/2:])

def movingaverage(interval, window_size):
	window= np.ones(int(window_size))/float(window_size)
	return np.abs(np.convolve(interval, window, 'same'))

#computes fft based psd power
def src_power_fft(vector, npts, nFFT, Fr, Sf, bb_freqs, srch_bins):
	#win = np.hamming(npts)
	win = sg.flattop(npts)
	vector = vector * win
	psd_fft = np.fft.fftshift(((np.absolute(np.fft.fft(vector, nFFT)))**2)/npts)
	fft_axis = Sf/2*np.linspace(-1, 1, nFFT) #fft_axis = np.fft.fftshift(f)
	power_level_ch_fft = []

	f = bb_freqs[0]
	bin_n = (f+Sf/2)/Fr
	power_level = float(sum(psd_fft[0:int(bin_n+srch_bins/2)]))
	power_level_ch_fft.append(power_level)

	for f in bb_freqs[1:]:
		bin_n = (f+Sf/2)/Fr #freq = bin_n*Fr-Sf/2
		power_level = float(sum(psd_fft[int(bin_n-srch_bins/2):int(bin_n+srch_bins/2)]))
		power_level_ch_fft.append(power_level)
	return psd_fft, fft_axis, power_level_ch_fft

#computes autocorrelation / fft based psd power
def src_power_autocorrelation(vector, npts, nFFT, Fr, Sf, bb_freqs, srch_bins):
	auto = np.correlate(vector, vector, 'same')
	psd = np.abs(fft.fftshift(fft.fft(autocorr_a, nFFT)))/npts/Sf
	axis = Sf/2*np.linspace(-1, 1, nFFT) #fft_axis = np.fft.fftshift(f)
	power_level_ch_fft = []

	f = bb_freqs[0]
	bin_n = (f+Sf/2)/Fr
	power_level = float(sum(psd[0:int(bin_n+srch_bins/2)]))
	power_level_ch_fft.append(power_level)

	for f in bb_freqs[1:]:
		bin_n = (f+Sf/2)/Fr #freq = bin_n*Fr-Sf/2
		power_level = float(sum(psd[int(bin_n-srch_bins/2):int(bin_n+srch_bins/2)]))
		power_level_ch_fft.append(power_level)
	return psd, axis, power_level_ch_fft

#computes welch based psd power
def src_power_welch(vector, npts, nFFT, Fr, Sf, bb_freqs, srch_bins):
	welch_axis, psd_welch = sg.welch(vector, window='flattop', fs = Sf, nperseg= nFFT, nfft = nFFT)
	psd_welch_aligned = np.fft.fftshift(psd_welch)
	welch_axis_aligned = np.fft.fftshift(welch_axis)
	power_level_ch_welch = []

	#1st slice must be calcd separately (indexes)
	f = bb_freqs[0]
	bin_n = (f+Sf/2)/Fr
	power_level = float(sum(psd_welch_aligned[0:int(bin_n+srch_bins/2)]))
	power_level_ch_welch.append(power_level)

	for f in bb_freqs[1:]:
		bin_n = (f+Sf/2)/Fr #freq = bin_n*Fr-Sf/2
		power_level = float(sum(psd_welch_aligned[int(bin_n-srch_bins/2):int(bin_n+srch_bins/2)]))
		power_level_ch_welch.append(power_level)
	return psd_welch_aligned, welch_axis_aligned, power_level_ch_welch

#determine usefull carriers
def _get_active_carriers(fft_len, occupied_carriers, pilot_carriers):
	""" Returns a list of all carriers that at some point carry data or pilots. """
	active_carriers = list()
	for carrier in list(occupied_carriers[0]) + list(pilot_carriers[0]):
		if carrier < 0:
			carrier += fft_len
		active_carriers.append(carrier)
	return active_carriers

#generate shmidl and cox sync word 1
def _make_sync_word1(fft_len, occupied_carriers, pilot_carriers):
    """ Creates a random sync sequence for fine frequency offset and timing
    estimation. This is the first of typically two sync preamble symbols
    for the Schmidl & Cox sync algorithm.
    The relevant feature of this symbols is that every second sub-carrier
    is zero. In the time domain, this results in two identical halves of
    the OFDM symbols.
    Symbols are always BPSK symbols. Carriers are scaled by sqrt(2) to keep
    total energy constant.
    Carrier 0 (DC carrier) is always zero. If used, carrier 1 is non-zero.
    This means the sync algorithm has to check on odd carriers!
    """
    active_carriers = _get_active_carriers(fft_len, occupied_carriers, pilot_carriers)
    np.random.seed(_seq_seed)
    #bpsk = {0: np.sqrt(2), 1: -np.sqrt(2)}
    bpsk = {0: 1.42, 1: -1.42}
    sw1 = [bpsk[np.random.randint(2)]  if x in active_carriers and x % 2 else 0 for x in range(fft_len)]
    return np.fft.fftshift(sw1)

#generate shmidl and cox sync word 2
def _make_sync_word2(fft_len, occupied_carriers, pilot_carriers):
    """ Creates a random sync sequence for coarse frequency offset and channel
    estimation. This is the second of typically two sync preamble symbols
    for the Schmidl & Cox sync algorithm.
    Symbols are always BPSK symbols.
    """
    active_carriers = _get_active_carriers(fft_len, occupied_carriers, pilot_carriers)
    np.random.seed(_seq_seed)
    bpsk = {0: 1, 1: -1}
    sw2 = [bpsk[np.random.randint(2)] if x in active_carriers else 0 for x in range(fft_len)]
    sw2[0] = 0j
    return np.fft.fftshift(sw2)

#plt data from flowgraph
def fft_plot(flowgraph, fc, nfft):
	vect_s = flowgraph.get_probe_vector_levels()
	vector = map(complex, vect_s[0:len(vect_s)/2], vect_s[len(vect_s)/2:])
	npts = flowgraph.get_vector_probe_pts()
	Sf = flowgraph.get_samp_rate()
	psd_fft = np.fft.fftshift(((np.absolute(np.fft.fft(vector, nfft)))**2)/npts)/Sf
	fft_axis = Sf/2*np.linspace(-1, 1, nfft)

	fig1 = plots.figure()
	plots.plot([item+fc for item in fft_axis],[10*math.log10(item+1e-20) for item in psd_fft])
	plots.xlabel('Frequency [Hz]')
	plots.ylabel('PSD [dB/Hz]')
	plots.title('FFT method PSD', fontsize=12)
	return

#plt data from flowgraph
def fft_plot_dB(data, Sf, fc, nfft):

	npts = len(data)
	psd_fft = np.fft.fftshift(((np.absolute(np.fft.fft(data, nfft)))**2)/(npts*Sf))
	fft_axis = Sf/2*np.linspace(-1, 1, nfft)

	return [item+fc for item in fft_axis], [10*math.log10(item+1e-20) for item in psd_fft]

def welch_plot_dB(data, Sf, fc, nfft):
	welch_axis, psd_welch = sg.welch(data, fs = Sf, nperseg= nfft, nfft = nfft)
	psd_welch_aligned = np.fft.fftshift(psd_welch)
	welch_axis_aligned = np.fft.fftshift(welch_axis)

	return [item+fc for item in welch_axis_aligned], [10*math.log10(item+1e-20) for item in psd_welch_aligned]

def fft_plot_lin(data, Sf, fc, nfft):
	npts = len(data)
	psd_fft = np.fft.fftshift(((np.absolute(np.fft.fft(data, nfft)))**2)/npts)/Sf
	fft_axis = Sf/2*np.linspace(-1, 1, nfft)

	return [item+fc for item in fft_axis], psd_fft

def td_power_estimate(vector, Sf):
	pt = float(sum((np.absolute(vector))**2))/Sf
	return pt

def welch_power_estimate(vector, nFFT, Sf):
	welch_axis, psd_welch = sg.welch(vector, fs = Sf, nperseg= nFFT, nfft = nFFT)
	psd_welch_aligned = np.fft.fftshift(psd_welch)
	power_level = float(sum(psd_welch_aligned))
	return power_level

#enforce spectrum rules generating occupied carriers, pilots and synch words
def spectrum_enforcer(fft_len, spectrum_constraint_fft, lobe_len):

	# Dynamic pilot carrier allocation
	usable = range(-fft_len/2, fft_len/2, 1)
	# Remove DC carrier
	usable.remove(0)
	# Remove side lobes
	del usable[0:lobe_len]
	del usable[-lobe_len:] 

	# Remove constrained carriers
	for carr in spectrum_constraint_fft:
		if carr in usable: usable.remove(carr)

	# Assign pilot carriers
	space = len(usable)/8
	middle = len(usable)/2
	p1 = usable[middle-3*space]
	p2 = usable[middle-space]
	p3 = usable[middle+space]
	p4 = usable[middle+3*space]
	pilot_carriers = ((p1, p2, p3, p4),)

	# Remove pilots from usable
	for carr in pilot_carriers[0]: usable.remove(carr)
	occupied_carriers = ((usable),)

	sync_word1 = _make_sync_word1(fft_len, occupied_carriers, pilot_carriers)
	sync_word2 = _make_sync_word2(fft_len, occupied_carriers, pilot_carriers)

	return occupied_carriers, pilot_carriers, _pilot_symbols, sync_word1.tolist(), sync_word2.tolist()
    #return occupied_carriers, pilot_carriers, _pilot_symbols, sync_word1, sync_word2

'''
def spectrum_enforcer(fft_len, spectrum_constraint_fft, lobe_len):
    st = -fft_len/2+lobe_len
    dc = 0
    fn = fft_len/2+1-lobe_len

    # Dynamic pilot carrier allocation
    usable = range(-fft_len/2, fft_len/2, 1)
    for carr in spectrum_constraint_fft:
		if carr in usable: usable.remove(carr)
    space = len(usable)/8
    middle = len(usable)/2
    pilot_carriers = ((usable[middle-space], usable[middle-2*space], usable[middle+space], usable[middle+2*space],),)
    
    # 4 pilot carrier structure
    occupied_carriers = (
    (range(st, pilot_carriers[0][0]) 
    + range(pilot_carriers[0][0]+1, pilot_carriers[0][1]) 
    + range(pilot_carriers[0][1]+1, 0) 
    + range(1, pilot_carriers[0][2]) 
    + range(pilot_carriers[0][2]+1, pilot_carriers[0][3]) 
    + range(pilot_carriers[0][3]+1, fn)),)
    
    for carr in spectrum_constraint_fft:
		if carr in occupied_carriers[0]: occupied_carriers[0].remove(carr)
    if 0 in occupied_carriers[0]: occupied_carriers[0].remove(0)
        
    sync_word1 = _make_sync_word1(fft_len, occupied_carriers, pilot_carriers)
    sync_word2 = _make_sync_word2(fft_len, occupied_carriers, pilot_carriers)
    
    return occupied_carriers, pilot_carriers, _pilot_symbols, sync_word1, sync_word2
'''

#find nearest value in numpy array
def find_nearest_a(array,value):
	idx = (np.abs(array-value)).argmin()
	return array[idx]

#find nearest value in python list
def find_nearest_l(lst,value):
	return min(lst, key=lambda x:abs(x-value))

#convert Hz to FFT bins
def spectrum_translator(spectrum_constraint_hz, fc, sf, fft_len, canc_bins):
	spectrum_constraint_fft = []
	spectrum_fft = np.linspace(-fft_len/2, fft_len/2-1, fft_len) #full constrain    
	Fr = float(sf)/float(fft_len) #Frequency resolution (Hz/fftbin)
	spectrum_hz = [item*Fr+fc for item in spectrum_fft]

	for f in spectrum_constraint_hz:
		f_remove = find_nearest_l(spectrum_hz, f)
		bin_remove = (f_remove-fc)/Fr
		x = 0
		while x < canc_bins/2:
			spectrum_constraint_fft.append(bin_remove+x)
			spectrum_constraint_fft.append(bin_remove-x)
			x += 1 
	return spectrum_constraint_fft

def fast_spectrum_scan(vct_sample, fc, channel_rate, srch_bw, n_fft, samp_rate, method, thr_leveler, show_plot):

	npts = len(vct_sample)
	if n_fft == 0: nFFT = int(2**math.ceil(math.log(npts,2))) #nr points fft
	else: nFFT = n_fft

	Fr = float(samp_rate)/float(nFFT)
	Fstart = fc - samp_rate/2
	Ffinish = fc + samp_rate/2

	print 'Scanning...'
	bb_freqs = frange(-samp_rate/2, samp_rate/2, channel_rate)
	srch_bins = srch_bw/Fr

	if method == 'welch':
		###-Welch Method-###
		psd, axis, power_level_ch = src_power_welch(vct_sample, npts, nFFT, Fr, samp_rate, bb_freqs, srch_bins)

	if method == 'fft':
		###- FFT Method-###
		psd, axis, power_level_ch = src_power_fft(vct_sample, npts, nFFT, Fr, samp_rate, bb_freqs, srch_bins)

	axis = [ax+fc for ax in axis]
	ax_ch = frange(Fstart, Ffinish, channel_rate)

	avg_power = np.average (power_level_ch)
	min_power = np.amin (power_level_ch)
	max_power = np.amax (power_level_ch)
	print 'min power', 10*math.log10(min_power+1e-20)
	print 'max power', 10*math.log10(max_power+1e-20) 
	print 'average power', 10*math.log10(avg_power+1e-20)

	thr = min_power * thr_leveler
	print 'decision threshold', 10*math.log10(thr+1e-20)

	# test detection threshold
	pwr = []
	spectrum_constraint_hz = []
	i = 0
	for item in power_level_ch:
		if item>thr:
			pwr.append(1)
			spectrum_constraint_hz.append(ax_ch[i])
		else:
			pwr.append(0.01)
		i += 1

	if show_plot:
		#plots.figure(2)
		#plots.plot(welch_axis,[10*math.log10(item) for item in psd_welch])

		f1, axarr1 = plots.subplots(3, sharex=True)
		axarr1[0].plot(axis,[10*math.log10(item+1e-20) for item in psd])
		axarr1[0].set_title('PSD Estimate using ' + method + '\'s method')
		axarr1[0].set_ylabel('PSD [dB/Hz]')

		axarr1[1].bar(ax_ch, [10*math.log10(item+1e-20) for item in power_level_ch[0:len(ax_ch)]], srch_bw/2, align = 'center')
		axarr1[1].set_title('Power by Channel')
		axarr1[1].set_ylabel('Power [dB]')

		axarr1[2].bar(ax_ch, pwr[0:len(ax_ch)], srch_bw/2, align = 'center')
		axarr1[2].set_title('Decision')
		axarr1[2].set_ylabel('Occupied/Not occupied')
		axarr1[2].set_xlabel('Frequency [Hz]')
		#plots.show()

	return spectrum_constraint_hz


def spectrum_scan(Fstart, Ffinish, channel_rate, srch_bw, n_fft, rf_source, receiver, method, thr_leveler, t_wait, show_plot):

	t = t_wait #0.2 # for lower sampling rates, the scanner must fill completely the vector...

	###-SAMP. FREQ. AND SAMPLES-###
	Sf = receiver.get_samp_rate()
	Fcs =  frange(Fstart+Sf/2, Ffinish, Sf)
	if len(Fcs)<1: #IN CASE SCANNING SR < TX SAMPLING RATE
		Fcs = []
		Fcs.append((Fstart + Ffinish)/2)
	npts = receiver.get_vector_probe_pts() #nr point each observation

	if n_fft == 0: nFFT = int(2**math.ceil(math.log(npts,2))) #nr points fft
	else: nFFT = n_fft

	Fr = float(Sf)/float(nFFT)

	print 'Gathering data...'
	vector_set = []

	for f in Fcs:
		try: rf_source.set_center_freq(f, 0)
		except: None
		print 'Tunning to:', f
		time.sleep(t)
		#vect_s = receiver.get_probe_vector_levels()
		#vector = map(complex, vect_s[0:len(vect_s)/2], vect_s[len(vect_s)/2:])   #real and imaginary are received concatenated
		vector = receiver.get_probe_vector_level()
		vector_set.append(vector)

	print 'Scanning...'
	bb_freqs = frange(-Sf/2, Sf/2, channel_rate)
	srch_bins = srch_bw/Fr

	psd_set = []
	axis_set = []
	power_level_ch_set = []

	if method == 'welch':
		for vt in vector_set:
			###-Welch Method-###
			psd, axis, power_level_ch = src_power_welch(vt, npts, nFFT, Fr, Sf, bb_freqs, srch_bins)
			psd_set.append(psd)
			axis_set.append(axis)
			power_level_ch_set.append(power_level_ch)

	if method == 'fft':
		for vt in vector_set:
			###- FFT Method-###
			psd, axis, power_level_ch = src_power_fft(vt, npts, nFFT, Fr, Sf, bb_freqs, srch_bins)
			psd_set.append(psd)
			axis_set.append(axis)
			power_level_ch_set.append(power_level_ch)

	psd = []
	power_level_ch = []
	psd = [item for sublist in psd_set for item in sublist]
	power_level_ch = [item for sublist in power_level_ch_set for item in sublist]
	axis = []	#each set of bb frequencies must be adjust to the specific tune freq

	j = 0
	for el in axis_set:
		for x in el:
			axis.append(x+Fcs[j])
		j += 1

	#free memory
	vector_set = None
	psd_set = None
	axis_set = None
	power_level_ch_set = None

	ax_ch = frange(Fstart, Ffinish, channel_rate)

	avg_power = np.average (power_level_ch)
	min_power = np.amin (power_level_ch)
	max_power = np.amax (power_level_ch)
	print 'min power', 10*math.log10(min_power+1e-20)
	print 'max power', 10*math.log10(max_power+1e-20) 
	print 'average power', 10*math.log10(avg_power+1e-20)

	thr = min_power * thr_leveler
	print 'decision threshold', 10*math.log10(thr+1e-20)

	# test detection threshold
	pwr = []
	spectrum_constraint_hz = []
	i = 0
	for item in power_level_ch:
		if item>thr:
			pwr.append(1)
			spectrum_constraint_hz.append(ax_ch[i])
		else:
			pwr.append(0.01)
		i += 1

	if show_plot:
		#plots.figure(2)
		#plots.plot(welch_axis,[10*math.log10(item) for item in psd_welch])

		f1, axarr1 = plots.subplots(3, sharex=True)
		axarr1[0].plot(axis,[10*math.log10(item+1e-20) for item in psd])
		axarr1[0].set_title('PSD Estimate using ' + method + '\'s method')
		axarr1[0].set_ylabel('PSD [dB/Hz]')

		axarr1[1].bar(ax_ch, [10*math.log10(item+1e-20) for item in power_level_ch[0:len(ax_ch)]], srch_bw/2, align = 'center')
		axarr1[1].set_title('Power by Channel')
		axarr1[1].set_ylabel('Power [dB]')

		axarr1[2].bar(ax_ch, pwr[0:len(ax_ch)], srch_bw/2, align = 'center')
		axarr1[2].set_title('Decision')
		axarr1[2].set_ylabel('Occupied/Not occupied')
		axarr1[2].set_xlabel('Frequency [Hz]')
		#plots.show()

	return spectrum_constraint_hz

#complete spectrum scanner hier block
class spectrum_probe(gr.hier_block2):

	def __init__(self, t, sr):
		gr.hier_block2.__init__(self, "spectrum_probe",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))

		##################################################
		# Variables
		self.t_obs = t_obs = t
		self.samp_rate = samp_rate = sr

		self.vector_probe_pts = vector_probe_pts = int(2**math.ceil(math.log(samp_rate*t_obs,2)))

		# Blocks
		self.stream_to_vector_probe = blocks.stream_to_vector(gr.sizeof_gr_complex*1, vector_probe_pts)
		self.probe_vector = blocks.probe_signal_vc(vector_probe_pts)

		# Connections
		self.connect(self, self.stream_to_vector_probe, self.probe_vector)

	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate

	def get_vector_probe_pts(self):
		return self.vector_probe_pts

	def get_t_obs(self):
		return self.t_obs

	def get_probe_vector_level(self):
		return self.probe_vector.level()

	def get_probe_vector_levels(self):
		vect = self.probe_vector.level()
		vectr = [item.real for item in vect]
		vecti = [item.imag for item in vect]
		return (vectr+vecti)

#Hier block complete and reconfigurable OFDM transmitter
class ofdm_transmit_path(gr.hier_block2): 
	def __init__(self, sf, oc, pc, ps, sw1, sw2, cp, pl, ro, payload_mod, scramble, put_crc):
		gr.hier_block2.__init__(self, "transmit_path",
				gr.io_signature(0, 0, 0),
				gr.io_signature(1, 1, gr.sizeof_gr_complex))

		##################################################
		# Variables
		##################################################
		self.sync_word2 = sync_word2 = sw2
		self.sync_word1 = sync_word1 = sw1
		self.pilot_symbols = pilot_symbols = ps
		self.pilot_carriers = pilot_carriers = pc
		self.occupied_carriers = occupied_carriers = oc
		self.fft_len = fft_len = (len(sync_word1)+len(sync_word2))/2

		#modulation
		if payload_mod == 'qpsk':
			self.payload_mod = payload_mod = digital.constellation_qpsk()
		elif payload_mod == 'qam16':
			self.payload_mod = payload_mod = digital.qam.qam_constellation(16,True,'none',False)
		elif payload_mod == 'bpsk':
			self.payload_mod = payload_mod = digital.constellation_bpsk()

		self.header_mod = header_mod = digital.constellation_bpsk()

		self.cp_len = cp_len = cp
		self.samp_rate = samp_rate = sf
		self.rolloff = rolloff = ro
		self.packet_len = packet_len = pl

		self.vector_probe_pts = vector_probe_pts = int(2**math.ceil(math.log(samp_rate*0.001,2)))

		self.packet_length_tag_key = packet_length_tag_key = "packet_len"
		self.length_tag_key = length_tag_key = "frame_len"
		self.payload_equalizer = payload_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, payload_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols, 1)
		self.header_formatter = header_formatter = digital.packet_header_ofdm(occupied_carriers, n_syms=1, len_tag_key=packet_length_tag_key, frame_len_tag_key=length_tag_key, bits_per_header_sym=header_mod.bits_per_symbol(), bits_per_payload_sym=payload_mod.bits_per_symbol(), scramble_header=True)
		self.header_equalizer = header_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, header_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols)

		# initialize the message queues
		self.source_queue = gr.msg_queue()

		self.scramble = scramble

		##################################################
		# Blocks
		self.msg_source = blocks.message_source(gr.sizeof_char*1, self.source_queue)

		self.fft_txpath = fft.fft_vcc(fft_len, False, (()), True, 1)
		#(self.fft_txpath).set_min_output_buffer(16000)
		self.packet_headergenerator_txpath = digital.packet_headergenerator_bb(header_formatter.formatter())
		self.cyclic_prefixer_txpath = digital.ofdm_cyclic_prefixer(fft_len, fft_len+cp_len, rolloff, packet_length_tag_key)
		#(self.cyclic_prefixer_txpath).set_min_output_buffer(32000)
		self.carrier_allocator_txpath = digital.ofdm_carrier_allocator_cvc(fft_len, occupied_carriers, pilot_carriers, pilot_symbols, (sync_word1, sync_word2), packet_length_tag_key)
		#(self.carrier_allocator_txpath).set_min_output_buffer(16000)
		self.crc32_txpath = digital.crc32_bb(False, packet_length_tag_key)
		self.chunks_to_symbols_header_txpath = digital.chunks_to_symbols_bc((header_mod.points()), 1)
		self.chunks_to_symbols_payload_txpath = digital.chunks_to_symbols_bc((payload_mod.points()), 1)
		self.tagged_stream_mux_txpath = blocks.tagged_stream_mux(gr.sizeof_gr_complex*1, packet_length_tag_key, 0)
		#(self.tagged_stream_mux_txpath).set_min_output_buffer(16000)
		self.stream_to_tagged_stream_txpath = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, packet_len, packet_length_tag_key)
		self.repack_bits_txpath = blocks.repack_bits_bb(8, payload_mod.bits_per_symbol(), packet_length_tag_key, False)
		self.tag_gate_txpath = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
		self.multiply_const_txpath = blocks.multiply_const_vcc((0.01, ))

		#Scrambler
		self.payload_scrambler = digital.additive_scrambler_bb(0x8a, 0x7f, 7, 0, bits_per_byte=8, reset_tag_key=self.packet_length_tag_key)

		#probes
		self.s2v = blocks.stream_to_vector(gr.sizeof_gr_complex*1, vector_probe_pts)
		self.probe = blocks.probe_signal_vc(vector_probe_pts)

		##################################################
		# Connections
		#Data source
		self.connect(self.msg_source, self.stream_to_tagged_stream_txpath)

		if put_crc:
			self.connect(self.stream_to_tagged_stream_txpath, self.crc32_txpath, (self.packet_headergenerator_txpath, 0))
			#Scrambler here --> crc, payload_scrambler, payload_unpack
			if self.scramble:
				self.connect(self.crc32_txpath, self.payload_scrambler, self.repack_bits_txpath)
			else:#SCRAMBLER OFF!!
				self.connect(self.crc32_txpath, self.repack_bits_txpath)
		else:
			self.connect(self.stream_to_tagged_stream_txpath, self.packet_headergenerator_txpath)
			#Scrambler here --> crc, payload_scrambler, payload_unpack
			if self.scramble:
				self.connect(self.stream_to_tagged_stream_txpath, self.payload_scrambler, self.repack_bits_txpath)
			else:#SCRAMBLER OFF!!
				self.connect(self.stream_to_tagged_stream_txpath, self.repack_bits_txpath)

		self.connect((self.chunks_to_symbols_payload_txpath, 0), (self.tagged_stream_mux_txpath, 1))
		self.connect((self.chunks_to_symbols_header_txpath, 0), (self.tagged_stream_mux_txpath, 0))
		self.connect((self.fft_txpath, 0), (self.cyclic_prefixer_txpath, 0))
		self.connect((self.carrier_allocator_txpath, 0), (self.fft_txpath, 0))
		self.connect((self.packet_headergenerator_txpath, 0), (self.chunks_to_symbols_header_txpath, 0))
		self.connect((self.tagged_stream_mux_txpath, 0), (self.carrier_allocator_txpath, 0))
		self.connect((self.repack_bits_txpath, 0), (self.chunks_to_symbols_payload_txpath, 0))

		self.connect((self.cyclic_prefixer_txpath, 0), (self.tag_gate_txpath, 0))
		self.connect((self.tag_gate_txpath, 0), (self.multiply_const_txpath, 0))

		# !!! OUTPUT !!!
		self.connect(self.multiply_const_txpath, self)

		#probes connection

	def connect_ouput_probe(self):
		self.connect(self.multiply_const_txpath, self.s2v, self.probe)

	def disconnect_ouput_probe(self):
		self.disconnect(self.multiply_const_txpath, self.s2v, self.probe)

	def get_probe_vector_levels(self):
		vect = self.probe.level()
		vectr = [item.real for item in vect]
		vecti = [item.imag for item in vect]
		return (vectr+vecti)

	def get_vector_probe_pts(self):
		return self.vector_probe_pts

	def send_pkt_s(self, payload='', eof=False):
		if eof:
			msg = gr.message(1) # tell self._pkt_input we're not sending any more packets
		else:
			msg = gr.message_from_string(payload)
		self.source_queue.insert_tail(msg)

#Hier block complete and reconfigurable OFDM receiver
class ofdm_receive_path(gr.hier_block2):
	def __init__(self, sf, oc, pc, ps, sw1, sw2, cp, payload_mod, debug, rx_callback, scramble, ext_crc):
		gr.hier_block2.__init__(self, "ofdm_receive_path",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))

		# Variables
		self.sync_word2 = sync_word2 = sw2
		self.sync_word1 = sync_word1 = sw1
		self.pilot_symbols = pilot_symbols = ps
		self.pilot_carriers = pilot_carriers = pc
		self.occupied_carriers = occupied_carriers = oc
		self.fft_len = fft_len = (len(sync_word1)+len(sync_word2))/2

		#payload modulation
		if payload_mod == 'qpsk':
			self.payload_mod = payload_mod = digital.constellation_qpsk()
		elif payload_mod == 'qam16':
			self.payload_mod = payload_mod = digital.qam.qam_constellation(16,True,'none',False)
		elif payload_mod == 'bpsk':
			self.payload_mod = payload_mod = digital.constellation_bpsk()

		#header modulation
		self.header_mod = header_mod = digital.constellation_bpsk()

		self.cp_len = cp_len = cp
		self.samp_rate = samp_rate = sf

		self.packet_length_tag_key = packet_length_tag_key = "packet_len"
		self.length_tag_key = length_tag_key = "frame_len"
		self.payload_equalizer = payload_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, payload_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols, 1)
		self.header_formatter = header_formatter = digital.packet_header_ofdm(occupied_carriers, n_syms=1, len_tag_key=packet_length_tag_key, frame_len_tag_key=length_tag_key, bits_per_header_sym=header_mod.bits_per_symbol(), bits_per_payload_sym=payload_mod.bits_per_symbol(), scramble_header=True)
		self.header_equalizer = header_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, header_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols)

		# initialize the message queue
		self.sink_queue = gr.msg_queue()
		self.rx_callback = rx_callback

		self.debug = debug
		self.scramble = scramble

		##################################################
		self.fft_payload_rxpath = fft.fft_vcc(fft_len, True, (), True, 1)
		self.fft_head_rxpath = fft.fft_vcc(fft_len, True, (()), True, 1)
		self.packet_headerparser_rxpath = digital.packet_headerparser_b(header_formatter.base())
		self.ofdm_sync_sc_rxpath = digital.ofdm_sync_sc_cfb(fft_len, cp_len, False)
		self.ofdm_serializer_payload_rxpath = digital.ofdm_serializer_vcc(fft_len, occupied_carriers, length_tag_key, packet_length_tag_key, 1, "", True)
		self.ofdm_serializer_header_rxpath = digital.ofdm_serializer_vcc(fft_len, occupied_carriers, length_tag_key, "", 0, "", True)
		self.ofdm_frame_equalizer_head_rxpath = digital.ofdm_frame_equalizer_vcvc(header_equalizer.base(), cp_len, length_tag_key, True, 1)
		self.ofdm_frame_equalizer_payload_rxpath = digital.ofdm_frame_equalizer_vcvc(payload_equalizer.base(), cp_len, length_tag_key, True, 0)
		self.digital_ofdm_chanest_vcvc_rxpath = digital.ofdm_chanest_vcvc((sync_word1), (sync_word2), 1, 0, 3, False)
		self.digital_header_payload_demux_rxpath = digital.header_payload_demux(3, fft_len, cp_len, length_tag_key, "", True, gr.sizeof_gr_complex)
		self.constellation_decoder_head_rxpath = digital.constellation_decoder_cb(header_mod.base())
		self.constellation_decoder_payload_rxpath = digital.constellation_decoder_cb(payload_mod.base())
		self.tag_debug_rxpath = blocks.tag_debug(gr.sizeof_char*1, "Rx Bytes", ""); self.tag_debug_rxpath.set_display(True)
		self.blocks_repack_bits_bb_0_rxpath = blocks.repack_bits_bb(payload_mod.bits_per_symbol(), 8, packet_length_tag_key, True)
		self.blocks_multiply_xx_rxpath = blocks.multiply_vcc(1)
		#self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vcc((0.01, ))
		self.delay_rxpath = blocks.delay(gr.sizeof_gr_complex*1, fft_len+cp_len)
		self.analog_frequency_modulator_fc_rxpath = analog.frequency_modulator_fc(-2.0/fft_len)    
		# Descrambler
		self.payload_descrambler = digital.additive_scrambler_bb(0x8a, 0x7f, 7, 0, bits_per_byte=8, reset_tag_key=self.packet_length_tag_key)
		self.crc32_rxpath = digital.crc32_bb(True, packet_length_tag_key)

		#data sink!
		self.final_sink = blocks.message_sink(gr.sizeof_char*1, self.sink_queue, False)     

		# Connections
		#RF LINK <<>>
		self.connect(self, (self.delay_rxpath, 0))
		self.connect(self, (self.ofdm_sync_sc_rxpath, 0))

		self.connect((self.blocks_multiply_xx_rxpath, 0), (self.digital_header_payload_demux_rxpath, 0))
		self.connect((self.analog_frequency_modulator_fc_rxpath, 0), (self.blocks_multiply_xx_rxpath, 0))
		self.connect((self.delay_rxpath, 0), (self.blocks_multiply_xx_rxpath, 1))
		self.connect((self.ofdm_sync_sc_rxpath, 0), (self.analog_frequency_modulator_fc_rxpath, 0))
		self.connect((self.digital_header_payload_demux_rxpath, 1), (self.fft_payload_rxpath, 0))
		self.connect((self.digital_header_payload_demux_rxpath, 0), (self.fft_head_rxpath, 0))
		self.connect((self.constellation_decoder_head_rxpath, 0), (self.packet_headerparser_rxpath, 0))
		self.connect((self.ofdm_serializer_header_rxpath, 0), (self.constellation_decoder_head_rxpath, 0))
		self.connect((self.ofdm_sync_sc_rxpath, 1), (self.digital_header_payload_demux_rxpath, 1))
		self.connect((self.fft_head_rxpath, 0), (self.digital_ofdm_chanest_vcvc_rxpath, 0))
		self.connect((self.digital_ofdm_chanest_vcvc_rxpath, 0), (self.ofdm_frame_equalizer_head_rxpath, 0))
		self.connect((self.ofdm_frame_equalizer_head_rxpath, 0), (self.ofdm_serializer_header_rxpath, 0))
		self.connect((self.ofdm_frame_equalizer_payload_rxpath, 0), (self.ofdm_serializer_payload_rxpath, 0))
		self.connect((self.fft_payload_rxpath, 0), (self.ofdm_frame_equalizer_payload_rxpath, 0))
		self.connect((self.constellation_decoder_payload_rxpath, 0), (self.blocks_repack_bits_bb_0_rxpath, 0))
		self.connect((self.ofdm_serializer_payload_rxpath, 0), (self.constellation_decoder_payload_rxpath, 0))

		if ext_crc:
			# Descrambler here --> repack, descrambler, crc
			if self.scramble:
				self.connect(self.blocks_repack_bits_bb_0_rxpath, self.payload_descrambler, self.crc32_rxpath, self.final_sink)
			else:#DESCRAMBLER OFF!!
				self.connect(self.blocks_repack_bits_bb_0_rxpath, self.crc32_rxpath, self.final_sink)
			if self.debug: self.connect(self.crc32_rxpath, self.tag_debug_rxpath)
		else:
			# Descrambler here --> repack, descrambler, crc
			if self.scramble:
				self.connect(self.blocks_repack_bits_bb_0_rxpath, self.payload_descrambler, self.final_sink)
			else:#DESCRAMBLER OFF!!
				self.connect(self.blocks_repack_bits_bb_0_rxpath, self.final_sink)
			if self.debug: self.connect(self.blocks_repack_bits_bb_0_rxpath, self.tag_debug_rxpath)

		##################################################
		# Asynch Message Connections
		self.msg_connect(self.packet_headerparser_rxpath, "header_data", self.digital_header_payload_demux_rxpath, "header_data")

		self._watcher = _queue_watcher_thread_mod(self.sink_queue, self.rx_callback) # mod = no CRC check

	def get_samp_rate(self):
		return self.samp_rate

#Hier OFDM based synchronization receiver
class ofdm_receive_path_light(gr.hier_block2):
	def __init__(self, sf, oc, pc, ps, sw1, sw2, cp, t_obs, payload_mod, debug, rx_callback, scramble):
		gr.hier_block2.__init__(self, "sync_receive_path_light",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))

		# Variables
		self.sync_word2 = sync_word2 = sw2
		self.sync_word1 = sync_word1 = sw1
		self.pilot_symbols = pilot_symbols = ps
		self.pilot_carriers = pilot_carriers = pc
		self.occupied_carriers = occupied_carriers = oc
		self.fft_len = fft_len = (len(sync_word1)+len(sync_word2))/2

		#payload modulation
		if payload_mod == 'qpsk':
			self.payload_mod = payload_mod = digital.constellation_qpsk()
			self.bps = 2
		elif payload_mod == 'qam16':
			self.payload_mod = payload_mod = digital.qam.qam_constellation(16,True,'none',False)
			self.bps = 4
		elif payload_mod == 'bpsk':
			self.payload_mod = payload_mod = digital.constellation_bpsk()
			self.bps = 1

		#header modulation
		self.header_mod = header_mod = digital.constellation_bpsk()

		self.cp_len = cp_len = cp
		self.samp_rate = samp_rate = sf

		self.vector_probe_pts = vector_probe_pts = int(2**math.ceil(math.log(samp_rate*t_obs,2)))

		self.packet_length_tag_key = packet_length_tag_key = "packet_len"
		self.length_tag_key = length_tag_key = "frame_len"

		self.payload_equalizer = payload_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, payload_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols, 1)
		self.header_formatter = header_formatter = digital.packet_header_ofdm(occupied_carriers, n_syms=1, len_tag_key=packet_length_tag_key, frame_len_tag_key=length_tag_key, bits_per_header_sym=header_mod.bits_per_symbol(), bits_per_payload_sym=payload_mod.bits_per_symbol(), scramble_header=True)
		self.header_equalizer = header_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, header_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols)

		self.digital_ofdm_rx = digital.ofdm_rx(
			fft_len=fft_len, cp_len=cp_len,
			frame_length_tag_key='frame_'+"length",
			packet_length_tag_key="length",
			occupied_carriers=occupied_carriers,
			pilot_carriers=pilot_carriers,
			pilot_symbols=pilot_symbols,
			sync_word1=sync_word1,
			sync_word2=sync_word2,
			bps_header=1,
			bps_payload=self.bps,
			debug_log=False,
			scramble_bits=scramble
			)
		self.blocks_tag_debug = blocks.tag_debug(gr.sizeof_char*1, "Rx Bytes", ""); self.blocks_tag_debug.set_display(True)        

		#probes
		self.s2v = blocks.stream_to_vector(gr.sizeof_gr_complex*1, vector_probe_pts)
		self.probe = blocks.probe_signal_vc(vector_probe_pts)

		# initialize the message queues
		self.sink_queue = gr.msg_queue()
		self.msg_sink = blocks.message_sink(gr.sizeof_char*1, self.sink_queue, False)
		self.rx_callback = rx_callback

		##################################################
		# Connections
		##################################################
		#RF LINK
		self.connect(self, self.digital_ofdm_rx)
		if debug:
			self.connect(self.digital_ofdm_rx, self.blocks_tag_debug)
		self.connect(self.digital_ofdm_rx, self.msg_sink)

		self._watcher = _queue_watcher_thread_mod(self.sink_queue, self.rx_callback) # mod = no CRC check

	def receive_ofdm(self):
		return None

	def sense(self):
		self.connect(self, self.s2v, self.probe)

	def unsense(self):
		self.disconnect(self, self.s2v, self.probe)

	def get_samp_rate(self):
		return self.samp_rate

	def get_probe_vector_level(self):
		return self.probe.level()

	def get_probe_vector_levels(self):
		vect = self.probe.level()
		vectr = [item.real for item in vect]
		vecti = [item.imag for item in vect]
		return (vectr+vecti)

	def get_vector_probe_pts(self):
		return self.vector_probe_pts

#Hier OFDM based synchronization transmitter
class sync_transmit_path(gr.hier_block2): 
	def __init__(self, sf, pkt_len, scramble):
		gr.hier_block2.__init__(self, "sync_transmit_path",
				gr.io_signature(0, 0, 0),
				gr.io_signature(1, 1, gr.sizeof_gr_complex))
				
		# Variables
		'''
		self.sync_word2 = sync_word2 = [0j, 0j, 0j, 0j, 0j, 0j, (-1+0j), (-1+0j), (-1+0j), (-1+0j), (1+0j), (1+0j), (-1+0j), (-1+0j), (-1+0j), (1+0j), (-1+0j), (1+0j), (1+0j), (1 +0j), (1+0j), (1+0j), (-1+0j), (-1+0j), (-1+0j), (-1+0j), (-1+0j), (1+0j), (-1+0j), (-1+0j), (1+0j), (-1+0j), 0j, (1+0j), (-1+0j), (1+0j), (1+0j), (1+0j), (-1+0j), (1+0j), (1+0j), (1+0j), (-1+0j), (1+0j), (1+0j), (1+0j), (1+0j), (-1+0j), (1+0j), (-1+0j), (-1+0j), (-1+0j), (1+0j), (-1+0j), (1+0j), (-1+0j), (-1+0j), (-1+0j), (-1+0j), 0j, 0j, 0j, 0j, 0j]
		self.sync_word1 = sync_word1 = [0., 0., 0., 0., 0., 0., 0., 1.41421356, 0., -1.41421356, 0., 1.41421356, 0., -1.41421356, 0., -1.41421356, 0., -1.41421356, 0., 1.41421356, 0., -1.41421356, 0., 1.41421356, 0., -1.41421356, 0., -1.41421356, 0., -1.41421356, 0., -1.41421356, 0., 1.41421356, 0., -1.41421356, 0., 1.41421356, 0., 1.41421356, 0., 1.41421356, 0., -1.41421356, 0., 1.41421356, 0., 1.41421356, 0., 1.41421356, 0., -1.41421356, 0., 1.41421356, 0., 1.41421356, 0., 1.41421356, 0., 0., 0., 0., 0., 0.]
		self.pilot_symbols = pilot_symbols = ((1, 1, 1, -1,),)
		self.pilot_carriers = pilot_carriers = ((-21, -7, 7, 21,),)
		self.occupied_carriers = occupied_carriers = (range(-26, -21) + range(-20, -7) + range(-6, 0) + range(1, 7) + range(8, 21) + range(22, 27),)
		'''
		self.sync_word1 = sync_word1 = _sync_sync_word1
		self.sync_word2 = sync_word2 = _sync_sync_word2
		self.pilot_symbols = pilot_symbols = _sync_pilot_symbols
		self.pilot_carriers = pilot_carriers = _sync_pilot_carriers
		self.occupied_carriers = occupied_carriers = _sync_occupied_carriers

		self.fft_len = fft_len = _sync_fft_len

		self.payload_mod = payload_mod = digital.constellation_qpsk()
		self.header_mod = header_mod = digital.constellation_bpsk()

		self.packet_length_tag_key = packet_length_tag_key = "packet_len"
		self.length_tag_key = length_tag_key = "frame_len"

		self.samp_rate = samp_rate = sf
		self.payload_equalizer = payload_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, payload_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols, 1)
		self.packet_len = packet_len = pkt_len
		self.header_formatter = header_formatter = digital.packet_header_ofdm(occupied_carriers, n_syms=1, len_tag_key=packet_length_tag_key, frame_len_tag_key=length_tag_key, bits_per_header_sym=header_mod.bits_per_symbol(), bits_per_payload_sym=payload_mod.bits_per_symbol(), scramble_header=True)
		self.header_equalizer = header_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, header_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols)
		self.cp_len = cp_len = _sync_cp_len

		self.blocks_multiply_const = blocks.multiply_const_vcc((0.01, ))

		self.digital_ofdm_tx = ofdm_tx_simple(
			fft_len=fft_len, cp_len=cp_len,
			packet_length_tag_key=packet_length_tag_key,
			occupied_carriers=occupied_carriers,
			pilot_carriers=pilot_carriers,
			pilot_symbols=pilot_symbols,
			sync_word1=sync_word1,
			sync_word2=sync_word2,
			bps_header=1,
			bps_payload=2,
			rolloff=cp_len/4,
			debug_log=False,
			scramble_bits=scramble
			)

		self.blocks_stream_to_tagged_stream = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, packet_len, packet_length_tag_key)

		# initialize the message queues
		self.source_queue = gr.msg_queue()
		self.msg_source = blocks.message_source(gr.sizeof_char*1, self.source_queue)

		##################################################
		# Connections
		##################################################
		self.connect(self.msg_source, self.blocks_stream_to_tagged_stream)
		self.connect(self.blocks_stream_to_tagged_stream, self.digital_ofdm_tx)
		self.connect(self.digital_ofdm_tx, self.blocks_multiply_const) 
		#RF LINK
		self.connect(self.blocks_multiply_const, self)

	def send_pkt_s(self, payload='', eof=False):
		if eof:
			msg = gr.message(1) # tell self._pkt_input we're not sending any more packets
		else:
			msg = gr.message_from_string(payload)
		self.source_queue.insert_tail(msg)

#Hier OFDM based synchronization receiver
class sync_receive_path(gr.hier_block2):
	def __init__(self, debug, sf, callback, scramble):
		gr.hier_block2.__init__(self, "sync_receive_path",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))

		# Variables
		self.sync_word1 = sync_word1 = _sync_sync_word1
		self.sync_word2 = sync_word2 = _sync_sync_word2
		self.pilot_symbols = pilot_symbols = _sync_pilot_symbols
		self.pilot_carriers = pilot_carriers = _sync_pilot_carriers
		self.occupied_carriers = occupied_carriers = _sync_occupied_carriers

		self.fft_len = fft_len = _sync_fft_len

		self.payload_mod = payload_mod = digital.constellation_qpsk()
		self.header_mod = header_mod = digital.constellation_bpsk()

		self.packet_length_tag_key = packet_length_tag_key = "packet_len"
		self.length_tag_key = length_tag_key = "frame_len"

		self.samp_rate = samp_rate = sf
		self.payload_equalizer = payload_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, payload_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols, 1)
		self.header_formatter = header_formatter = digital.packet_header_ofdm(occupied_carriers, n_syms=1, len_tag_key=packet_length_tag_key, frame_len_tag_key=length_tag_key, bits_per_header_sym=header_mod.bits_per_symbol(), bits_per_payload_sym=payload_mod.bits_per_symbol(), scramble_header=True)
		self.header_equalizer = header_equalizer = digital.ofdm_equalizer_simpledfe(fft_len, header_mod.base(), occupied_carriers, pilot_carriers, pilot_symbols)
		self.cp_len = cp_len = _sync_cp_len

		self.digital_ofdm_rx = ofdm_rx_simple(
			fft_len=fft_len, cp_len=cp_len,
			frame_length_tag_key='frame_'+"length",
			packet_length_tag_key="length",
			occupied_carriers=occupied_carriers,
			pilot_carriers=pilot_carriers,
			pilot_symbols=pilot_symbols,
			sync_word1=sync_word1,
			sync_word2=sync_word2,
			bps_header=1,
			bps_payload=2,
			debug_log=False,
			scramble_bits=scramble
			)
		self.blocks_tag_debug = blocks.tag_debug(gr.sizeof_char*1, "Rx Bytes", ""); self.blocks_tag_debug.set_display(True)        

		# initialize the message queues
		self.sink_queue = gr.msg_queue()
		self.msg_sink = blocks.message_sink(gr.sizeof_char*1, self.sink_queue, False)

		##################################################
		# Connections
		##################################################
		#RF LINK
		self.connect(self, self.digital_ofdm_rx)
		if debug:
			self.connect(self.digital_ofdm_rx, self.blocks_tag_debug)
		self.connect(self.digital_ofdm_rx, self.msg_sink)

		self._watcher = _queue_watcher_thread_mod(self.sink_queue, callback)

#listening thread for received packets - no CRC check
class _queue_watcher_thread_mod(_threading.Thread):
    def __init__(self, rcvd_pktq, callback):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_pktq = rcvd_pktq
        self.callback = callback
        self.keep_running = True
        self.start()

    def run(self):
        while self.keep_running:
            msg = self.rcvd_pktq.delete_head()
            payload = msg.to_string()
            if self.callback:
                self.callback(payload)

_def_fft_len = 64
_def_cp_len = 16
_def_frame_length_tag_key = "frame_length"
_def_packet_length_tag_key = "packet_length"
_def_packet_num_tag_key = "packet_num"
# Data and pilot carriers are same as in 802.11a
_def_occupied_carriers = (range(-26, -21) + range(-20, -7) + range(-6, 0) + range(1, 7) + range(8, 21) + range(22, 27),)
_def_pilot_carriers=((-21, -7, 7, 21,),)
_pilot_sym_scramble_seq = (
        1,1,1,1, -1,-1,-1,1, -1,-1,-1,-1, 1,1,-1,1, -1,-1,1,1, -1,1,1,-1, 1,1,1,1, 1,1,-1,1,
        1,1,-1,1, 1,-1,-1,1, 1,1,-1,1, -1,-1,-1,1, -1,1,-1,-1, 1,-1,-1,1, 1,1,1,1, -1,-1,1,1,
        -1,-1,1,-1, 1,-1,1,1, -1,-1,-1,1, 1,-1,-1,-1, -1,1,-1,-1, 1,-1,1,1, 1,1,-1,1, -1,1,-1,1,
        -1,-1,-1,-1, -1,1,-1,1, 1,-1,1,-1, 1,1,1,-1, -1,1,-1,-1, -1,1,1,1, -1,-1,-1,-1, -1,-1,-1
)
_def_pilot_symbols= tuple([(x, x, x, -x) for x in _pilot_sym_scramble_seq])
_seq_seed = 42


def _get_constellation(bps):
    """ Returns a modulator block for a given number of bits per symbol """
    constellation = {
            1: digital.constellation_bpsk(),
            2: digital.constellation_qpsk(),
            3: digital.constellation_8psk()
    }
    try:
        return constellation[bps]
    except KeyError:
        print 'Modulation not supported.'
        exit(1)

class ofdm_tx_simple(gr.hier_block2):
    #Hierarchical block for OFDM modulation - original by gnuradio, altered by germano
    def __init__(self, fft_len=_def_fft_len, cp_len=_def_cp_len,
                 packet_length_tag_key=_def_packet_length_tag_key,
                 occupied_carriers=_def_occupied_carriers,
                 pilot_carriers=_def_pilot_carriers,
                 pilot_symbols=_def_pilot_symbols,
                 bps_header=1,
                 bps_payload=1,
                 sync_word1=None,
                 sync_word2=None,
                 rolloff=0,
                 debug_log=False,
                 scramble_bits=False
                 ):
        gr.hier_block2.__init__(self, "ofdm_tx",
                    gr.io_signature(1, 1, gr.sizeof_char),
                    gr.io_signature(1, 1, gr.sizeof_gr_complex))
        ### Param init / sanity check ########################################
        self.fft_len           = fft_len
        self.cp_len            = cp_len
        self.packet_length_tag_key = packet_length_tag_key
        self.occupied_carriers = occupied_carriers
        self.pilot_carriers    = pilot_carriers
        self.pilot_symbols     = pilot_symbols
        self.bps_header        = bps_header
        self.bps_payload       = bps_payload
        self.sync_word1 = sync_word1
        if sync_word1 is None:
            self.sync_word1 = _make_sync_word1(fft_len, occupied_carriers, pilot_carriers)
        else:
            if len(sync_word1) != self.fft_len:
                raise ValueError("Length of sync sequence(s) must be FFT length.")
        self.sync_words = [self.sync_word1,]
        if sync_word2 is None:
            self.sync_word2 = _make_sync_word2(fft_len, occupied_carriers, pilot_carriers)
        else:
            self.sync_word2 = sync_word2
        if len(self.sync_word2):
            if len(self.sync_word2) != fft_len:
                raise ValueError("Length of sync sequence(s) must be FFT length.")
            self.sync_word2 = list(self.sync_word2)
            self.sync_words.append(self.sync_word2)
        if scramble_bits:
            self.scramble_seed = 0x7f
        else:
            self.scramble_seed = 0x00 # We deactivate the scrambler by init'ing it with zeros
        ### Header modulation ################################################
        crc = digital.crc32_bb(False, self.packet_length_tag_key)
        header_constellation  = _get_constellation(bps_header)
        header_mod = digital.chunks_to_symbols_bc(header_constellation.points())
        formatter_object = digital.packet_header_ofdm(
            occupied_carriers=occupied_carriers, n_syms=1,
            bits_per_header_sym=self.bps_header,
            bits_per_payload_sym=self.bps_payload,
            scramble_header=scramble_bits
        )
        header_gen = digital.packet_headergenerator_bb(formatter_object.base(), self.packet_length_tag_key)
        header_payload_mux = blocks.tagged_stream_mux(
                itemsize=gr.sizeof_gr_complex*1,
                lengthtagname=self.packet_length_tag_key,
                tag_preserve_head_pos=1 # Head tags on the payload stream stay on the head
        )
        self.connect(
                self,
                crc,
                header_gen,
                header_mod,
                (header_payload_mux, 0)
        )
        if debug_log:
            self.connect(header_gen, blocks.file_sink(1, 'tx-hdr.dat'))
        ### Payload modulation ###############################################
        payload_constellation = _get_constellation(bps_payload)
        payload_mod = digital.chunks_to_symbols_bc(payload_constellation.points())
        payload_scrambler = digital.additive_scrambler_bb(
            0x8a,
            self.scramble_seed,
            7,
            0, # Don't reset after fixed length (let the reset tag do that)
            bits_per_byte=8, # This is before unpacking
            reset_tag_key=self.packet_length_tag_key
        )
        payload_unpack = blocks.repack_bits_bb(
            8, # Unpack 8 bits per byte
            bps_payload,
            self.packet_length_tag_key
        )
        self.connect(
            crc,
            payload_scrambler,
            payload_unpack,
            payload_mod,
            (header_payload_mux, 1)
        )
        ### Create OFDM frame ################################################
        allocator = digital.ofdm_carrier_allocator_cvc(
            self.fft_len,
            occupied_carriers=self.occupied_carriers,
            pilot_carriers=self.pilot_carriers,
            pilot_symbols=self.pilot_symbols,
            sync_words=self.sync_words,
            len_tag_key=self.packet_length_tag_key
        )
        (allocator).set_min_output_buffer(16000)
        ffter = fft.fft_vcc(
                self.fft_len,
                False, # Inverse FFT
                (), # No window
                True # Shift
        )
        cyclic_prefixer = digital.ofdm_cyclic_prefixer(
            self.fft_len,
            self.fft_len+self.cp_len,
            rolloff,
            self.packet_length_tag_key
        )
        (cyclic_prefixer).set_min_output_buffer(16000)
        self.connect(header_payload_mux, allocator, ffter, cyclic_prefixer, self)
        if debug_log:
            self.connect(allocator,       blocks.file_sink(gr.sizeof_gr_complex * fft_len, 'tx-post-allocator.dat'))
            self.connect(cyclic_prefixer, blocks.file_sink(gr.sizeof_gr_complex,           'tx-signal.dat'))


class ofdm_rx_simple(gr.hier_block2):
    #Hierarchical block for OFDM modulation - original by gnuradio, altered by germano
    def __init__(self, fft_len=_def_fft_len, cp_len=_def_cp_len,
                 frame_length_tag_key=_def_frame_length_tag_key,
                 packet_length_tag_key=_def_packet_length_tag_key,
                 packet_num_tag_key=_def_packet_num_tag_key,
                 occupied_carriers=_def_occupied_carriers,
                 pilot_carriers=_def_pilot_carriers,
                 pilot_symbols=_def_pilot_symbols,
                 bps_header=1,
                 bps_payload=1,
                 sync_word1=None,
                 sync_word2=None,
                 debug_log=False,
                 scramble_bits=False
                 ):
        gr.hier_block2.__init__(self, "ofdm_rx",
                    gr.io_signature(1, 1, gr.sizeof_gr_complex),
                    gr.io_signature(1, 1, gr.sizeof_char))
        ### Param init / sanity check ########################################
        self.fft_len           = fft_len
        self.cp_len            = cp_len
        self.frame_length_tag_key    = frame_length_tag_key
        self.packet_length_tag_key   = packet_length_tag_key
        self.occupied_carriers = occupied_carriers
        self.bps_header        = bps_header
        self.bps_payload       = bps_payload
        n_sync_words = 1
        if sync_word1 is None:
            self.sync_word1 = _make_sync_word1(fft_len, occupied_carriers, pilot_carriers)
        else:
            if len(sync_word1) != self.fft_len:
                raise ValueError("Length of sync sequence(s) must be FFT length.")
            self.sync_word1 = sync_word1
        self.sync_word2 = ()
        if sync_word2 is None:
            self.sync_word2 = _make_sync_word2(fft_len, occupied_carriers, pilot_carriers)
            n_sync_words = 2
        elif len(sync_word2):
            if len(sync_word2) != fft_len:
                raise ValueError("Length of sync sequence(s) must be FFT length.")
            self.sync_word2 = sync_word2
            n_sync_words = 2
        if scramble_bits:
            self.scramble_seed = 0x7f
        else:
            self.scramble_seed = 0x00 # We deactivate the scrambler by init'ing it with zeros
        ### Sync ############################################################
        sync_detect = digital.ofdm_sync_sc_cfb(fft_len, cp_len)
        delay = blocks.delay(gr.sizeof_gr_complex, fft_len+cp_len)
        oscillator = analog.frequency_modulator_fc(-2.0 / fft_len)
        mixer = blocks.multiply_cc()
        hpd = digital.header_payload_demux(
            n_sync_words+1,       # Number of OFDM symbols before payload (sync + 1 sym header)
            fft_len, cp_len,      # FFT length, guard interval
            frame_length_tag_key, # Frame length tag key
            "",                   # We're not using trigger tags
            True                  # One output item is one OFDM symbol (False would output complex scalars)
        )
        self.connect(self, sync_detect)
        self.connect(self, delay, (mixer, 0), (hpd, 0))
        self.connect((sync_detect, 0), oscillator, (mixer, 1))
        self.connect((sync_detect, 1), (hpd, 1))
        if debug_log:
            self.connect((sync_detect, 0), blocks.file_sink(gr.sizeof_float, 'freq-offset.dat'))
            self.connect((sync_detect, 1), blocks.file_sink(gr.sizeof_char, 'sync-detect.dat'))
        ### Header demodulation ##############################################
        header_fft           = fft.fft_vcc(self.fft_len, True, (), True)
        chanest              = digital.ofdm_chanest_vcvc(self.sync_word1, self.sync_word2, 1)
        header_constellation = _get_constellation(bps_header)
        header_equalizer     = digital.ofdm_equalizer_simpledfe(
            fft_len,
            header_constellation.base(),
            occupied_carriers,
            pilot_carriers,
            pilot_symbols,
            symbols_skipped=0,
        )
        header_eq = digital.ofdm_frame_equalizer_vcvc(
                header_equalizer.base(),
                cp_len,
                self.frame_length_tag_key,
                True,
                1 # Header is 1 symbol long
        )
        header_serializer = digital.ofdm_serializer_vcc(
                fft_len, occupied_carriers,
                self.frame_length_tag_key
        )
        header_demod     = digital.constellation_decoder_cb(header_constellation.base())
        header_formatter = digital.packet_header_ofdm(
                occupied_carriers, 1,
                packet_length_tag_key,
                frame_length_tag_key,
                packet_num_tag_key,
                bps_header,
                bps_payload,
                scramble_header=scramble_bits
        )
        header_parser = digital.packet_headerparser_b(header_formatter.formatter())
        self.connect(
                (hpd, 0),
                header_fft,
                chanest,
                header_eq,
                header_serializer,
                header_demod,
                header_parser
        )
        self.msg_connect(header_parser, "header_data", hpd, "header_data")
        if debug_log:
            self.connect((chanest, 1),      blocks.file_sink(gr.sizeof_gr_complex * fft_len, 'channel-estimate.dat'))
            self.connect((chanest, 0),      blocks.file_sink(gr.sizeof_gr_complex * fft_len, 'post-hdr-chanest.dat'))
            self.connect((chanest, 0),      blocks.tag_debug(gr.sizeof_gr_complex * fft_len, 'post-hdr-chanest'))
            self.connect(header_eq,         blocks.file_sink(gr.sizeof_gr_complex * fft_len, 'post-hdr-eq.dat'))
            self.connect(header_serializer, blocks.file_sink(gr.sizeof_gr_complex,           'post-hdr-serializer.dat'))
            self.connect(header_descrambler, blocks.file_sink(1,                             'post-hdr-demod.dat'))
        ### Payload demod ####################################################
        payload_fft = fft.fft_vcc(self.fft_len, True, (), True)
        payload_constellation = _get_constellation(bps_payload)
        payload_equalizer = digital.ofdm_equalizer_simpledfe(
                fft_len,
                payload_constellation.base(),
                occupied_carriers,
                pilot_carriers,
                pilot_symbols,
                symbols_skipped=1, # (that was already in the header)
                alpha=0.1
        )
        payload_eq = digital.ofdm_frame_equalizer_vcvc(
                payload_equalizer.base(),
                cp_len,
                self.frame_length_tag_key
        )
        payload_serializer = digital.ofdm_serializer_vcc(
                fft_len, occupied_carriers,
                self.frame_length_tag_key,
                self.packet_length_tag_key,
                1 # Skip 1 symbol (that was already in the header)
        )
        payload_demod = digital.constellation_decoder_cb(payload_constellation.base())
        self.payload_descrambler = digital.additive_scrambler_bb(
            0x8a,
            self.scramble_seed,
            7,
            0, # Don't reset after fixed length
            bits_per_byte=8, # This is after packing
            reset_tag_key=self.packet_length_tag_key
        )
        payload_pack = blocks.repack_bits_bb(bps_payload, 8, self.packet_length_tag_key, True)
        self.crc = digital.crc32_bb(True, self.packet_length_tag_key)
        self.connect(
                (hpd, 1),
                payload_fft,
                payload_eq,
                payload_serializer,
                payload_demod,
                payload_pack,
                self.payload_descrambler,
                self.crc,
                self
        )
        if debug_log:
            self.connect((hpd, 1),           blocks.tag_debug(gr.sizeof_gr_complex*fft_len, 'post-hpd'))
            self.connect(payload_fft,        blocks.file_sink(gr.sizeof_gr_complex*fft_len, 'post-payload-fft.dat'))
            self.connect(payload_eq,         blocks.file_sink(gr.sizeof_gr_complex*fft_len, 'post-payload-eq.dat'))
            self.connect(payload_serializer, blocks.file_sink(gr.sizeof_gr_complex,         'post-payload-serializer.dat'))
            self.connect(payload_demod,      blocks.file_sink(1,                            'post-payload-demod.dat'))
            self.connect(payload_pack,       blocks.file_sink(1,                            'post-payload-pack.dat'))
            self.connect(crc,                blocks.file_sink(1,                            'post-payload-crc.dat'))

class noise_estimator(gr.hier_block2):
	def __init__(self, sr, cr, t, f_off):
		gr.hier_block2.__init__(self, "noise_estimator",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))

		# Variables
		self.t_obs = t_obs = t
		self.samp_rate = samp_rate = sr
		self.channel_rate = channel_rate = cr
		self.dec = dec = int (samp_rate / channel_rate)
		self.filter_taps = filter_taps = firdes.low_pass_2(1, samp_rate,  channel_rate, 5e3, 60)
		self.N = N = int(2**math.ceil(math.log(channel_rate*t_obs,2)))
		self.freq_offset = freq_offset = f_off

		# Blocks
		if freq_offset > 0:
			self.freq_xlating = filter.freq_xlating_fir_filter_ccf(1, (1, ), freq_offset, samp_rate)

		self.s2v = blocks.stream_to_vector(gr.sizeof_gr_complex*1, N)
		self.probe = blocks.probe_signal_vc(N)
		self.skiphead = blocks.skiphead(gr.sizeof_gr_complex*1, int(2*N))
		self.head = blocks.head(gr.sizeof_gr_complex*1, int(N))
		self.rational_resampler = filter.rational_resampler_ccf(interpolation = 1, decimation = dec, taps = None, fractional_bw = None,)
		self.fft_filter = filter.fft_filter_ccc(1, (filter_taps), 1)
		self.fft_filter.declare_sample_delay(0)

		# Connections
		if freq_offset > 0:
			self.connect(self, self.freq_xlating, self.fft_filter, self.rational_resampler, self.skiphead, self.head, self.s2v, self.probe)
		else:
			self.connect(self, self.fft_filter, self.rational_resampler, self.skiphead, self.head, self.s2v, self.probe)

	def get_level(self):
		return np.array(self.probe.level())

	def get_noise_estimate(self):
		vct = np.array(self.probe.level())
		return clc_power_freq(vct, 2048, self.channel_rate)

#Universal TUN/TAP device driver to move packets to/from kernel
#See /usr/src/linux/Documentation/networking/tuntap.txt
# Linux specific...
# TUNSETIFF ifr flags from <linux/tun_if.h>
IFF_TUN = 0x0001   # tunnel IP packets
IFF_TAP = 0x0002   # tunnel ethernet frames
IFF_NO_PI = 0x1000   # don't pass extra packet info
IFF_ONE_QUEUE = 0x2000   # beats me ;)
#
#Before starting using the device
# sudo ifconfig gr<number> 192.168.200.1
# and define MTU if applicable
# sudo ifconfig gr0 mtu 400
# test w/ ping, ssh, iperf, etc
# iperf server: iperf -s -B 192.168.200.2
# iperf client: iperf -c 192.168.200.2 -t 60 -i 10

def open_tun_interface(tun_device_filename):
	from fcntl import ioctl
	mode = IFF_TAP | IFF_NO_PI
	TUNSETIFF = 0x400454ca
	tun = os.open(tun_device_filename, os.O_RDWR)
	ifs = ioctl(tun, TUNSETIFF, struct.pack("16sH", "gr%d", mode))
	ifname = ifs[:16].strip("\x00")
	return (tun, ifname)

#filter packets containing sync data - remove control chars
def filter_sync_data(raw_data):
	l = len(raw_data)
	filtered = ''
	i = 0
	while i <= l-3:
		if raw_data[i] == '@':
			i += 1
		elif raw_data[i] == '#' and raw_data[i+1] == '#' and raw_data[i+2] == '#':
			i += 3
			if raw_data[i] != '$':
				filtered += raw_data[i]
				i += 1
		elif raw_data[i] == '$':
			i += 1
		else:
			filtered += raw_data[i]
			i += 1
	return filtered

#extract sync data given a sync data key
def get_sync_data(data, key):
	key_s = key+'S'
	key_f = key+'F'
	start = len(key_s)
	if data.find(key_s) == -1 or data.find(key_s) == -1: 
		return False
	else:
		output = data[data.find(key_s)+start:data.find(key_f)]
		return output

#my custom made payloads
def build_sync_payload(str_msg, pkt_size):
	if type(str_msg) is not str:
		return 'the message was not a string message'
	else:
		l = len(str_msg)
		payload = '###' + str_msg + '$$$' + (pkt_size-l-6) * '@'
		return payload

def chunks_of_word(word, chunk_size):
	chunked = []
	for i in range(0, len(word), chunk_size):
		chunked.append(word[i:i+chunk_size])
	return chunked

#sync_data_keys = ['OCUP', 'PILOT', 'PIL', 'FREQ', 'SAMP', 'MOD', 'PACT','SW1R', 'SW1I', 'SW2R', 'SW2I']
sync_data_keys = ['OCUP', 'PILOT', 'PIL', 'FREQ', 'SAMP', 'MOD', 'PACT', 'SW1', 'SW2']

def pack_sync_data(occupied_carriers, pilot_carriers, pilot_symbols, ofdm_fc, ofdm_samp_freq, payload_mod, packet_len, sync_word1, sync_word2):
	syncdata = 'OCUPS' + str(occupied_carriers) + 'OCUPF' + 'PILOTS' + str(pilot_carriers) + 'PILOTF' + 'PILS' + str(pilot_symbols) + 'PILF' + 'FREQS' + str(ofdm_fc) + 'FREQF' + 'SAMPS' + str(ofdm_samp_freq) + 'SAMPF' + 'MODS' + str(payload_mod) + 'MODF' + 'PACTS' + str(packet_len) + 'PACTF' + 'SW1S' + str(sync_word1) + 'SW1F' + 'SW2S' + str(sync_word2) + 'SW2F'
	return syncdata

def unpack_sync_data(filtered_data):
	sync_data = [True] * 9
	i = 0
	for key in sync_data_keys:
		new = get_sync_data(filtered_data, key)
		if new:
			sync_data[i] = new
		i += 1

	i = 0
	for el in sync_data:
		print sync_data_keys[i]
		print el
		i += 1

	print 'rebuilding sync data...'
	occupied_carriers =  ast.literal_eval(sync_data[0])
	pilot_carriers = ast.literal_eval(sync_data[1])
	pilot_symbols = ast.literal_eval(sync_data[2])
	ofdm_fc = ast.literal_eval(sync_data[3])
	ofdm_samp_freq = ast.literal_eval(sync_data[4])
	payload_mod = sync_data[5]  # bpsk qpsk qam16
	packet_len = ast.literal_eval(sync_data[6])
	sync_word1 = ast.literal_eval(sync_data[7])
	sync_word2 = ast.literal_eval(sync_data[8])

	return occupied_carriers, pilot_carriers, pilot_symbols, ofdm_fc, ofdm_samp_freq, payload_mod, packet_len, sync_word1, sync_word2

	#A-from MASTER OS to SLAVE OS
	#B-from MASTER SENSE to SLAVE SENSE
	#C-from SLAVE OS to MASTER OS
	#D-from SLAVE SENSE to MASTER SENSE
	#U- UNKNOWN

def make_sync_header(payload_len, type_pkt):
	return '###' + payload_len + type_pkt

def make_sync_packet(payload, pkt_size, pkt_type, pkt_numb):
	l = len(payload)
	L = str(l)
	Le = (4-len(L))*'0' + L #force 4 digits
	pkt_hd = make_sync_header(Le, pkt_type)
	pkt_dt = payload
	N = str(pkt_numb)
	pkt_nr = (2-len(N))*'0' + N #force 2 digits
	#overhead = 3 + 4 + 1 + 2 = 10 -> ### + len + type + nr
	packet_length = len(pkt_hd) + len(pkt_nr) + len(pkt_dt)
	packing = (pkt_size-packet_length) * '\x55'
	pkt = pkt_hd + pkt_nr + pkt_dt + packing
	return pkt

def unmake_sync_packet(frame):
	s = frame.find('###')
	l = 3
	len_len = 4
	tpe_len = 1
	nr_len = 2
	if s == -1:
		print 'RX wrong packing - no s or f marks'
		return frame, 'BAD', 9999
	else:
		pld_len = int(frame[s+l:s+l+len_len]) #length of pld_len = 4
		tpe = frame[s+l+len_len:s+l+len_len+tpe_len]
		nr = int(frame[s+l+len_len+tpe_len:s+l+len_len+tpe_len+nr_len])
		output = frame[s+l+len_len+tpe_len+nr_len:s+l+len_len+tpe_len+nr_len+pld_len]
		return output, tpe, nr

	#A - OS packet
	#B - Cogitive packet
	#U- UNKNOWN

def make_sync_packet_evo(fm, tpe, nr, full_length, payload):
	payload_len_s = str(len(payload))
	payload_len_s = (4-len(payload_len_s))*'0' + payload_len_s #4

	nr_s = str(nr)
	nr_s = (2-len(nr_s))*'0' + nr_s #2

	pkt = str(fm) + tpe + nr_s + payload_len_s + payload #1+1+2+4
	packing = ''.join(random.choice(string.ascii_uppercase) for i in range(full_length-len(pkt)))
	#packed = pkt + (full_length-len(pkt)) * '\x55'
	packed = pkt + packing
	return packed #overhead = 1 + 1 + 2 + 4 = 8 -> fm + tpe + nr + len

def unmake_sync_packet_evo(frame):
	try:
		fm = frame[0]
		tpe = frame[1]
		nr = int(frame[2:4])
		length = int(frame[4:8])
		data = frame[8:8+length]
		return fm, tpe, nr, data
	except:
		print 'an error occoured while unmaking sync packet'
		return 'BAD', 'BAD', 'BAD', 'BAD'

def make_packet(payload, pkt_size , type_pkt): # make_packet(payload, self.ofdm_settings['ofdm_packet_len']-4, 'A'))
	
	l = len(payload)
	L = str(l)
	Le = (4-len(L))*'0' + L
	packing = (pkt_size - (5 + l)) * '\x55'
	pkt = Le + type_pkt + payload + packing
	return pkt

def unmake_packet(frame, w_crc):
	if w_crc:
		try:
			pld_len = int(frame[0:4]) #length of pld_len = 4
			tpe = frame[4] #length of tpe_len = 1
			output = frame[5:5+pld_len]
			return output, tpe, True
		except:
			print 'an error occoured while unmaking ofdm packet - in-flowgraph CRC'
	else:
		ok, frame = digital.crc.check_crc32(frame)
		if ok:
			try:
				pld_len = int(frame[0:4]) #length of pld_len = 4
				tpe = frame[4] #length of tpe_len = 1
				output = frame[5:5+pld_len]
				return output, tpe, ok
			except:
				print 'an error occoured while unmaking ofdm packet- out-flowgraph CRC'
				print 'ok: ', ok
				print 'frame: ', frame
		else:
			print 'CRC NOK'
			return 'BAD', 'BAD', ok

	#A - OS packet
	#B - Cogitive packet
	#U- UNKNOWN

def make_packet_evo(fm, tpe, full_length, payload):
	# fm - 2bytes; to - 2bytes; tpe - 1byte
	paylaod_length_s = str(len(payload))
	paylaod_length_s = (4-len(paylaod_length_s))*'0' + paylaod_length_s
	pkt = str(fm) + tpe + paylaod_length_s + payload
	packing = ''.join(random.choice(string.ascii_uppercase) for i in range(full_length-len(pkt)))
	#packed = pkt + (full_length-len(pkt)) * '\x55'
	packed = pkt + packing
	return packed

def unmake_packet_evo(frame, w_crc):
	if w_crc:
		try:
			fm = frame[0]
			tpe = frame[1]
			length = int(frame[2:6])
			data = frame[6:6+length]
			return fm, tpe, length, data, True
		except:
			print 'an error occoured while unmaking ofdm packet - in-flowgraph CRC'
			return 'BAD', 'BAD', 'BAD', 'BAD', False
	else:
		ok, frame = digital.crc.check_crc32(frame)
		if ok:
			try:
				fm = frame[0]
				tpe = frame[1]
				length = int(frame[2:6])
				data = frame[6:6+length]
				return fm, tpe, length, data, ok
			except:
				print 'an error occoured while unmaking ofdm packet- out-flowgraph CRC'
				print 'ok: ', ok
				print 'frame: ', frame
		else:
			print 'CRC NOK'
			return 'BAD', 'BAD', 'BAD', 'BAD', ok



