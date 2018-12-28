# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
import os
import txzmq
from twisted.internet import defer
from twisted.logger import Logger
from jupyter_core.paths import jupyter_data_dir
from . import sockets, message, history

class KernelBase(object):
    # default kernel_info
    protocol_version = '5.3.0' # TODO: duplicate var in message.py??
    # calm down linter
    implementation = None
    implementation_version = None
    language_info = None
    banner = None

    help_links = []

    log = Logger()

    def __init__(self, connection_props, reactor=None, *args, **kwargs):
        if not reactor:
            from twisted.internet import reactor
        self.reactor = reactor
        self.connection_props = connection_props

        self.history_manager = history.HistoryManager(self.get_history_path())

        sign_scheme = self.connection_props["signature_scheme"]
        key = self.connection_props["key"]
        self.message_manager = message.MessageManager(sign_scheme, key)

        self.zmq_factory = txzmq.ZmqFactory()
        self.zmq_factory.registerForShutdown()
        self.execution_count = 0
        self.shutdown_bcast = None
        self.stop_deferred = defer.Deferred()

        # HACK: Instead of a handler object and setting up a parent for
        # each request, We use a global parent.
        # Obviously this breaks some edge cases, but I don't see why we
        # should care concidering the early stage of the project
        self.curr_parent = None
        
        transport = self.connection_props["transport"]
        addr = self.connection_props["ip"]

        # the shell_sock is circular-referencing
        # it is only allocated once on app up and down tho
        shell_endpoint = self._endpoint(transport, addr,
                                        self.connection_props["shell_port"])
        self.shell_sock = sockets.ShellConnection(self.handle_message,
                                                  self.zmq_factory,
                                                  shell_endpoint)

        ctrl_endpoint = self._endpoint(transport, addr,
                                       self.connection_props["control_port"])
        self.ctrl_sock = sockets.ShellConnection(self.handle_message,
                                                 self.zmq_factory,
                                                 ctrl_endpoint)
        
        iopub_endpoint = self._endpoint(transport, addr,
                                        self.connection_props["iopub_port"])
        self.iopub_sock = sockets.IOPubConnection(self.zmq_factory,
                                                  iopub_endpoint)
        
        stdin_endpoint = self._endpoint(transport, addr,
                                        self.connection_props["stdin_port"])
        self.stdin_sock = sockets.StdinConnection(self.zmq_factory,
                                                  stdin_endpoint)
        
        hb_endpoint = self._endpoint(transport, addr,
                                     self.connection_props["hb_port"])
        self.hb_sock = sockets.HearbeatConnection(self.zmq_factory,
                                                  hb_endpoint)

    @defer.inlineCallbacks
    def run(self):
        self.send_update("status", {'execution_state': 'starting'})
        yield self.history_manager.connect()
        yield self.do_startup()
        self.send_update("status", {'execution_state': 'idle'})
        val = yield self.stop_deferred
        yield self.do_shutdown()
        if self.shutdown_bcast:
            self.iopub_sock.publish(self.shutdown_bcast)
        defer.returnValue(val)

    @defer.inlineCallbacks
    def handle_message(self, request_socket, sender_id, message_parts):
        try:
            # extra ids? probebly will never be used
            # TODO: catch parsing errors
            msg, _ = self.message_manager.parse(message_parts)

            self.curr_parent = msg['header']

            self.send_update("status", {'execution_state': 'busy'})

            msg_type = msg['header']['msg_type']
            if msg_type == 'kernel_info_request':
                resp_type = 'kernel_info_reply'
                content = yield self.do_kernel_info(**msg['content'])
            elif msg_type == 'execute_request':
                resp_type = "execute_reply"
                self.execution_count += 1
                self.history_manager.append(msg['content']['code'],
                                            self.execution_count)

                self.send_update("execute_input",
                                 {'code': msg['content']['code'],
                                 'execution_count': self.execution_count})
                if msg['content']['code'].endswith("?"):
                    # Altough inspection requests exist, frontends does not
                    # seem to send them. Instead, the kernel is in charge of
                    # deciding when to return an inspection. When this happens,
                    # the inpspection output is returned via the _deprecated_
                    # payload feature
                    content = yield self._inspect_proxy(msg['content']['code'])
                else:                    
                    # TODO: currently we can't stop on error, so no way
                    # to handle that..
                    msg['content'].pop('stop_on_error', None)
                    content = yield self.do_execute(**msg['content'])
            elif msg_type == 'is_complete_request':
                resp_type = "is_complete_reply"
                content = yield self.do_is_complete(**msg['content'])
            elif msg_type == 'complete_request':
                resp_type = 'complete_reply'
                content = yield self.do_complete(**msg['content'])
            elif msg_type == 'inspect_request':
                resp_type = 'inspect_reply'
                content = yield self.do_inspect(**msg['content'])
            elif msg_type == 'history_request':
                resp_type = 'history_reply'
                content = yield self.do_history(**msg['content'])
            elif msg_type == 'shutdown_request':
                resp_type = 'shutdown_reply'

                content = {'restart': msg['content']['restart']}
                self.shutdown_bcast =\
                    self.message_manager.build('shutdown_reply', content,
                                               msg['header'])
                self.signal_stop()
            elif msg_type == 'interrupt_request':
                resp_type = 'interrupt_reply'
                content = yield self.do_interrupt(**msg['content'])
            else:
                self.log.info("No handler for request of type {req_type}",
                               req_type=msg_type)
                self.log.debug("Unhandled request content is {content}",
                               content=msg['content'])
                defer.returnValue(None)
            
            msg_bin = self.message_manager.build(resp_type, content,
                                                msg['header'])
            request_socket.sendMultipart(sender_id, msg_bin)
        except Exception:
            self.log.failure("Uncought exception in message handler")
            self.signal_stop()
        finally:
            self.send_update("status", {'execution_state': 'idle'})

    def do_kernel_info(self):
        return {
            'protocol_version': self.protocol_version,
            'implementation': self.implementation,
            'implementation_version': self.implementation_version,
            'language_info': self.language_info,
            'banner': self.banner,
            'help_links': self.help_links
        }
    
    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        raise NotImplementedError

    def do_is_complete(self, code):
        raise NotImplementedError
    
    def do_complete(self, code, cursor_pos):
        return {
            'matches': [],
            'cursor_start':0,
            'cursor_end':0,
            'metadata':{},
            'status': 'ok'
        }
    
    @defer.inlineCallbacks
    def _inspect_proxy(self, code):
        stripped_code = code.rstrip("?")
        cursor_pos = len(stripped_code)
        detail_level = min(1, len(code) - len(stripped_code) - 1)
        inspect_content = yield self.do_inspect(stripped_code, cursor_pos,
                                                detail_level)
        
        response = {
            'status': 'ok',
            # The base class increments the execution count
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

        if inspect_content['found']:
            response['payload'].append({
                'source': 'page',
                'data': inspect_content['data'],
                'start': 0
            })
        
        defer.returnValue(response)
    
    def do_inspect(self, code, cursor_pos, detail_level=1):
        return {
            'status': 'ok',
            'found': False,
            'data': {},
            'metadata': {}
        }
    
    @defer.inlineCallbacks
    def do_history(self, hist_access_type, output, raw, session=None,
                   start=None, stop=None, n=None, pattern=None, unique=False):
        # Most of the arguments seem too rare to be taken care of seriously
        if hist_access_type != "tail" or not n or output:
            defer.returnValue({
                'history': []
            })
        else:
            result = yield self.history_manager.tail(n)
            defer.returnValue({
                'history': result
            })
    
    def do_startup(self):
        pass

    def do_shutdown(self, restart=False):
        pass

    def do_interrupt(self):
        return {}

    def send_update(self, msg_type, content):
        msg = self.message_manager.build(msg_type, content, self.curr_parent)
        self.iopub_sock.publish(msg)
    
    def signal_stop(self):
        # Multiple sources could request kernel shutdown
        # because only one is sufficient, ignore all other
        # attempts
        if not self.stop_deferred.called:
            self.stop_deferred.callback(None)

    @staticmethod
    def _endpoint(transport, addr, port,
                  type=txzmq.ZmqEndpointType.bind):
        url = "{}://{}:{}".format(transport, addr, port)
        return txzmq.ZmqEndpoint(type, url)
    
    @classmethod
    def get_history_path(cls):
        return os.path.join(jupyter_data_dir(),
                            "{}_history.db".format(cls.implementation.lower()))
