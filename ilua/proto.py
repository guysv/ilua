import json

from twisted.internet import protocol, defer
from twisted.protocols import basic
from twisted.logger import Logger

class OutputCapture(protocol.ProcessProtocol):
    log = Logger()

    def __init__(self, message_sink):
        self.message_sink = message_sink

    def connectionMade(self):
        self.log.debug("Process is running")
        self.transport.closeStdin()

    def outReceived(self, data):
        data_utf8 = data.decode("utf-8")
        self.log.debug("Received stdout data: {data}", data=repr(data_utf8))
        self.message_sink("stdout", data_utf8)

    def errReceived(self, data):
        data_utf8 = data.decode("utf-8")
        self.log.debug("Received stdout data: {data}", data=repr(data_utf8))
        self.message_sink("stderr", data_utf8)

class InterpreterProtocol(basic.NetstringReceiver):
    log = Logger()
    queue = defer.DeferredQueue()

    def connectionMade(self):
        self.log.debug("Interpreter connections eastablished")
    
    def stringReceived(self, string):
        response = json.loads(string.decode("utf8", "ignore"))
        self.responseReceived(response)
    
    def sendRequest(self, request):
        request = json.dumps(request).encode("utf-8")
        self.sendString(request)
        return self.queue.get()
    
    def responseReceived(self, response):
        self.queue.put(response)