#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2017 Germano Capela at gmail.com
# 
import zmq, Queue, os, sys, time, struct, signal, datetime
import threading
import Queue
import cherrypy, simplejson
from jinja2 import Environment, FileSystemLoader
import numpy as np
import xmlrpclib

import ssl
try:
  from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer, SimpleSSLWebSocketServer
except:
  print "try sudo pip install git+https://github.com/dpallot/simple-websocket-server.git"
  sys.exit(0)
from optparse import OptionParser

log_levels = {"CRITICAL":50, "ERROR":40, "WARNING":30, "INFO":20, "DEBUG":10}

# GET CURRENT DIRECTORY
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
env=Environment(loader=FileSystemLoader(CUR_DIR), trim_blocks=True)
MAX_LO_MTU = 65535

def signal_handler(signal, frame):
  print "you pressed ctrl-C!"
  _ws_server_control_runner.keep_running = False
  _ws_server_data_runner.keep_running = False

  _ws_dispatcher_control.keep_running = False
  _ws_dispatcher_data.keep_running = False

  _data_processor.keep_running = False

  ws_server_control.close()
  ws_server_data.close()
  sys.exit(0)


def jsonToUnicode(data):
  return unicode(simplejson.dumps(data), "utf-8")

class web_site(object):
    def __init__(self, data_processor, ws_control_port, ws_data_port, ssl=False):
      self.data_processor = data_processor
      self.ws_control_port = ws_control_port
      self.ws_data_port = ws_data_port
      self.scheme = 'wss' if ssl else 'ws'

    @cherrypy.expose
    def set_rf_gain(self, rf_gain):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.data_processor.set_rf_gain(int(float(rf_gain)))

    @cherrypy.expose
    def set_tune_freq(self, freq):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.data_processor.set_tune_freq(float(freq))

    @cherrypy.expose
    def set_rate(self, rate):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.data_processor.set_rate(float(rate))

    @cherrypy.expose
    def set_average(self, average):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.data_processor.set_average(float(average))

    @cherrypy.expose
    def set_precision(self, precision):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      if precision == "True":
        self.data_processor.set_precision(True)
      else:
        self.data_processor.set_precision(False)

    @cherrypy.expose
    def set_samp_rate(self, samp_rate):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.data_processor.set_samp_rate(float(samp_rate))

    @cherrypy.expose
    def index(self):

      template = env.get_template('./public/html/index_ws.html')
      return template.render(
        now=time.strftime("%H:%M:%S"),
        description='Web based SDR',
        site_title="Web SDR tests",
        control_port=self.ws_control_port,
        data_port=self.ws_data_port,
        scheme=self.scheme)

