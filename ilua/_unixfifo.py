import os
import errno
from twisted.internet import abstract, defer, fdesc, task

class UnixFifo(abstract.FileDescriptor):
    def __init__(self, path, mode, reactor=None):
        super(UnixFifo, self).__init__(reactor=reactor)
        self.path = path
        self.mode = mode
        self._actual_mode = os.O_NONBLOCK
        if 'r' in self.mode:
            self._actual_mode |= os.O_RDONLY
        elif 'w' in self.mode:
            self._actual_mode |= os.O_WRONLY
        else:
            raise ValueError("mode must be 'r' or 'w'")
    
    def pipeOpened(self):
        print(self.path + " opened")
    
    def dataReceived(self, data):
        pass
    
    def _try_open(self):
        try:
            fileno = os.open(self.path, self._actual_mode)
            self.fileno = lambda: fileno
            self._open_loop.stop()
        except OSError as e:
            if e.errno != errno.ENXIO:
                raise
    
    @defer.inlineCallbacks
    def open(self):
        os.mkfifo(self.path)
        
        self._open_loop = task.LoopingCall(self._try_open)
        # HACK: I failed to figure out how to open a fifo for write
        #       without polling.. This could panelize startup time
        yield self._open_loop.start(0.01, False)
        
        self.startReading()
        self.connected = 1
        
        self.pipeOpened()
    
    def doRead(self):
        return fdesc.readFromFD(self.fileno(), self.dataReceived)
    
    def writeSomeData(self, data):
        return fdesc.writeToFD(self.fileno(), data)
    
    def connectionLost(self, reason):
        super(UnixFifo, self).connectionLost(reason)
        os.close(self.fileno())