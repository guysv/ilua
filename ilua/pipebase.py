class PipeBase(object):
    @classmethod
    def cmd_pipe(cls):
        return cls("cmd", True)
    
    @classmethod
    def ret_pipe(cls):
        return cls("ret", False)