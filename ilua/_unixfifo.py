# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv3.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-3.0.txt
# for full license details.

import os
import os.path

from jupyter_core.paths import jupyter_runtime_dir
from .pipebase import PipeBase
from .netstrio import NetstringIO

class Fifo(PipeBase):
    def __init__(self, name_suffix, outbound):
        self.path = os.path.join(jupyter_runtime_dir(),
                                 "{}_{}".format(name_suffix,
                                                os.getpid()))
        
        os.mkfifo(self.path)

        self._mode = "wb" if outbound else "rb"

    def connect(self):
        self.stream = NetstringIO(open(self.path, self._mode))

    def close(self):
        self.stream.close()
        os.remove(self.path)