class data_processor(threading.Thread):
  def __init__(self, ZMQ_IP, ZMQ_PORT, shared_queue_control, shared_queue_data, xmlrpc_server):
    threading.Thread.__init__(self)
    self.zmq_context = zmq.Context()
    self.zmq_sub = self.zmq_context.socket(zmq.SUB)
    self.zmq_sub.connect("tcp://%s:%s" % (ZMQ_IP, ZMQ_PORT))
    self.zmq_sub.setsockopt(zmq.SUBSCRIBE, "")
    self.shared_queue_control = shared_queue_control
    self.shared_queue_data = shared_queue_data
    self.xmlrpc_server = xmlrpc_server

    self.samp_rate = self.xmlrpc_server.get_samp_rate()
    self.precision = self.xmlrpc_server.get_precision()
    self.tune_freq = self.xmlrpc_server.get_tune_freq()
    self.rate = self.xmlrpc_server.get_rate()
    self.average = self.xmlrpc_server.get_av()
    self.rf_gain = self.xmlrpc_server.get_rf_gain()

    self.device = self.xmlrpc_server.get_arg()
    if "airspyhf" not in self.device:
      self.gain_range = [self.xmlrpc_server.get_rf_gain_start(), self.xmlrpc_server.get_rf_gain_step(), self.xmlrpc_server.get_rf_gain_stop()]
      print 'gain range', self.gain_range
    else:
      self.gain_range = [0, 0, 0]
    print 'from server', self.get_samp_rate(), self.get_tune_freq(), self.get_rate(), self.get_average(), self.get_precision()

    self.reasembled_frame = ''
    if self.precision:
        self.data_type = np.float32
    else:
        self.data_type = np.int8
    self.max_fft_data = np.array([])
    self.strt = True

    self.keep_running = True

  def set_precision(self, precision):
    self.precision = precision
    if precision:
        self.data_type = np.float32
        self.xmlrpc_server.set_precision(True)
    else:
        self.data_type = np.int8
        self.xmlrpc_server.set_precision(False)
    self.shared_queue_control.put(jsonToUnicode({"precision":self.precision}))

  def get_precision(self):
    self.precision = self.xmlrpc_server.get_precision()
    self.shared_queue_control.put(jsonToUnicode({"precision":self.precision}))
    return self.precision

  def set_tune_freq(self, tune_freq):
    self.tune_freq = tune_freq
    self.xmlrpc_server.set_tune_freq(float(self.tune_freq))
    self.shared_queue_control.put(jsonToUnicode({"tune_freq":self.tune_freq}))
    self.shared_queue_control.put(jsonToUnicode({"samp_rate":self.samp_rate}))

  def get_tune_freq(self):
    self.tune_freq = self.xmlrpc_server.get_tune_freq()
    self.shared_queue_control.put(jsonToUnicode({"tune_freq":self.tune_freq}))
    return self.tune_freq

  def set_samp_rate(self, samp_rate):
    self.samp_rate = samp_rate
    self.shared_queue_control.put(jsonToUnicode({"samp_rate":self.samp_rate}))
    self.xmlrpc_server.set_samp_rate(float(self.samp_rate))

  def get_samp_rate(self):
    self.samp_rate = self.xmlrpc_server.get_samp_rate()
    self.shared_queue_control.put(jsonToUnicode({"samp_rate":self.samp_rate}))
    return self.samp_rate

  def set_rate(self, rate):
    self.rate = rate
    self.xmlrpc_server.set_rate(float(rate))
    self.shared_queue_control.put(jsonToUnicode({"rate":self.rate}))

  def get_rate(self):
    self.rate = self.xmlrpc_server.get_rate()
    self.shared_queue_control.put(jsonToUnicode({"rate":self.rate}))
    return self.rate

  def set_average(self, average):
    self.average = average
    self.xmlrpc_server.set_av(float(average))
    self.shared_queue_control.put(jsonToUnicode({"average":self.average}))

  def get_average(self):
    self.average = self.xmlrpc_server.get_av()
    self.shared_queue_control.put(jsonToUnicode({"average":self.average}))
    return self.average

  def set_rf_gain(self, rf_gain):
    self.rf_gain = rf_gain
    self.xmlrpc_server.set_rf_gain(rf_gain)
    self.shared_queue_control.put(jsonToUnicode({"rf_gain":self.rf_gain}))
    self.get_gain_range()

  def get_rf_gain(self):
    self.rf_gain = self.xmlrpc_server.get_rf_gain()
    self.shared_queue_control.put(jsonToUnicode({"rf_gain":self.rf_gain}))
    return self.rf_gain

  def get_gain_range(self):
    self.gain_range = [self.xmlrpc_server.get_rf_gain_start(), self.xmlrpc_server.get_rf_gain_step(), self.xmlrpc_server.get_rf_gain_stop()]
    self.shared_queue_control.put(jsonToUnicode({"gain_range":self.gain_range}))
    return self.gain_range    

  def get_all_statics(self):
    self.get_average()
    self.get_rate()
    self.get_tune_freq()
    self.get_samp_rate()
    self.get_precision()
    self.get_rf_gain()
    self.get_gain_range()

  def run(self):
    print "running data processor"
    while self.keep_running:
      msg_str = self.zmq_sub.recv()
      msg_str = msg_str[10:]
      #print "received message:", len(msg_str)

      n_frags = struct.unpack('!B', msg_str[0])[0] #obtain number of fragments
      frag_id = struct.unpack('!B', msg_str[1])[0] #obtain fragment number
      msg_str = msg_str[2:] #grab fft data
      #print 'n_frags', n_frags, 'frag_id', frag_id

      if n_frags == 1: #single fragment
        try:
          fft_data = np.fromstring(msg_str, self.data_type)

          if len(self.max_fft_data) != len(fft_data):
              self.max_fft_data = fft_data

          if self.strt:
              self.max_fft_data = fft_data
              self.strt = False

          # pass data
          self.shared_queue_data.put(msg_str)
            
        except Exception, e:
          exc_type, exc_obj, exc_tb = sys.exc_info()
          print ("singleframe error (%s) %s line %s" % (str(e), exc_type, exc_tb.tb_lineno))

      else: #multiple fragments situation
        self.reasembled_frame += msg_str
        if frag_id == n_frags - 1: #final fragment
          try:
            fft_data = np.fromstring(self.reasembled_frame, self.data_type)

            if len(self.max_fft_data) != len(fft_data):
                self.max_fft_data = fft_data

            if self.strt:
                self.max_fft_data = fft_data
                self.strt = False

            # pass data
            self.shared_queue_data.put(self.reasembled_frame)

            self.reasembled_frame = ''
          except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print ("multiframe error (%s) %s line %s" % (str(e), exc_type, exc_tb.tb_lineno))
            self.reasembled_frame = ''
        else:
            pass

    print "stopping data processor"


ws_clients_control = []
class controlWShandler(WebSocket):

  def handleMessage(self):
    for client in ws_clients_control:
      if client != self:
        client.sendMessage(self.address[0] + u' - ' + self.data)

  def handleConnected(self):
    print(self.address, 'control connected')
    #send initial data - tune_freq samp_rate average rate and precision
    for client in ws_clients_control:
      client.sendMessage(self.address[0] + u' - control connected')
    ws_clients_control.append(self)
    _data_processor.get_all_statics()

  def handleClose(self):
    ws_clients_control.remove(self)
    print(self.address, 'control closed')
    for client in ws_clients_control:
      client.sendMessage(self.address[0] + u' - control disconnected')

