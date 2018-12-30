# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
UNIX FIFO class implemented as a twisted FileDescriptor to allow async
reading of named pipes on unix

Tested on linux, thoughts and prayers for other UNIXes
"""

import os
import errno
from jupyter_core.paths import jupyter_runtime_dir
from twisted.internet import abstract, defer, fdesc, task


def get_pipe_path(name):
    """
    Generate a FIFO path from name on unix
    """
    return os.path.join(jupyter_runtime_dir(),
                        "ilua_{}_{}".format(name, os.getpid()))

class UnixFifo(abstract.FileDescriptor):
    """
    Async IO implementation for UNIX FIFOs
    """
    def __init__(self, path, mode, reactor=None):
        """
        :param path: Path to pipe (not existing yet)
        :type path: string
        :param mode: Read (r) or write (w) modes,
        :type mode: string
        :param reactor: Used reactor, defaults to None
        :param reactor: twisted.internet.posixbase.PosixReactorBase, optional
        """

        super(UnixFifo, self).__init__(reactor=reactor)
        self.path = path
        os.mkfifo(self.path)

        self.mode = mode
        self._actual_mode = os.O_NONBLOCK
        if 'r' in self.mode:
            self._actual_mode |= os.O_RDONLY
        elif 'w' in self.mode:
            self._actual_mode |= os.O_WRONLY
        else:
            raise ValueError("mode must be 'r' or 'w'")
    
    def dataReceived(self, data):
        pass
    
    def _try_open(self):
        """
        Try to open the FIFO, might not work when opening for writing with
        ENXIO error which means that we should try again according to fifo(7)
        """

        try:
            fileno = os.open(self.path, self._actual_mode)
            self.fileno = lambda: fileno
            self._open_loop.stop()
        except OSError as e:
            if e.errno != errno.ENXIO:
                raise
    
    @defer.inlineCallbacks
    def open(self):
        """
        Open FIFO, starts up reading/writing

        :return: a deferred firing when FIFO is opened
        :rtype: twisted.internet.deferred.Deferred
        """

        self._open_loop = task.LoopingCall(self._try_open)
        # HACK: I failed to figure out how to open a fifo for write
        #       without polling.. This could panelize startup time
        yield self._open_loop.start(0.01, False)
        
        self.startReading()
        self.connected = 1
    
    def doRead(self):
        return fdesc.readFromFD(self.fileno(), self.dataReceived)
    
    def writeSomeData(self, data):
        return fdesc.writeToFD(self.fileno(), data)
    
    def connectionLost(self, reason):
        super(UnixFifo, self).connectionLost(reason)
        os.close(self.fileno())
        os.remove(self.path)