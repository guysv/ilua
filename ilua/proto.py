# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
This module hosts the various twisted
protocols used during communiction with
lua subprocess
"""

import json

from twisted.internet import protocol, defer
from twisted.protocols import basic
from twisted.logger import Logger

class OutputCapture(protocol.ProcessProtocol):
    """
    A protocol for capturing and logging any
    output coming out from attached process
    """

    log = Logger()

    def __init__(self, message_sink):
        """
        :param message_sink: output handler
        :type message_sink: function
        """

        self.message_sink = message_sink

    def connectionMade(self):
        self.log.debug("Process is running")
        self.transport.closeStdin()

    def outReceived(self, data):
        self.log.debug("Received stdout data: {data}", data=repr(data))
        self.message_sink("stdout", data.decode("utf8", "replace"))

    def errReceived(self, data):
        self.log.debug("Received stdout data: {data}", data=repr(data))
        self.message_sink("stderr", data.decode("utf8", "replace"))

class InterpreterProtocol(basic.NetstringReceiver):
    """
    Child (Lua) interpreter command protocol
    This class shapes the communication API
    into a single method used to command the
    interpreter
    """

    log = Logger()
    queue = defer.DeferredQueue()

    def connectionMade(self):
        self.log.debug("Interpreter connections eastablished")
    
    def stringReceived(self, string):
        response = json.loads(string.decode("utf8", "ignore"))
        self.responseReceived(response)
    
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
        self.sendString(request)
        return self.queue.get()
    
    def responseReceived(self, response):
        """
        Called whenever a new response arrives
        
        :param response: response object
        :type response: dict
        """

        self.queue.put(response)