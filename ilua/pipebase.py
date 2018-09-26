# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv3.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-3.0.txt
# for full license details.

class PipeBase(object):
    def connect(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    @classmethod
    def cmd_pipe(cls):
        return cls("cmd", True)
    
    @classmethod
    def ret_pipe(cls):
        return cls("ret", False)