import os
import os.path

from jupyter_core.paths import jupyter_runtime_dir

class UnixFifo(object):
    def __init__(self, name_suffix):
        self.path = os.path.join(jupyter_runtime_dir(),
                                 "{}_{}".format(name_suffix,
                                                os.getpgid()))
        self.pipe = os.mkfifo(self.path)
    
    def connect(self):
        pass # TODO: echo..
    
    def close(self):
        self.pipe.close()
        os.remove(self.path)
