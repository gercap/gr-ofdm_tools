#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2014 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# Created by Germanocapela at gmail dot com - based on chat_blocks.py from GNURadio tutorials
#
# Versatile block to send/receive PDU formatted messages
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import string
import numpy
import pmt
from gnuradio import gr, digital, blocks

class message_pdu(gr.basic_block):
    """
    This block will accept inputs through a member function,
    sanitize them (in this case, remove all non-printable characters)
    prepend a prefix, and send the string as a uint8 vector out on
    the message port named 'msg_out'.
    """
    def __init__(self, callback, prefix=None, access_code=None):
        gr.basic_block.__init__(self,
            name="message_pdu",
            in_sig=[],
            out_sig=[])
        self.prefix = prefix
        self.callback = callback

        # Register the message port IN
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)

        # Register the message port OUT
        self.message_port_register_out(pmt.intern('out'))

        # access_code = digital.packet_utils.default_access_code
        #  1010110011011101101001001110001011110010100011000010000011111100
        if access_code:
            if not digital.packet_utils.is_1_0_string(access_code):
                raise ValueError, \
                    "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)

        self.access_code = access_code


    def post_message(self, msg_str, meta=None):
        if self.prefix is not None:
            send_str = "[{}] {}".format(self.prefix, msg_str)
        else:
            send_str = msg_str

        # prepend AC to sent packet
        if self.access_code:
            (packed_access_code, padded) = digital.packet_utils.conv_1_0_string_to_packed_binary_string(self.access_code)
            print self.access_code
            print map(ord, packed_access_code)
            print padded
            send_str = packed_access_code + send_str

        # Create an empty PMT (contains only spaces):
        send_pmt = pmt.make_u8vector(len(send_str), ord(' '))
        # Copy all characters to the u8vector:
        for i in range(len(send_str)):
            pmt.u8vector_set(send_pmt, i, ord(send_str[i]))
        # Send the message:
        if meta is not None:
            self.message_port_pub(pmt.intern('out'), pmt.cons(pmt.to_pmt(meta), send_pmt))
        else:
            self.message_port_pub(pmt.intern('out'), pmt.cons(pmt.PMT_NIL, send_pmt))

    def handle_msg(self, msg_pmt, printMetadata=False):
        """ Receiver a u8vector on the input port, and print it out. """
        # Collect metadata, convert to Python format:
        meta = pmt.to_python(pmt.car(msg_pmt))
        # Collect message, convert to Python format:
        msg = pmt.cdr(msg_pmt)
        # Make sure it's a u8vector
        if not pmt.is_u8vector(msg):
            print "[ERROR] Received invalid message type.\n"
            return
        # Convert to string:
        msg_str = "".join([chr(x) for x in pmt.u8vector_elements(msg)])
        # Just for good measure, and to avoid attacks, let's filter again:
        # msg_str = filter(lambda x: x in string.printable, msg_str)
        # Print string, and if available, the metadata:
        if self.callback is not None:
            self.callback(msg_str)
        else:
            print msg_str
        if meta is not None and printMetadata:
            print "[METADATA]: ", meta


if __name__ == "__main__":
    import time
    # Create a flow graph
    tb = gr.top_block()
    # Create chat blocks
    chat_tx = message_pdu(None)
    chat_rx = message_pdu(None)
    pdu_to_tagged_stream = blocks.pdu_to_tagged_stream(blocks.byte_t, "packet_len")
    tagged_stream_to_pdu = blocks.tagged_stream_to_pdu(blocks.byte_t, "packet_len")
    # Connect them up
    tb.msg_connect(chat_tx, 'out',  pdu_to_tagged_stream, 'pdus')
    tb.connect(pdu_to_tagged_stream, tagged_stream_to_pdu)
    tb.msg_connect(tagged_stream_to_pdu, 'pdus',  chat_rx, 'in')
    # Start flow graph
    tb.start()
    chat_str = ""
    print "======= Chat/Message Passing Tester. Please type a message (type /quit to exit) ========="
    try:
        while chat_str != "/quit":
            chat_str = raw_input('> ')
            chat_tx.post_message(chat_str)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print "\n"
    except EOFError:
        print "\n"
    # Shut down flow graph
    tb.stop()
    # Wait for blocks to shut down
    tb.wait()
    print ">>> Done. Enjoy the message passing! <<<"
