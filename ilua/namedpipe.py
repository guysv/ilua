import os
from twisted.internet import defer
if os.name == "posix":
    # pylint: disable=E0401
    from ._unixfifo import UnixFifo as NamedPipe
elif os.name == "nt":
    # pylint: disable=E0401
    from ._win32namedpipe import NamedPipe
else:
    raise RuntimeError("os.name {} is not supported".format(os.name))

class PipeAddress(object):
    pass

class CoupleOPipes(object):

    def __init__(self, in_pipe_path, out_pipe_path, reactor=None):
        if reactor is None:
            from twisted.internet import reactor
        self.in_pipe = NamedPipe(in_pipe_path, "r", reactor)
        self.out_pipe = NamedPipe(out_pipe_path, "w", reactor)

        self.disconnecting = 0

    @defer.inlineCallbacks    
    def connect(self, protocolFactory):
        yield self.in_pipe.open()
        yield self.out_pipe.open()

        proto = protocolFactory.buildProtocol(PipeAddress())
        def foo(data):
            print("Read: " + repr(data))
            proto.dataReceived(data)
        self.in_pipe.dataReceived = foo
        proto.transport = self
        defer.returnValue(proto)
    
    def write(self, data):
        print("Write: " + repr(data))
        self.out_pipe.write(data)
    
    def writeSequence(self, data):
        print("Write s: " + repr(data))
        self.out_pipe.writeSequence(data)
    
    def loseConnection(self):
        self.in_pipe.loseConnection()
        self.out_pipe.loseConnection()

        self.disconnecting = 1
    
    def getPeer(self):
        return PipeAddress()
    
    def getHost(self):
        return PipeAddress()
