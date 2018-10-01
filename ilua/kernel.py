# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-3.0.txt
# for full license details.

import json
import os
import functools
import threading

if os.name == 'nt':
    import win32api
    import win32con

from twisted.internet import reactor, protocol, defer, threads
from txkernel.kernelbase import KernelBase
from txkernel.kernelapp import KernelApp

from .pipe import Pipe, NetstringPipe

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
        super(ILuaKernel, self).__init__(*args, **kwargs)

        self.log.debug("Opening pipes")
        # Pipe setup
        self.cmd_pipe = NetstringPipe.cmd_pipe()
        self.ret_pipe = NetstringPipe.ret_pipe()

        self.pipes_lock = threading.Lock()

        # Lua process setup
        self.log.debug("Launching child lua")
        def message_sink(stream, data):
            return self.send_update("stream", {"name": stream, "text": data})
        proto = OutputCapture(message_sink)
        lua_env = {
            'ILUA_CMD_PATH': self.cmd_pipe.path,
            'ILUA_RET_PATH': self.ret_pipe.path,
            'ILUA_LIB_PATH': LUALIBS_PATH
        }
        # pylint: disable=no-member
        if os.name == "nt":
            self.lua_process = reactor.spawnProcess(proto, None,
                                                    ['lua', INTERPRETER_SCRIPT],
                                                    lua_env)
        else:
            self.lua_process = reactor.spawnProcess(proto, 'lua',
                                                    ['lua', INTERPRETER_SCRIPT],
                                                    lua_env)

        self.log.debug("Connecting to lua")
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
            if result['payload']['returned'] != "" and not silent:
                self.send_update("execute_result", {
                    'execution_count': self.execution_count,
                    'data': {
                        'text/plain': result['payload']['returned']
                    },
                    'metadata': {}
                })

            defer.returnValue({
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            })
        else:
            full_traceback = result['payload']['returned'].split("\n")
            evalue = full_traceback[0]
            traceback = full_traceback
            if not silent:
                self.send_update("error", {
                    'execution_count': self.execution_count,
                    'traceback': traceback,
                    'ename': 'n/a',
                    'evalue': evalue
                })

            defer.returnValue({
                'status': 'error',
                'execution_count': self.execution_count,
                'traceback': traceback,
                'ename': 'n/a',
                'evalue': evalue
            })

    @defer.inlineCallbacks
    def do_is_complete(self, code):
        result = yield threads.deferToThread(self.send_message,
                                             {"type": "is_complete",
                                             "payload": code})

        defer.returnValue({'status': result['payload']})

    def do_interrupt(self):
        if os.name == 'nt':
            self.log.warn("Windows currently does not support keyboard"\
                          " interrupts")
        else:
            self.lua_process.signalProcess("INT")

    def on_stop(self):
        self.cmd_pipe.close()
        self.ret_pipe.close()
        self.lua_process.signalProcess("KILL")

if __name__ == '__main__':
    if os.name == "nt":
        import signal
        signal.signal(signal.SIGINT, lambda *args: None)
    KernelApp(ILuaKernel).run()
