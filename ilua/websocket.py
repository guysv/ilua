import ipaddress
from sqlite3 import connect
from twisted.internet import abstract, defer, fdesc, task
import json
import queue
from urllib import response
from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory
from twisted.internet import protocol, defer
from twisted.protocols import basic
from twisted.logger import Logger
    

class WSClientProtocol(WebSocketClientProtocol):
    log = Logger()
    queue = defer.DeferredQueue()

    def onConnect(self, response):
        self.log.debug("Server connected: {0}".format(response.peer))

    def onConnecting(self, transport_details):
        self.log.debug("Connecting; transport details: {}".format(transport_details))
        return None  # ask for defaults

    def onOpen(self):
        self.log.debug("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            return
        response = json.loads(payload.decode("utf8", "ignore"))
        self.queue.put(response)

    def onClose(self, wasClean, code, reason):
        self.log.debug("WebSocket connection closed: {0}".format(reason))

    def sendRequest(self, request):
        """
        Send a request to the child interpreter,
        and wait for response
        
        :param request: request object (dict)
        :type request: dict
        :return: response
        :rtype: dict
        """
        request = json.dumps(request).encode("utf8")
        self.sendMessage(request)
        return self.queue.get()