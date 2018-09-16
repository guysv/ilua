import os
import os.path

from jupyter_core.paths import jupyter_runtime_dir
from .pipebase import PipeBase
from .netstrio import NetstringIO

class Fifo(PipeBase):
    def __init__(self, name_suffix, outbound):
        self.path = os.path.join(jupyter_runtime_dir(),
                                 "{}_{}".format(name_suffix,
                                                os.getpgid()))
        
        os.mkfifo(self.path)

        mode = "wb" if outbound else "rb"
        self.stream = NetstringIO.cast(open(self.path, mode))

    def connect(self):
        pass

    def close(self):
        self.stream.close()
        os.remove(self.path)
