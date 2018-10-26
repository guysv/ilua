# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

import os
from ..netstrio import NetstringIO
if os.name == "posix":
    # pylint: disable=E0401
    from ._unixfifo import Fifo as Pipe
elif os.name == "nt":
    # pylint: disable=E0401
    from ._win32namedpipe import NamedPipe as Pipe
else:
    raise RuntimeError("os.name {} is not supported".format(os.name))

class NetstringPipe(Pipe):
    def connect(self):
        super(NetstringPipe, self).connect()
        self.stream = NetstringIO(self.stream)
