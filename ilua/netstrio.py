# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

import io
import re
import math

__version__ = "0.1.0"

class NetstringError(Exception):
    pass

class NetstringIO(object):
    MAX_NETSTR_LENGTH = 99999
    _LENGTH_FORMAT = re.compile("[1-9][0-9]*")

    def __init__(self, raw):
        self.raw = raw
    
    def read_netstring(self):
        length_buffer = []
        while True:
            char_read = self.raw.read(1)
            if not char_read:
                raise NetstringError("Reached EOF while parsing length")
            if char_read == b":":
                break
            length_buffer.append(char_read)
            if len(length_buffer) > self._calc_length_limit():
                raise NetstringError("Length format exceeds "\
                                     "log10(MAX_NETSTR_LENGTH)")
        
        if len(length_buffer) == 0:
            raise NetstringError("Length is empty")
        
        length = b"".join(length_buffer).decode("ascii")
        if not self._LENGTH_FORMAT.match(length) and length != "0":
            raise NetstringError("Length is invalid")
        
        length = int(length)
        if length > self.MAX_NETSTR_LENGTH:
            raise NetstringError("Length exceeds MAX_NETSTR_LENGTH")
        
        data = self.raw.read(length)
        if not data:
            raise NetstringError("Reached EOF while reading data")
        
        if self.raw.read(1) != b",":
            raise NetstringError("Could not read ending character")
        
        return data

    def write_netstring(self, data):
        # TODO: enfoce length?
        return self.raw.write(bytes(str(len(data)).encode("ascii")) + b":" + data + b",")
    
    def __getattr__(self, attr):
        return getattr(self.raw, attr)

    @classmethod
    def _calc_length_limit(cls):
        return math.ceil(math.log10(cls.MAX_NETSTR_LENGTH))
