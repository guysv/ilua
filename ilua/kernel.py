# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-3.0.txt
# for full license details.

import json
import os
import re
import functools
import itertools
import threading

from pygments.lexers import _lua_builtins, scripting
from pygments import token

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
        disabled_modules = list(_lua_builtins.MODULES)
        self.lexer = scripting.LuaLexer(disabled_modules=disabled_modules)

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
        lua_env = os.environ.update({
            'ILUA_CMD_PATH': self.cmd_pipe.path,
            'ILUA_RET_PATH': self.ret_pipe.path,
            'ILUA_LIB_PATH': LUALIBS_PATH
        })
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

        with self.pipes_lock:
            self.cmd_pipe.stream.write_netstring(message_json)
            self.cmd_pipe.stream.flush()
            resp = self.ret_pipe.stream.read_netstring()

        return json.loads(resp.decode("utf8", "ignore"))

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
    
    def get_last_obj(self, code, cursor_pos):
        all_tokens = list(self.lexer.get_tokens_unprocessed(code[:cursor_pos]))

        unordered_tokens = itertools.takewhile(lambda x: x[1] == token.Name or
                                                        x[2] in '.:',
                                              all_tokens[::-1])
        unordered_tokens = list(unordered_tokens)
        
        last_obj = []
        if not unordered_tokens:
            return last_obj
        
        now_name = token.Name == unordered_tokens[0][1]
        for i, t in enumerate(unordered_tokens):
            if now_name and t[1] == token.Name:
                last_obj.insert(0, t[2])
            elif not now_name and i < 2 and t[2] == ":":
                last_obj.insert(0, t[2])
            elif not now_name and  t[2] == ".":
                last_obj.insert(0, t[2])
            else:
                break
            now_name = not now_name
        
        if last_obj and last_obj[0] in ".:":
            last_obj.pop(0)
        
        return last_obj

    @defer.inlineCallbacks
    def do_complete(self, code, cursor_pos):
        last_obj = self.get_last_obj(code, cursor_pos)
        initial = last_obj.pop() if last_obj and last_obj[-1] not in ".:" \
                  else ""
        only_methods = last_obj[-1] == ":" if last_obj else False
        breadcrumbs = last_obj[::2]
        
        result = yield threads.deferToThread(self.send_message,
                                             {"type": "complete", "payload": {
                                              'breadcrumbs': breadcrumbs,
                                              'only_methods': only_methods}})
        
        matches = filter(lambda x: x.startswith(initial), result['payload'])
        matches_prefix = "".join(last_obj)
        matches_full = [matches_prefix + m for m in matches]
        
        cursor_start = cursor_pos - sum([len(s) for s in breadcrumbs]) \
                            - len(breadcrumbs) - len(initial)
        cursor_end = cursor_pos

        defer.returnValue({
                'matches': sorted(list(set(matches_full))),
                'cursor_start':cursor_start,
                'cursor_end':cursor_end,
                'metadata':{},
                'status': 'ok'
        })

    def do_interrupt(self):
        self.log.warn("ILua does not support keyboard interrupts")

    def on_stop(self):
        self.cmd_pipe.close()
        self.ret_pipe.close()
        self.lua_process.signalProcess("KILL")

if __name__ == '__main__':
    if os.name == "nt":
        import signal
        signal.signal(signal.SIGINT, lambda *args: None)
    KernelApp(ILuaKernel).run()
