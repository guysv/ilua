from txkernel.kernelapp import KernelApp

class ILuaApp(KernelApp):
    def __init__(self, *args, **kwargs):
        super(ILuaApp, self).__init__(*args, **kwargs)
        self.parser.add_argument("-l", "--lua-interpreter")