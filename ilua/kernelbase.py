# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
Twisted-based Jupyter base kernel implementation
Pretty much a reimplementation of ipykernel.kernelbase,
but with Twisted, which allows async code in python 2,
and provides txzmq.
"""

import os
import txzmq
from twisted.internet import defer
from twisted.logger import Logger
from jupyter_core.paths import jupyter_data_dir
from . import sockets, message, history

class KernelBase(object):
    """
    Twisted-based Jupyter base kernel implementation,
    implements frontend requests handling and routing.
    
    The base kernel exposes the API used by sub classes,
    and provides a default implementation for a few
    requests

    The API is very similar to the stock Jupyter base
    kernel, and mostly receives the same arguments.
    
    One difference between stock Jupyter and this class
    is that all the message handling methods here return
    a Twisted deferred, which will probably kill
    portabillity

    Subclasses only really need to implement do_execute
    and do_is_complete.
    """

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
        """
        
        :param connection_props: Connection properties dictionary, built
                                 by ilua.connection.ConnectionFile
        :type connection_props: dict
        :param reactor: Twisted reactor to use, defaults
                        to the global one
        :param reactor: Twisted.internet.posixbase.PosixReactorBase,
                        optional
        """

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
        """
        Launch the kernel

        :return: a deferred firing when the kernel shuts down
        :rtype: twisted.internet.deferred.Deferred
        """

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
        """
        Kernel requests central handler, passed to the request
        (shell/control) sockets. When called by a sockets,
        message is parsed and routed to the responsible handler
        of that request type, returning the serialized response
        
        :param request_socket: The socket which received the request,
                               which also sends the response.
                               DEPRICATED: to be moved to the sockets
        :type request_socket: txzmq.ZmqConnection
        :param sender_id: DEPRICATED: to be moved to the sockets
        :type sender_id: ???
        :param message_parts: Message data parts, to be parsed
                              with kernel.message_manager.parse()
        :type message_parts: list
        :return: Serialized response
        :rtype: list
        """

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
                content = content or {}
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
        """
        Handle kernel_info request
        
        :return: response containing kernel info
        :rtype: dict or
                twisted.internet.deferred.Deferred
        """

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
        """
        Handle execution requests. Advertize
        returned data is to be advertized with
        kernel.send_update("execute_result", {...})
        and data from output/error streams with
        kernel.send_update("stream", {...})
        
        :param code: code to be evaluated
        :type code: string
        :param silent: Should the request produce
                       execute_result/stream messages
                       if true, no output is to be
                       advertized on the IOPub socket
        :type silent: bool
        :param store_history: Should the evaluation
                              request be logged, in
                              the execution history,
                              defaults to True
                              DEPRECATED: to be handled
                              by base kernel, ignore.
        :type store_history: bool, optional
        :param user_expressions: some depricated hack,
                                 defaults to None,
                                 should always be None.
        :type user_expressions: dict, optional
        :param allow_stdin: Should the execution process
                            request stdin input, defaults
                            to False
        :type allow_stdin: bool, optional
        :return: response containing execution reply
        :rtype: dict or
                twisted.internet.deferred.Deferred
        """

        raise NotImplementedError

    def do_is_complete(self, code):
        """
        Test if the code sample is suitable for
        evaluations. Is more code is to be written?
        
        :param code: code to evaluate
        :type code: string
        :return: response containing is complete
                 reply
        :rtype: dict or
                twisted.internet.deferred.Deferred
        """

        raise NotImplementedError
    
    def do_complete(self, code, cursor_pos):
        """
        Offer code completion to given state
        
        :param code: code to evaluate
        :type code: string
        :param cursor_pos: position of cursor in
                           code
        :type cursor_pos: int
        :return: response containing is complete
                 reply
        :rtype: dict or
                twisted.internet.deferred.Deferred
        """

        return {
            'matches': [],
            'cursor_start':0,
            'cursor_end':0,
            'metadata':{},
            'status': 'ok'
        }
    
    @defer.inlineCallbacks
    def _inspect_proxy(self, code):
        """
        Wrap execution request as inspection
        request. specialized inspection requests
        do exist in Jupyter, but frontends does
        not seem to send em. This method wraps
        code from execution requests to inspection
        requests to be handled seemlessly by
        subclassing kernels, and translates response
        to execute_reply format
        
        :param code: code to inspect
        :type code: string
        :return: inspection_reply wrapped as execute_reply
        :rtype: twisted.internet.deferred.Deferred
        """

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
        """
        Inspect the code and return insights such as
        documentation.
        
        :param code: code to inspect
        :type code: string
        :param cursor_pos: positon of cursor in code
        :type cursor_pos: int
        :param detail_level: level of verbosity (i.e. # of ?s).
                             higher levels should add more
                             insights. defaults to 1
        :param detail_level: int, optional
        :return: response containing inspect reply
        :rtype: dict or
                twisted.internet.deferred.Deferred
        """

        return {
            'status': 'ok',
            'found': False,
            'data': {},
            'metadata': {}
        }
    
    @defer.inlineCallbacks
    def do_history(self, hist_access_type, output, raw, session=None,
                   start=None, stop=None, n=None, pattern=None, unique=False):
        """
        Fetch execution history from past sessions
        This method is NOT to be overidden by sub
        classes

        Note: currently, only 'tail' access is
        implemented, so any other request yields
        empty response

        :return: response containing inspect reply
        :rtype: dict or
                twisted.internet.deferred.Deferred
        """

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
        """
        Callback to do stuff on kernel startup
        """
        pass

    def do_shutdown(self, restart=False):
        """
        Callback to do stuff on kernel shutdown
        :param restart: ignored
        """
        pass

    def do_interrupt(self):
        """
        Handle interrupt requests
        """
        return {}

    def send_update(self, msg_type, content):
        """
        Send messages on the IOPub socket such
        as execution_result or (out/err) stream
        
        :param msg_type: type of IOPub message
        :type msg_type: string
        :param content: message content
        :type content: dict
        """
        msg = self.message_manager.build(msg_type, content, self.curr_parent)
        self.iopub_sock.publish(msg)
    
    def signal_stop(self):
        """
        Any piece of code (except kernel init)
        that wants to initiate a shutdown should
        call this method
        """

        # Multiple sources could request kernel shutdown
        # because only one is sufficient, ignore all other
        # attempts
        if not self.stop_deferred.called:
            self.stop_deferred.callback(None)

    @staticmethod
    def _endpoint(transport, addr, port,
                  type=txzmq.ZmqEndpointType.bind):
        """
        Utility method to build ZMQ urls
        easily
        """

        url = "{}://{}:{}".format(transport, addr, port)
        return txzmq.ZmqEndpoint(type, url)
    
    @classmethod
    def get_history_path(cls):
        """
        Get platform-specific path to past
        sessions execution history
        """

        return os.path.join(os.path.expanduser("~"),
                            ".{}_history.db".format(cls.implementation.lower()))
