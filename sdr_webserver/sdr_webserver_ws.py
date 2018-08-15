# encoding: utf-8

import socket, Queue, os, sys, time, struct, signal
from threading import Thread
import Queue
import cherrypy, simplejson
from jinja2 import Environment, FileSystemLoader
import numpy as np
import xmlrpclib

import ssl
from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer, SimpleSSLWebSocketServer
from optparse import OptionParser

log_levels = {"CRITICAL":50, "ERROR":40, "WARNING":30, "INFO":20, "DEBUG":10}

# GET CURRENT DIRECTORY
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
env=Environment(loader=FileSystemLoader(CUR_DIR), trim_blocks=True)
MAX_LO_MTU = 65535

def signal_handler(signal, frame):
  print "you pressed ctrl-C!"
  _ws_server_runner.keep_running = False
  _ws_dispatcher.keep_running = False
  _data_processor.keep_running = False
  ws_server.close()
  sys.exit(0)

class web_site(object):
    def __init__(self, data_processor, xmlrpc_server, ssl=False):
      self.xmlrpc_server = xmlrpc_server
      self.data_processor = data_processor
      self.scheme = 'wss' if ssl else 'ws'

    @cherrypy.expose
    def set_rate(self, rate):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.xmlrpc_server.set_rate(float(rate))

    @cherrypy.expose
    def set_average(self, average):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      self.xmlrpc_server.set_av(float(average))

    @cherrypy.expose
    def set_precision(self, precision):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      if precision == "True":
        self.xmlrpc_server.set_precision(True)
        self.data_processor.set_precision(True)
      else:
        self.xmlrpc_server.set_precision(False)
        self.data_processor.set_precision(False)

    @cherrypy.expose
    def index(self):

      template = env.get_template('./public/html/index_ws.html')
      return template.render(
        now=time.strftime("%H:%M:%S"),
        description='Web based SDR',
        site_title="Web SDR tests",
        scheme=self.scheme)

class data_processor(Thread):
  def __init__(self, UDP_IP, UDP_PORT, shared_queue, xmlrpc_server):
    Thread.__init__(self)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    self.sock.bind((UDP_IP, UDP_PORT))
    self.shared_queue = shared_queue
    self.xmlrpc_server = xmlrpc_server

    self.sample_rate = self.xmlrpc_server.get_samp_rate()
    self.tune_freq = self.xmlrpc_server.get_tune_freq()

    self.reasembled_frame = ''
    self.precision = self.xmlrpc_server.get_precision()
    if self.precision:
        self.data_type = np.float32
    else:
        self.data_type = np.float16
    self.max_fft_data = np.array([])
    self.strt = True

    self.keep_running = True

  def set_precision(self, precision):
    if precision:
        self.data_type = np.float32
    else:
        self.data_type = np.float16

  def run(self):

    while self.keep_running:
      msg_str, addr = self.sock.recvfrom(MAX_LO_MTU) # buffer size is 1024 bytes
      #print "received message:", msg_str

      n_frags = struct.unpack('!B', msg_str[0])[0] #obtain number of fragments
      frag_id = struct.unpack('!B', msg_str[1])[0] #obtain fragment number
      msg_str = msg_str[2:] #grab fft data

      if n_frags == 1: #single fragment
        try:
          fft_data = np.fromstring(self.reasembled_frame, self.data_type)

          if len(self.max_fft_data) != len(fft_data):
              self.max_fft_data = fft_data

          if self.strt:
              self.max_fft_data = fft_data
              self.strt = False

          # pass data
          axis = np.around(self.sample_rate/2.0*np.linspace(-1, 1, len(fft_data)) + self.tune_freq, decimals=3)
          self.shared_queue.put((axis, fft_data))

          #axis = sample_rate/2*np.linspace(-1, 1, len(fft_data)) + tune_freq
          #self.max_fft_data = np.maximum(self.max_fft_data, fft_data)
          #curve_data[0] = (axis/1e6, fft_data);
          #if hold_max: curve_data[1] = (axis/1e6, self.max_fft_data);
            
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
            axis = np.around(self.sample_rate/2.0*np.linspace(-1, 1, len(fft_data)) + self.tune_freq, decimals=3)
            self.shared_queue.put((axis, fft_data))
            
            #self.max_fft_data = np.maximum(self.max_fft_data, fft_data)
            #curve_data[1] = (axis/1e6, fft_data);
            #if hold_max: curve_data[0] = (axis/1e6, self.max_fft_data);

            self.reasembled_frame = ''
          except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print ("multiframe error (%s) %s line %s" % (str(e), exc_type, exc_tb.tb_lineno))
            self.reasembled_frame = ''
        else:
            pass

