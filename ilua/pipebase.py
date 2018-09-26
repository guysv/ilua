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