ws_clients_data = []
class datalWShandler(WebSocket):

  def handleMessage(self):
    for client in ws_clients_data:
      if client != self:
        client.sendMessage(self.address[0] + u' - ' + self.data)

  def handleConnected(self):
    print(self.address, 'data connected')
    #send initial data - tune_freq samp_rate average rate and precision
    for client in ws_clients_data:
      client.sendMessage(self.address[0] + u' - data connected')
    ws_clients_data.append(self)

  def handleClose(self):
    ws_clients_data.remove(self)
    print(self.address, 'data closed')
    for client in ws_clients_data:
      client.sendMessage(self.address[0] + u' - data disconnected')

class ws_server_runner(threading.Thread):
  def __init__(self, ws_server, ws_server_id):
    threading.Thread.__init__(self)
    self.ws_server = ws_server
    self.ws_server_id = ws_server_id
    self.keep_running = True

  def run(self):
    print "starting ws server", self.ws_server_id
    while self.keep_running:
      self.ws_server.serveonce()
    print "stopping ws server", self.ws_server_id


class ws_dispatcher(threading.Thread):
  def __init__(self, shared_queue, ws_clients, ws_server_id):
    threading.Thread.__init__(self)
    self.shared_queue = shared_queue
    self.ws_clients = ws_clients
    self.ws_server_id = ws_server_id
    self.keep_running = True

  def run(self):
    print "starting ws dispatcher ", self.ws_server_id
    while self.keep_running:
      while not self.shared_queue.empty():
        data = self.shared_queue.get()
        for client in self.ws_clients:
          if client != self:
            client.sendMessage(data)
      time.sleep(1e-3)
    print "stopping ws dispatcher ", self.ws_server_id

if __name__ == '__main__':

  parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
  parser.add_option("--serverIP", default='127.0.0.1', type='string', action="store", dest="serverIP", help="rpc and zmq server address")
  parser.add_option("--rpcport", default=7658, type='int', action="store", dest="rpcport", help="xmlrpc port")
  parser.add_option("--zmqport", default=5005, type='string', action="store", dest="zmqport", help="PORT of ZMQ publisher")
  parser.add_option("--ssl", default=0, type='int', action="store", dest="ssl", help="ssl (1: on, 0: off (default))")
  parser.add_option("--cert", default='./cert.pem', type='string', action="store", dest="cert", help="cert (./cert.pem)")
  parser.add_option("--key", default='./key.pem', type='string', action="store", dest="key", help="key (./key.pem)")
  parser.add_option("--ver", default=ssl.PROTOCOL_TLSv1, type=int, action="store", dest="ver", help="ssl version")

  (options, args) = parser.parse_args()

  shared_queue_control = Queue.Queue(5)
  shared_queue_data = Queue.Queue(10)

  signal.signal(signal.SIGINT, signal_handler)

  xmlrpc_server = xmlrpclib.Server("http://" + options.serverIP + ":"+str(options.rpcport))
  while True:
    try:
      dummy = xmlrpc_server.get_samp_rate()
    except:
      print 'rxmlrpc offline?', "http://" + options.serverIP + ":"+str(options.rpcport)
      time.sleep(3)
      pass
    else:
      print 'rxmlrpc okay!', "http://" + options.serverIP + ":"+str(options.rpcport)
      break

  ws_control_port = 9000
  ws_data_port = 8000

  if options.ssl == 1:
    ws_server_control = SimpleSSLWebSocketServer("", ws_control_port, controlWShandler, options.cert, options.key, version=options.ver)
    ws_server_data = SimpleSSLWebSocketServer("", ws_data_port, dataWShandler, options.cert, options.key, version=options.ver)
  else:
    ws_server_control = SimpleWebSocketServer("", ws_control_port, controlWShandler)
    ws_server_data = SimpleWebSocketServer("", ws_data_port, datalWShandler)

  _ws_server_control_runner = ws_server_runner(ws_server_control, 'control')
  _ws_server_control_runner.start()

  _ws_server_data_runner = ws_server_runner(ws_server_data, 'data')
  _ws_server_data_runner.start()

  _ws_dispatcher_control = ws_dispatcher(shared_queue_control, ws_clients_control, 'control')
  _ws_dispatcher_control.start()

  _ws_dispatcher_data = ws_dispatcher(shared_queue_data, ws_clients_data, 'data')
  _ws_dispatcher_data.start()

  _data_processor = data_processor(options.serverIP, options.zmqport, shared_queue_control, shared_queue_data, xmlrpc_server)
  _data_processor.start()
  
  print 'server okay!', "http://127.0.0.1:8080"

  print 'main process'

  # RUN
  cherrypy.quickstart(web_site(_data_processor, ws_control_port, ws_data_port), '/',  config = 'cherrypy.conf')