ws_clients = []
class simpleWShandler(WebSocket):

  def handleMessage(self):
    for client in ws_clients:
      if client != self:
        client.sendMessage(self.address[0] + u' - ' + self.data)

  def handleConnected(self):
    print(self.address, 'connected')
    for client in ws_clients:
      client.sendMessage(self.address[0] + u' - connected')
    ws_clients.append(self)

  def handleClose(self):
    ws_clients.remove(self)
    print(self.address, 'closed')
    for client in ws_clients:
      client.sendMessage(self.address[0] + u' - disconnected')

class ws_server_runner(Thread):
  def __init__(self, ws_server):
    Thread.__init__(self)
    self.ws_server = ws_server
    self.keep_running = True

  def run(self):
    print "starting ws server"
    while self.keep_running:
      self.ws_server.serveonce()
      time.sleep(1)

class ws_dispatcher(Thread):
  def __init__(self, shared_queue):
    Thread.__init__(self)
    self.shared_queue = shared_queue
    self.keep_running = True

  def run(self):
    print "starting ws ws dispatcher"
    while self.keep_running:
      while not self.shared_queue.empty():
        (axis, fft_data) = self.shared_queue.get()
        u = unicode(simplejson.dumps({"plot_data":{"axis": axis.tolist(), "fft_data":fft_data.tolist()}}), "utf-8")
        for client in ws_clients:
          if client != self:
            client.sendMessage(u)
      time.sleep(1e-3)



if __name__ == '__main__':

  keep_running = True

  parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
  parser.add_option("--host", default='', type='string', action="store", dest="host", help="ws hostname (localhost)")
  parser.add_option("--port", default=9000, type='int', action="store", dest="port", help="ws port (9000)")
  parser.add_option("--rpchost", default='127.0.0.1', type='string', action="store", dest="rpchost", help="rpc server hostname (localhost)")
  parser.add_option("--rpcport", default=7658, type='int', action="store", dest="rpcport", help="xml rpc server (127.0.0.1)")
  parser.add_option("--ssl", default=0, type='int', action="store", dest="ssl", help="ssl (1: on, 0: off (default))")
  parser.add_option("--cert", default='./cert.pem', type='string', action="store", dest="cert", help="cert (./cert.pem)")
  parser.add_option("--key", default='./key.pem', type='string', action="store", dest="key", help="key (./key.pem)")
  parser.add_option("--ver", default=ssl.PROTOCOL_TLSv1, type=int, action="store", dest="ver", help="ssl version")

  (options, args) = parser.parse_args()

  UDP_IP = "0.0.0.0"
  UDP_PORT = 5005

  shared_queue = Queue.Queue(10)

  signal.signal(signal.SIGINT, signal_handler)

  if options.ssl == 1:
    ws_server = SimpleSSLWebSocketServer(options.host, options.port, simpleWShandler, options.cert, options.key, version=options.ver)
  else:
    ws_server = SimpleWebSocketServer(options.host, options.port, simpleWShandler)

  _ws_server_runner = ws_server_runner(ws_server)
  _ws_server_runner.start()

  _ws_dispatcher = ws_dispatcher(shared_queue)
  _ws_dispatcher.start()

  xmlrpc_server = xmlrpclib.Server("http://" + options.rpchost + ":"+str(options.rpcport))
  while True:
    try:
      dummy = xmlrpc_server.get_samp_rate()
    except:
      print 'server offline?', "http://" + options.rpchost + ":"+str(options.rpcport)
      time.sleep(3)
      pass
    else:
      print 'server okay!', "http://" + options.rpchost + ":"+str(options.rpcport)
      break

  _data_processor = data_processor(UDP_IP, UDP_PORT, shared_queue, xmlrpc_server)
  _data_processor.start()

  # RUN
  cherrypy.quickstart(web_site(_data_processor, xmlrpc_server), '/',  config = 'cherrypy.conf')