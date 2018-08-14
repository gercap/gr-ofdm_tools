from gevent import monkey; monkey.patch_all()
import gevent
 
from ws4py.server.geventserver import WebSocketServer
from ws4py.websocket import WebSocket
 
# Construct an array of 256 bytes, 0x00 to 0xff
bytes = b""
for i in range(256):
    bytes += chr(i)
 
class MyWebSocket(WebSocket):
    def opened(self):
        print "Socket opened"
 
    def received_message(self, message):
        "Handle requests. Echo is echoed, bytes is a request for binary data"
        print "Received message of length %d" % len(message)
        if message.data.startswith("Echo"):
            self.send(message.data, message.is_binary)
        if message.data == "bytes":
            self.send(bytes, True)
 
    def closed(self, code, reason):
        print "Socket closed %s %s" % (code, reason)
 
server = WebSocketServer(('127.0.0.1', 9001), websocket_class=MyWebSocket)
server.serve_forever()