# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-3.0.txt
# for full license details.
"""
Lua Jupyter kernel, extending ilua.kernelbase
Manages the Lua subprocess and commnad pipes,
output capturing, frontend requests, and other
stuff
"""

import os
import re

from distutils.spawn import find_executable

if os.name == 'nt':
    # pylint: disable=E0401
    from twisted.internet import _pollingfile

import termcolor

from twisted.internet import protocol, defer

from .kernelbase import KernelBase

from .namedpipe import CoupleOPipes, get_pipe_path
from .proto import InterpreterProtocol, OutputCapture
from .inspector import Inspector
from .version import version as ilua_version

INTERPRETER_SCRIPT = os.path.join(os.path.dirname(__file__), "interp.lua")
LUA_PATH_EXTRA = os.path.join(os.path.dirname(__file__), "?.lua")

_bold_red = lambda s: termcolor.colored(s, "red", attrs=['bold'])

class ILuaKernel(KernelBase):
    """
    Jupyter kernel for Lua, managing the communication
    between a Lua subprocess and a Jupyter frontend
    """

    implementation = 'ILua'
    implementation_version = ilua_version
    language = "lua"
    language_info = {
        'name': 'lua',
        'mimetype': 'text/x-lua',
        'file_extension': '.lua',
        'version': 'n/a'
    }
    banner = "ILua {}".format(ilua_version)
    help_links = [
        {"text": "Lua Reference",
         "url": "https://www.lua.org/manual/5.3/"}
    ]

    def __init__(self, *args, **kwargs):
        super(ILuaKernel, self).__init__(*args, **kwargs)
        self.inspector = Inspector()

        self.pipes = CoupleOPipes(get_pipe_path("ret"), get_pipe_path("cmd"))

        self.lua_interpreter = kwargs.pop("lua_interpreter")

        # Lua process setup
        self.log.debug("Launching child lua")
        def message_sink(stream, data):
            return self.send_update("stream", {"name": stream, "text": data})
        proto = OutputCapture(message_sink)
        os.environ.update({
            'ILUA_CMD_PATH': self.pipes.out_pipe.path,
            'ILUA_RET_PATH': self.pipes.in_pipe.path,
            'LUA_PATH': os.environ.get("LUA_PATH", ";") + ";"  + LUA_PATH_EXTRA
        })

        assert find_executable(self.lua_interpreter), ("Could not find '{}', "
                                                       "is Lua in the system "
                                                       "path?".format(
                                                           self.lua_interpreter))

        # pylint: disable=no-member
        if os.name == "nt":
            self.lua_process = self.reactor.spawnProcess(proto, None,
                                                         [self.lua_interpreter,
                                                          INTERPRETER_SCRIPT],
                                                         None)
        else:
            self.lua_process = self.reactor.spawnProcess(proto,
                                                         self.lua_interpreter,
                                                         [self.lua_interpreter,
                                                          INTERPRETER_SCRIPT],
                                                         None)

    @defer.inlineCallbacks
    def do_startup(self):
        self.proto = yield self.pipes.connect(
            protocol.Factory.forProtocol(InterpreterProtocol))

        returned = yield self.proto.sendRequest({"type": "execute",
                                                "payload": "nil, _VERSION"})

        if not returned["payload"]['success']:
            self.log.warn("Version request failed")
        else:
            version = re.findall(r"Lua (\d(?:\.\d)+)",
                                 returned['payload']['returned'])
            if not version:
                self.log.warn("Failed to parse version from interpreter"
                              " response")
                self.log.debug("Response: {response}",
                               response=returned['payload']['returned'])
            else:
                # There is a race between the kernel startup and the kernel
                # info request where the reply might come out before we figure
                # out the language version. We might need to block with a
                # deferred in the future (but this hurts startup time)
                self.language_info['version'] = version[0]
                self.log.debug("Lua version is {version}", version=version[0])

    @defer.inlineCallbacks
    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        result = yield self.proto.sendRequest({"type": "execute",
                                              "payload": code})

        if os.name == "nt":
            # Because twisted's default implementation for process output
            # reading on windows is polling the output pipe, sometimes the
            # kernel will finish execute requests before output is read.
            # This causes a statistical lag in output display
            # The sleep seems to help the execution request to lose the
            # race, therefore eliminating the lag
            sleep_deferred = defer.Deferred()
            self.reactor.callLater(_pollingfile.MAX_TIMEOUT,
                                   sleep_deferred.callback, None)
            yield sleep_deferred

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
        result = yield self.proto.sendRequest({"type": "is_complete",
                                               "payload": code})

        defer.returnValue({'status': result['payload']})

    @defer.inlineCallbacks
    def do_complete(self, code, cursor_pos):
        last_obj = self.inspector.get_last_obj(code, cursor_pos)
        initial = last_obj.pop() if last_obj and last_obj[-1] not in ".:" \
                  else ""
        only_methods = last_obj[-1] == ":" if last_obj else False
        breadcrumbs = last_obj[::2]

        result = yield self.proto.sendRequest({
            "type": "complete",
            "payload": {
                'breadcrumbs':breadcrumbs,
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

    _EMPTY_INSPECTION = {
        "status": "ok",
        "found": False,
        "data": {},
        "metadata": {}
    }

    @defer.inlineCallbacks
    def do_inspect(self, code, cursor_pos, detail_level):
        last_obj = self.inspector.get_last_obj(code, cursor_pos)
        breadcrumbs = last_obj[::2]

        result = yield self.proto.sendRequest({"type": "info",
                                               "payload": {'breadcrumbs':
                                                           breadcrumbs}})

        if not result['payload']:
            defer.returnValue(self._EMPTY_INSPECTION.copy())

        info = result['payload']

        text_parts = []

        if info['preloaded_info']:
            text_parts.append(u"{} {}".format(_bold_red("Signature:"),
                                              info['func_signature']))
            text_parts.append(u"{}\n{}".format(_bold_red("Documentation:"),
                                              info['func_documentation']))
            text_parts.append(u"{} {}".format(_bold_red("Path:"), "n/a"))
        elif info['source'].startswith("@"):
            # Source is available, parse source file for info
            # TODO: caching?
            source_file = info['source'][1:]
            line = int(info['linedefined'])
            documentation = self.inspector.get_doc(source_file, line)
            text_parts.append(u"{}\n{}".format(_bold_red("Documentation:"),
                                              documentation))

            if detail_level >= 1:
                last_line = int(info['lastlinedefined'])
                source = self.inspector.get_source(source_file, line,
                                                   last_line)
                text_parts.append(u"{}\n{}".format(_bold_red("Source:"),
                                                  source))

            text_parts.append(u"{} {}".format(_bold_red("Path:"), source_file))
        else:
            defer.returnValue(self._EMPTY_INSPECTION.copy())

        defer.returnValue({
            'status': 'ok',
            'found': True,
            'data': {
                'text/plain': u"\n".join(text_parts)
            },
            'metadata': {}
        })

    def do_interrupt(self):
        self.log.warn("ILua does not support keyboard interrupts")

    def do_shutdown(self):
        self.pipes.loseConnection()
        self.lua_process.signalProcess("KILL")
