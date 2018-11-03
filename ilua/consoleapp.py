import os
from jupyter_console.app import ZMQTerminalIPythonApp

from .app import ILuaApp

class ILuaConsoleApp(ILuaApp):
    def run(self):
        cli_args = vars(self.parser.parse_args())
        cli_args.pop("connection_file", None)

        os.environ.update({
            key.upper(): cli_args[key]
            for key in cli_args
        })

        # HACK: passing arguments to jupyter_console via command line
        #       because I have yet to figure out how to do it through
        #       IPython's fancy traitlets framework
        ZMQTerminalIPythonApp.launch_instance(argv=['--kernel', 'lua'])

if __name__ == '__main__':
    ILuaConsoleApp().run()