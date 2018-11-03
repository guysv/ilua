import os
from jupyter_console.app import launch_new_instance
from txkernel.kernelapp import KernelApp
from .kernel import ILuaKernel

class ILuaApp(KernelApp):
    ENV_VAR_PREFIX = "ILUA_"

    def __init__(self, *args, **kwargs):
        super(ILuaApp, self).__init__(ILuaKernel, *args, **kwargs)
        self.parser.add_argument("-i", "--lua-interpreter", metavar="LUA",
                                 default=self._get_default("LUA_INTERPRETER",
                                                           'lua'),
                                 help="Lua interpreter to use for code "
                                      "evaluations")

def main():
    if os.name == "nt":
        import signal
        signal.signal(signal.SIGINT, lambda *args: None)
    ILuaApp().run()

if __name__ == '__main__':
    main()
