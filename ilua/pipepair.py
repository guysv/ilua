import os
from .error import UnsupportedPlatform
if os.name == "unix":
    from ._unixfifo import Fifo as Pipe
elif os.name == "nt":
    from ._win32namedpipe import NamedPipe as Pipe
else:
    raise UnsupportedPlatform("os.name{} is not supported"\
                              .format(os.name))

class PipePair(object):
    def __init__(self):
        self.cmd_pipe = Pipe.cmd_pipe()
        self.ret_pipe = Pipe.ret_pipe()
    
    def connect(self):
        self.cmd_pipe.connect()
        self.ret_pipe.connect()

        self.cmd_pipe.stream.write_netstring()