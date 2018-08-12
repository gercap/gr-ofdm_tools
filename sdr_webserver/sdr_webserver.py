# encoding: utf-8

import socket, Queue, os, sys, time, struct, signal
from threading import Thread
import Queue
import cherrypy, simplejson
from jinja2 import Environment, FileSystemLoader
import numpy as np

log_levels = {"CRITICAL":50, "ERROR":40, "WARNING":30, "INFO":20, "DEBUG":10}

# GET CURRENT DIRECTORY
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
env=Environment(loader=FileSystemLoader(CUR_DIR), trim_blocks=True)
MAX_LO_MTU = 65535

def signal_handler(signal, frame):
  global keep_running

  keep_running = False
  _data_processor.join()
  sys.exit(0)

class web_site(object):
    def __init__(self, shared_queue):
      self.shared_queue = shared_queue

    @cherrypy.expose
    def get_fft_data(self):
      cherrypy.response.headers['Content-Type'] = 'application/json'
      if not self.shared_queue.empty():
        (axis, fft_data) = self.shared_queue.get()
        return simplejson.dumps({"axis": axis.tolist(), "fft_data":fft_data.tolist()})

    @cherrypy.expose
    def index(self):

      template = env.get_template('./public/html/index.html')
      return template.render(
        now=time.strftime("%H:%M:%S"),
        description='Web based SDR',
        site_title="Web SDR tests")

class data_processor(Thread):
  def __init__(self, UDP_IP, UDP_PORT, shared_queue):
    Thread.__init__(self)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    self.sock.bind((UDP_IP, UDP_PORT))
    self.shared_queue = shared_queue

    self.sample_rate = 1
    self.tune_freq = 0
    self.reasembled_frame = ''
    self.precision = True
    if self.precision:
        self.data_type = np.float32
    else:
        self.data_type = np.float16
    self.max_fft_data = np.array([])
    self.strt = True

    self.keep_running = True

  def run(self):

    while keep_running:
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
          axis = self.sample_rate/2.0*np.linspace(-1, 1, len(fft_data)) + self.tune_freq
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
            axis = self.sample_rate/2.0*np.linspace(-1, 1, len(fft_data)) + self.tune_freq
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


if __name__ == '__main__':

  keep_running = True
  UDP_IP = "127.0.0.1"
  UDP_PORT = 5005

  signal.signal(signal.SIGINT, signal_handler)

  shared_queue = Queue.Queue(10)

  _data_processor = data_processor(UDP_IP, UDP_PORT, shared_queue)
  _data_processor.start()

  # RUN
  #cherrypy.quickstart(web_site(), '/',  config = 'cherrypy.conf')
  cherrypy.config.update(config = 'cherrypy.conf')
  cherrypy.tree.mount(web_site(shared_queue), '/', config = 'cherrypy.conf')
  if hasattr(cherrypy.engine, "signal_handler"):
      cherrypy.engine.signal_handler.subscribe()
  if hasattr(cherrypy.engine, "console_control_handler"):
      cherrypy.engine.console_control_handler.subscribe()

  cherrypy.engine.start()
  cherrypy.engine.block()

import cherrypy
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import EchoWebSocket

cherrypy.config.update({'server.socket_port': 9000})
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

class Root(object):
    @cherrypy.expose
    def index(self):
        return 'some HTML with a websocket javascript connection'

    @cherrypy.expose
    def ws(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler

cherrypy.quickstart(Root(), '/', config={'/ws': {'tools.websocket.on': True,
                                                 'tools.websocket.handler_cls': EchoWebSocket}})
