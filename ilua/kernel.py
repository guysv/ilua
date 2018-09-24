import json
import os
import functools
import threading

from twisted.internet import reactor, protocol, defer, threads
from txkernel.kernelbase import KernelBase
from txkernel.kernelapp import PassiveKernelApp

if os.name == "posix":
    from ._unixfifo import Fifo as Pipe
elif os.name == "nt":
    from ._win32namedpipe import NamedPipe as Pipe
else:
    raise RuntimeError("os.name {} is not supported".format(os.name))

INTERPRETER_SCRIPT = os.path.join(os.path.dirname(__file__), "interp.lua")
LUALIBS_PATH = os.path.join(os.path.dirname(__file__), "lualibs")

class OutputCapture(protocol.ProcessProtocol):
    def __init__(self, message_sink):
        self.message_sink = message_sink
    
    def connectionMade(self):
        self.transport.closeStdin()
    
    def outReceived(self, data):
        self.message_sink("stdout", data.decode("utf-8"))
    
    def errReceived(self, data):
        self.message_sink("stdout", data.decode("utf-8"))

class ILuaKernel(KernelBase):
    implementation = 'ILua'
    implementation_version = '1.0'
    language = "lua"
    lanugae_version = "n/a"
    language_info = {
        'name': 'Lua',
        'mimetype': 'text/plain',
        'file_extension': '.lua'
    }
    banner = "placehoderr.."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log.debug("Opening pipes")
        # Pipe setup
        self.cmd_pipe = Pipe.cmd_pipe()
        self.ret_pipe = Pipe.ret_pipe()

        self.pipes_lock = threading.Lock()

        # Lua process setup
        self.log.debug("Launching child lua")
        def message_sink(stream, data):
            return self.send_update("stream", {"name": stream, "text": data})
        proto = OutputCapture(message_sink)
        reactor.spawnProcess(proto, 'lua', ['lua', INTERPRETER_SCRIPT,
                                            self.cmd_pipe.path,
                                            self.ret_pipe.path,
                                            LUALIBS_PATH])
        
        self.cmd_pipe.connect()
        self.ret_pipe.connect()

        test_payload = "feedacdc"
        self.cmd_pipe.stream.write_netstring(json.dumps({"type": "echo",
                                                         "payload": test_payload}).encode("utf-8"))
        self.cmd_pipe.stream.flush()

        self.log.debug("Wrote test message to cmd_pipe")    
        if json.loads(self.ret_pipe.stream.read_netstring())["payload"] != test_payload:
            raise Exception("placeholder")
        self.log.debug("Read test message from ret_pipe")

    def send_message(self, message):
        message_json = json.dumps(message).encode("utf-8")

        self.pipes_lock.acquire()
        self.cmd_pipe.stream.write_netstring(message_json)
        self.cmd_pipe.stream.flush()
        self.pipes_lock.release()

        return json.loads(self.ret_pipe.stream.read_netstring())
    
    @defer.inlineCallbacks
    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        self.execution_count += 1

        result = yield threads.deferToThread(self.send_message,
                                             {"type": "execute",
                                             "payload": code})
        
        if result["payload"]["success"]:
            self.send_update("execute_result", {
                'execution_count': self.execution_count,
                'data': {
                    'text/plain': "\t".join(result['payload']['returned'])
                },
                'metadata': {}
            })
        
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }
        else:
            self.send_update("error", {
                'execution_count': self.execution_count,
                'traceback': result['payload']['returned'],
                'ename': 'n/a',
                'evalue': 'n/a'
            })

            return {
                'status': 'error',
                'execution_count': self.execution_count,
                'traceback': result['payload']['returned'],
                'ename': 'n/a',
                'evalue': 'n/a'
            }
    
    @defer.inlineCallbacks
    def do_is_complete(self, code):
        result = yield threads.deferToThread(self.send_message,
                                             {"type": "is_complete",
                                             "payload": code})
        
        if result['payload']['complete']:
            return {'status': 'complete'}
        else:
            return {'status': 'incomplete'}
        
if __name__ == '__main__':
    PassiveKernelApp(ILuaKernel).run()
