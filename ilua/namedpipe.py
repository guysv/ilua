# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
Cross-platform dual-pipes twisted
transport implementation
"""

import os
from twisted.internet import defer
if os.name == "posix":
    # pylint: disable=E0401
    from ._unixfifo import UnixFifo as NamedPipe, get_pipe_path
elif os.name == "nt":
    # pylint: disable=E0401
    from ._win32namedpipe import Win32NamedPipe as NamedPipe, get_pipe_path
else:
    raise RuntimeError("os.name {} is not supported".format(os.name))

class PipeAddress(object):
    """
    Some dummy object required by twisted
    """
    pass

class CoupleOPipes(object):
    """
    Duplex transport over dual named pipes,
    one for incoming data and one for outgoing
    This object can be used as a transport
    for twisted protocols.

    Implements twisted.internet.iterfaces.ITransport
    """

    def __init__(self, in_pipe_path, out_pipe_path, reactor=None):
        if reactor is None:
            from twisted.internet import reactor
        self.in_pipe = NamedPipe(in_pipe_path, "r", reactor)
        self.out_pipe = NamedPipe(out_pipe_path, "w", reactor)

        self.disconnecting = 0

    @defer.inlineCallbacks
    def connect(self, protocolFactory):
        in_opened = self.in_pipe.open()
        out_opened = self.out_pipe.open()
        yield in_opened
        yield out_opened

        proto = protocolFactory.buildProtocol(PipeAddress())
        self.in_pipe.dataReceived = lambda data: proto.dataReceived(data)
        proto.makeConnection(self)
        defer.returnValue(proto)

    def write(self, data):
        self.out_pipe.write(data)

    def writeSequence(self, data):
        self.out_pipe.writeSequence(data)

    def loseConnection(self):
        self.in_pipe.loseConnection()
        self.out_pipe.loseConnection()

        self.disconnecting = 1

    def getPeer(self):
        return PipeAddress()

    def getHost(self):
        return PipeAddress()
