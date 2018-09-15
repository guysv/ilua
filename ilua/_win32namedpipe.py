import os
import msvcrt
import win32pipe
import win32con
import win32security

class Win32NamedPipe(object):
    def __init__(self, name_suffix, outbound):
        self.path = ur"\\.\pipe\{}_{}".format(name_suffix, os.getpid())

        direction = win32con.PIPE_ACCESS_OUTBOUND if outbound else \
            win32con.PIPE_ACCESS_INBOUND

        # TODO: we probebly want to limit access for current user
        security_attribs = win32security.SECURITY_ATTRIBUTES()

        self._handle = win32pipe.CreateNamedPipe(self.path, direction,
                                                 win32con.PIPE_TYPE_BYTE,
                                                 1, 0, 0, 2000, # Arbitrary?
                                                 security_attribs)

        direction = os.O_APPEND if outbound else os.O_RDONLY
        fd = msvcrt.open_osfhandle(int(self._handle), direction)

        direction = "wb" if outbound else "rb"
        self.stream = os.fdopen(fd, direction)

    def connect(self):
        win32pipe.ConnectNamedPipe(self._handle, None)
        # TODO: echo routine?

    def close():
        self._handle.close()
