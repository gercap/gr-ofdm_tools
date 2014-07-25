#!/usr/bin/env python
# 
# Copyright 2013 John Malsbury
# Copyright 2014 Balint Seeber <balint256@gmail.com>
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

from __future__ import with_statement

import sys, time, random, struct, threading
from math import pi
import Queue
import numpy
from gnuradio import gr
import pmt
from gnuradio.digital import packet_utils
import gnuradio.digital as gr_digital

from constants import *

# /////////////////////////////////////////////////////////////////////////////
#                   Simple MAC w/ ARQ
# /////////////////////////////////////////////////////////////////////////////

class Node():
    def __init__(self, id):
        self.id = id
        self.last_heard = None
        self.alive = False
    def update(self, time):
        was_alive = self.alive
        self.alive = True
        self.last_heard = time
        return (was_alive == False) and (self.alive)
    def expire(self):
        self.alive = False

class simple_mac(gr.basic_block):
#class simple_mac(gr.sync_block):
    """
    docstring for block mac
    """
    def __init__(self, addr, timeout, max_attempts, broadcast_interval=2.0,
            exp_backoff=True, backoff_randomness=0.05,
            node_expiry_delay=10.0, expire_on_arq_failure=False, only_send_if_alive=False,
            prepend_dummy=False):
        gr.basic_block.__init__(self,
            name="simple_mac",
            in_sig=None,
            out_sig=None)
        
        self.lock = threading.RLock()
        self.debug_stderr = False
        
        self.addr = addr                                #MAC's address
        
        self.pkt_cnt_arq = 0                            #pkt_cnt for arq channel
        self.pkt_cnt_no_arq = 0                            #pkt_cnt for non_arq channel
        
        self.arq_expected_sequence_number = 0            #keep track for sequence error detection
        self.no_arq_expected_sequence_number = 0        #keep track for sequence error detection
        
        self.arq_sequence_error_cnt = 0                    #arq channel seq errors - VERY BAD
        self.no_arq_sequence_error_cnt = 0                #non-arq channel seq error count
        self.arq_pkts_txed = 0                            #how many arq packets we've transmitted
        self.arq_retxed = 0                                #how many times we've retransmitted
        self.failed_arq = 0
        self.max_attempts = max_attempts
        
        self.arq_channel_state = ARQ_CHANNEL_IDLE
        self.expected_arq_id = -1                        #arq id we're expected to get ack for      
        self.timeout = timeout                            #arq timeout parameter
        self.time_of_tx = 0.0                            #time of last arq transmission
        self.exp_backoff = exp_backoff
        self.backoff_randomness = backoff_randomness
        self.next_random_backoff_percentage = 0.0
        
        self.queue = Queue.Queue()                        #queue for msg destined for ARQ path
        
        self.last_tx_time = None
        self.broadcast_interval = broadcast_interval
        self.nodes = {}
        self.node_expiry_delay = node_expiry_delay
        self.expire_on_arq_failure = expire_on_arq_failure
        self.only_send_if_alive = only_send_if_alive
        
        self.prepend_dummy = prepend_dummy
        
        #message i/o for radio interface
        self.message_port_register_out(pmt.intern('to_radio'))
        self.message_port_register_in(pmt.intern('from_radio'))
        self.set_msg_handler(pmt.intern('from_radio'), self.radio_rx)
        
        #message i/o for app interface
        self.message_port_register_out(pmt.intern('to_app'))
        self.message_port_register_in(pmt.intern('from_app'))
        self.set_msg_handler(pmt.intern('from_app'), self.app_rx)
        
        try:
            self.message_port_register_in(pmt.intern('from_app_arq'), True)
            print "Simple MAC ARQ in blocking mode"
        except:
        #if True:
            print "Simple MAC ARQ in non-blocking mode"
            self.message_port_register_in(pmt.intern('from_app_arq'))
            self.set_msg_handler(pmt.intern('from_app_arq'), self.app_rx_arq)
        
        #message i/o for ctrl interface
        self.message_port_register_out(pmt.intern('ctrl_out'))
        self.message_port_register_in(pmt.intern('ctrl_in'))
        self.set_msg_handler(pmt.intern('ctrl_in'), self.ctrl_rx)
    
    def general_work(self, input_items, output_items):
    #    return self.work(input_items, output_items)
    
    #def work(self, input_items, output_items):
        #sys.stdout.write('.')
        #sys.stdout.flush()
        #sys.stderr.write("[w+]");sys.stderr.flush();
        with self.lock:
            if self.arq_channel_state == ARQ_CHANNEL_IDLE:
                #msg = self.delete_head_nowait(pmt.intern('from_app_arq'))
                msg = self.pop_msg_queue(pmt.intern('from_app_arq'))
                if pmt.is_null(msg):
                    return 0
                #print "Via work:", msg
                #self.app_rx_arq(msg)
                self._app_rx(msg, True)
            else:
                #print "Not doing any work while ARQ channel is busy"
                pass
        #sys.stderr.write("[w-]");sys.stderr.flush();
        return 0
    
    
    #transmit layer 3 broadcast packet
    def send_bcast_pkt(self):
        self.send_pkt_radio((None, {'EM_DEST_ADDR':BROADCAST_ADDR}), 0, BROADCAST_PROTOCOL_ID, ARQ_NO_REQ)
    
    
    #transmit ack packet
    def send_ack(self, ack_addr, ack_pkt_cnt):
       data = [ack_pkt_cnt]
       meta_dict = {'EM_DEST_ADDR': ack_addr}
       pdu_tuple = (data, meta_dict)
       self.tx_no_arq(pdu_tuple, ARQ_PROTOCOL_ID)
       if self.debug_stderr: sys.stderr.write("[%.6f] ==> Sent ACK %03d to %03d\n" % (time.time(), ack_pkt_cnt, ack_addr))
    
    
    #transmit data through non-arq path    
    def tx_no_arq(self, pdu_tuple, protocol_id):
        self.send_pkt_radio(pdu_tuple, self.pkt_cnt_no_arq, protocol_id, ARQ_NO_REQ)
        self.pkt_cnt_no_arq = ( self.pkt_cnt_no_arq + 1 ) % 256
    
    
    #transmit data - msg is numpy array
    def send_pkt_radio(self, pdu_tuple, pkt_cnt, protocol_id, control, allow_dummy=True):
        meta_data = pdu_tuple[1]
        if allow_dummy:
            prepend_dummy = self.prepend_dummy or ('EM_PREPEND_DUMMY' in meta_data.keys() and meta_data['EM_PREPEND_DUMMY'])
            if prepend_dummy:
                #meta_data['EM_PREPEND_DUMMY'] = False
                #sys.stdout.write('.')
                #sys.stdout.flush()
                self.send_pkt_radio(pdu_tuple, pkt_cnt, DUMMY_PROTOCOL_ID, control, False)
        
        payload = pdu_tuple[0]
        if payload is None:
            payload = []
        elif isinstance(payload, str):
            payload = map(ord, list(payload))
        elif not isinstance(payload, list):
            payload = list(payload)
        
        dest_addr = meta_data['EM_DEST_ADDR']
        if dest_addr == -1:
            dest_addr = BROADCAST_ADDR
        elif dest_addr < -1 or dest_addr > BROADCAST_ADDR:
            print "Invalid address:", dest_addr
            return
        
        #create header, merge with payload, convert to pmt for message_pub
        data = [
            pkt_cnt,
            self.addr,
            dest_addr,
            protocol_id,
            control
        ]
        
        data += payload
        
        data = pmt.init_u8vector(len(data), data)
        meta = pmt.to_pmt({})
        
        #construct pdu and publish to radio port
        pdu = pmt.cons(meta, data)
        
        #publish to msg port
        self.message_port_pub(pmt.intern('to_radio'),pdu)
        
        with self.lock:
            self.last_tx_time = time.time()
    
    
    #transmit data through arq path
    def tx_arq(self, pdu_tuple, protocol_id):
        self.send_pkt_radio(pdu_tuple, self.pkt_cnt_arq, protocol_id, ARQ_REQ)
    
    
    def output_user_data(self, pdu_tuple):
        data = []
        if len(pdu_tuple[0]) > PKT_INDEX_MAX:
            data = pdu_tuple[0][PKT_INDEX_MAX:]
        
        data = pmt.init_u8vector(len(data), data)
        
        #pass through metadata if there is any
        meta = pmt.to_pmt(pdu_tuple[1])
        
        self.message_port_pub(pmt.intern('to_app'), pmt.cons(meta,data))
    
    
    def check_nodes(self):
        time_now = time.time()
        for n in self.nodes.keys():
            node = self.nodes[n]
            if node.alive:
                diff = time_now - node.last_heard
                if diff > self.node_expiry_delay:
                    node.expire()
                    print "Node %03d disappeared" % (node.id)
    
    
    def radio_rx(self, msg):
        try:
            meta = pmt.car(msg)
            data =  pmt.cdr(msg)
        except:
            #raise NameError("mac - input not a PDU")
            print "Message is not a PDU"
            return
        
        if pmt.is_u8vector(data):
            data = pmt.u8vector_elements(data)
        else:
            #raise NameError("Data is not u8 vector")
            print "Data is not a u8vector"
            return
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        #sys.stderr.write("[r+]");sys.stderr.flush();
        with self.lock:
            self._radio_rx(data, meta_dict)
        #sys.stderr.write("[r-]");sys.stderr.flush();
    
    def _radio_rx(self, data, meta_dict):
        crc_ok = True
        if 'CRC_OK' in meta_dict.keys():
            crc_ok = meta_dict['CRC_OK']
        
        if len(data) >= PKT_INDEX_MAX: #check for weird header only stuff
            src_addr = data[PKT_INDEX_SRC]
            meta_dict['EM_SRC_ID'] = src_addr
            
            if not src_addr == self.addr:
                if not crc_ok:
                    if src_addr in self.nodes.keys() and self.nodes[src_addr].alive:
                        #print "Packet of length %d from node %d to address %d failed CRC" % (len(data), src_addr, data[PKT_INDEX_DEST])
                        sys.stderr.write("!")
                        sys.stderr.flush()
                    return
                #print "Heard node", src_addr
                if src_addr in self.nodes.keys():
                    node = self.nodes[src_addr]
                else:
                    node = Node(src_addr)
                    self.nodes[src_addr] = node
                
                if node.update(time.time()):
                    print "Node %03d alive" % (node.id)
            else:
                #if crc_ok:
                #    print "Heard myself"
                return
            
            discard = False
            
            incoming_protocol_id = data[PKT_INDEX_PROT_ID]
            control_field = data[PKT_INDEX_CTRL]
            pkt_cnt = data[PKT_INDEX_CNT]
            dest_addr = data[PKT_INDEX_DEST]
            
            if not control_field in [ARQ_REQ, ARQ_NO_REQ]:
                print "Bad control field: %d" % (control_field)
                return
            
            if (incoming_protocol_id != DUMMY_PROTOCOL_ID) and ((dest_addr == self.addr or dest_addr == BROADCAST_ADDR) and (not src_addr == self.addr)):  # for us?
                # check to see if we must ACK this packet
                if control_field == ARQ_REQ: # TODO: stuff CTRL and Protocol in one field
                    self.send_ack(src_addr, pkt_cnt) # Then send ACK
                    if not (self.arq_expected_sequence_number == pkt_cnt):
                        self.arq_sequence_error_cnt += 1
                        if ((pkt_cnt + 1) % 256) != self.arq_expected_sequence_number:
                            print "Discarding out-of-sequence data: %03d (expected: %03d)" % (pkt_cnt, self.arq_expected_sequence_number)
                            if self.debug_stderr: sys.stderr.write("[%.6f] ==> Discarding OoS data %03d (expected: %03d)\n" % (time.time(), pkt_cnt, self.arq_expected_sequence_number))
                        discard = True
                    self.arq_expected_sequence_number =  (pkt_cnt + 1) % 256
                
                elif not incoming_protocol_id in [BROADCAST_PROTOCOL_ID]:
                    if self.no_arq_expected_sequence_number != pkt_cnt:
                        self.no_arq_sequence_error_cnt += 1
                        if incoming_protocol_id == ARQ_PROTOCOL_ID and len(data) > PKT_INDEX_MAX and data[5] == self.expected_arq_id:
                            pass
                        else:
                            print "Out-of-sequence data: %03d (expected: %03d, protocol: %d)" % (pkt_cnt, self.no_arq_expected_sequence_number, incoming_protocol_id)
                        if self.debug_stderr: sys.stderr.write("[%.6f] ==> OoS data %03d (expected: %03d, protocol: %d)\n" % (time.time(), pkt_cnt, self.no_arq_expected_sequence_number, incoming_protocol_id))
                    self.no_arq_expected_sequence_number = (pkt_cnt + 1) % 256
                
                # check to see if this is an ACK packet
                if incoming_protocol_id == ARQ_PROTOCOL_ID:
                    if len(data) > PKT_INDEX_MAX:
                        rx_ack = data[5]
                        if self.arq_channel_state == ARQ_CHANNEL_IDLE:
                            print "Received ACK while idle: %03d" % (rx_ack)
                            if self.debug_stderr: sys.stderr.write("[%.6f] ==> Got ACK %03d while idle\n" % (time.time(), rx_ack, self.pkt_cnt_arq, diff))
                        elif rx_ack == self.expected_arq_id: # 1st byte into payload
                            self.arq_channel_state = ARQ_CHANNEL_IDLE
                            self.pkt_cnt_arq = (self.pkt_cnt_arq + 1) % 256
                            diff = time.time() - self.time_of_tx
                            #print "==> ACK took %f sec" % (diff)
                            if self.debug_stderr: sys.stderr.write("[%.6f] ==> Got ACK %03d (next: %03d, took %f sec)\n" % (time.time(), rx_ack, self.pkt_cnt_arq, diff))
                        else:
                            if ((rx_ack + 1) % 256) != self.expected_arq_id:
                                print "Received out-of-sequence ACK: %03d (expected: %03d)" % (rx_ack, self.expected_arq_id)
                            if self.debug_stderr: sys.stderr.write("[%.6f] ==> OoS ACK %03d (expected: %03d)\n" % (time.time(), rx_ack, self.expected_arq_id))
                    else:
                        print "ARQ protocol packet too short"
                
                # do something with incoming user data
                elif incoming_protocol_id == USER_IO_PROTOCOL_ID:
                    if not discard:
                        pdu_tuple = (data, meta_dict)
                        self.output_user_data(pdu_tuple)
                
                elif incoming_protocol_id == BROADCAST_PROTOCOL_ID:
                    pass
                
                else:
                    print "Unknown protocol: %d" % (incoming_protocol_id)
        elif crc_ok:
            print "Did not receive enough bytes for a header (only got %d)" % (len(data))
        
        self.run_arq_fsm()
    
    
    def app_rx(self, msg):
        with self.lock:
            self._app_rx(msg, False)
    
    def app_rx_arq(self, msg):
        with self.lock:
            self._app_rx(msg, True)
    
    def _app_rx(self, msg, arq):
        try:
            meta = pmt.car(msg)
            data =  pmt.cdr(msg)
        except:
            #raise NameError("mac - input not a PDU")
            print "Message is not a PDU"
            return
        
        if pmt.is_u8vector(data):
            data = pmt.u8vector_elements(data)
        else:
            #raise NameError("Data is not u8 vector")
            print "Data is not a u8vector"
            return
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        if arq:
            meta_dict['EM_USE_ARQ'] = True
        
        if (not 'EM_DEST_ADDR' in meta_dict.keys()) or (meta_dict['EM_DEST_ADDR'] == -1):
            meta_dict['EM_DEST_ADDR'] = BROADCAST_ADDR
        
        self.dispatch_app_rx(data, meta_dict)
    
    
    def dispatch_app_rx(self, data, meta_dict):
        #double check to make sure correct meta data was in PDU
        if (not 'EM_USE_ARQ' in meta_dict.keys()) or (not 'EM_DEST_ADDR' in meta_dict.keys()):
            #raise NameError("EM_USE_ARQ and/or EM_DEST_ADDR not specified in PDU")
            print "PDU missing MAC metadata"
            return
        
        use_arq = meta_dict['EM_USE_ARQ']
        dest_addr = meta_dict['EM_DEST_ADDR']
        
        if dest_addr == BROADCAST_ADDR and use_arq:
            #print "Not using ARQ for broadcast packet"
            sys.stderr.write("*")
            sys.stderr.flush()
            use_arq = False
        
        with self.lock:
            if dest_addr != BROADCAST_ADDR and self.only_send_if_alive:
                if not dest_addr in self.nodes.keys():
                    print "Not sending packet to %03d as it hasn't been seen yet" % (dest_addr)
                    return
                elif not self.nodes[dest_addr].alive:
                    print "Not sending packet to %03d as it isn't alive" % (dest_addr)
                    return
            
            #assign tx path depending on whether PMT_BOOL EM_USE_ARQ is true or false
            if use_arq and dest_addr != BROADCAST_ADDR:
                self.queue.put((data, meta_dict))
                self.run_arq_fsm()
            else:
                self.tx_no_arq((data, meta_dict), USER_IO_PROTOCOL_ID)
            
            #self.run_arq_fsm()
    
    
    def ctrl_rx(self,msg):
        #sys.stderr.write("[c+]");sys.stderr.flush();
        with self.lock:
        #    sys.stderr.write("[c]");sys.stderr.flush();
            if (self.broadcast_interval > 0) and (self.last_tx_time is None or (time.time() - self.last_tx_time) >= self.broadcast_interval):
                self.send_bcast_pkt()
            
            self.run_arq_fsm()
            
            self.check_nodes()
        #sys.stderr.write("[c-]");sys.stderr.flush();
    
    
    def run_arq_fsm(self):
        # check to see if we have any outgoing messages from arq buffer we should send or pending re-transmissions
        if self.arq_channel_state == ARQ_CHANNEL_IDLE: #channel ready for next arq msg
            if not self.queue.empty(): #we have an arq msg to send, so lets send it
                #print self.queue.qsize()
                self.arq_pdu_tuple = self.queue.get() # get msg
                self.expected_arq_id = self.pkt_cnt_arq # store it for re-use
                self.tx_arq(self.arq_pdu_tuple, USER_IO_PROTOCOL_ID)
                self.time_of_tx = time.time() # note time for arq timeout recognition
                self.arq_channel_state = ARQ_CHANNEL_BUSY # remember that the channel is busy
                self.arq_pkts_txed += 1
                self.retries = 0
                self.next_random_backoff_percentage = self.backoff_randomness * random.random()
        else: # if channel is busy, lets check to see if its time to re-transmit
            if self.exp_backoff:
                backedoff_timeout = self.timeout * (2**self.retries)
            else:
                backedoff_timeout = self.timeout * (self.retries + 1)
            backedoff_timeout *= (1.0 + self.next_random_backoff_percentage)
            if (time.time() - self.time_of_tx) > backedoff_timeout: # check for ack timeout
                #data = self.arq_pdu_tuple[0]
                dest = self.arq_pdu_tuple[1]['EM_DEST_ADDR']
                if self.retries == self.max_attempts:            # know when to quit
                    print "[Addr: %03d ID: %03d] ARQ failed after %d attempts" % (dest, self.expected_arq_id, self.retries)
                    if self.debug_stderr: sys.stderr.write("[%.6f] ==> [Addr: %03d ID: %03d] ARQ failed after %d attempts\n" % (time.time(), self.expected_arq_id, self.retries))
                    self.retries = 0
                    self.arq_channel_state = ARQ_CHANNEL_IDLE
                    self.failed_arq += 1
                    self.pkt_cnt_arq = ( self.pkt_cnt_arq + 1 ) % 256   # start on next pkt
                    if self.expire_on_arq_failure:
                        if dest in self.nodes.keys():
                            node = self.nodes[dest]
                            node.expire()
                            print "Expired node %03d after ARQ retry failure" % (dest)
                        else:
                            print "ARQ retry failed to destination not in node map: %03d" % (dest)
                else:
                    self.retries += 1
                    time_now = time.time()
                    #print "[Addr: %03d ID: %03d] ARQ timed out after %.3f s - retry #%d" % (dest, self.expected_arq_id, (time_now - self.time_of_tx), self.retries)
                    sys.stderr.write(".")
                    sys.stderr.flush()
                    self.tx_arq(self.arq_pdu_tuple, USER_IO_PROTOCOL_ID)
                    if self.debug_stderr: sys.stderr.write("[%.6f] ==> [Addr: %03d ID: %03d] ARQ timed out after %.3f s - retry #%d\n" % (time.time(), dest, self.expected_arq_id, (time_now - self.time_of_tx), self.retries))
                    self.time_of_tx = time_now
                    self.next_random_backoff_percentage = self.backoff_randomness * random.random()
                    self.arq_retxed += 1
