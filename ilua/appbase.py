# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

"""
This module implements a kernel entry-point.

The typical Jupyter kernel has two app modes:

child mode: The kernel is launched as a child
process of a Jupyter frontend, and its connection
file is made by the frontend.

passive mode: The kernel is launched as a
stand-alone program, and generates its connection
file by itself. The connection file path is then
returned to the user for frontend connections.
"""
import sys
import argparse
import os
from os import path
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import zmq
from twisted.internet import task
from twisted.logger import globalLogBeginner, FilteringLogObserver, \
                           textFileLogObserver, LogLevel, PredicateResult
from .connection import ConnectionFile

class AppBase(object):
    """
    Base kernel app class that takes care of managing the connection
    to the frontends, and allows extensions by child classes to add
    extra command-line arguments

    Child classes that wish to add extra command-line arguments may
    use the app.parser field which is an argparse parser
    """

    _NAME_TO_LEVEL = {
        'debug': LogLevel.debug,
        'info': LogLevel.info,
        'warn': LogLevel.warn,
        'error': LogLevel.error,
        'critical': LogLevel.critical
    }

    def __init__(self, kernel_cls, *extra_kernel_args, **extra_kernel_kwargs):
        """
        :param kernel_cls: Kernel class to instantiate
        :type kernel_cls: ilua.kernelbase.KernelBase
        :param extra_kernel_args: Extra args passed to kernel_cls constructor
        :type extra_kernel_args: tuple
        :param extra_kernel_kwargs: Extra kwargs passed to kernel_cls constructor
        :type extra_kernel_kwargs: dict
        """

        self.kernel_cls = kernel_cls
        self.env_var_prefix = self.kernel_cls.implementation.upper() + "_"
        self.extra_kernel_args = extra_kernel_args
        self.extra_kernel_kwargs = extra_kernel_kwargs

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-l', '--log-level',
                                 default=self._get_default('LOG_LEVEL',
                                                           'warn'),
                                 metavar="LEVEL",
                                 choices=self._NAME_TO_LEVEL.keys(),
                                 help="Show only certain logs")
    
    def run(self):
        """
        Run kernel application
        """
        # separated from other options to give subclasses a chance to override
        self.parser.add_argument('-c', '--connection-file',
                            help="Path to existing connection file")
        cli_args = vars(self.parser.parse_args())
        
        # wow twisted log api sucks bigtime
        # all this mess just to set global log level
        filter_level = self._NAME_TO_LEVEL[cli_args.pop("log_level")]
        log_filter =\
            lambda e: PredicateResult.yes if e['log_level'] >= filter_level\
                      else PredicateResult.no
        observer = FilteringLogObserver(textFileLogObserver(sys.stdout),
                                        [log_filter])
        globalLogBeginner.beginLoggingTo([observer], redirectStandardIO=False)

        if cli_args.get("connection_file"):
            connection_file =\
                ConnectionFile.from_existing(cli_args.pop("connection_file"))
            write_connection_file = False
        else:
            connection_file = ConnectionFile.generate()
            write_connection_file = True
        
        self.extra_kernel_kwargs.update(cli_args)

        self.kernel = self.kernel_cls(connection_file.connection_props,
                                      *self.extra_kernel_args,
                                      **self.extra_kernel_kwargs)

        if write_connection_file:
            # Fix socket ports
            props = connection_file.connection_props
            props["shell_port"] = self._get_socket_port(self.kernel.shell_sock)
            props["control_port"] = self._get_socket_port(self.kernel.ctrl_sock)
            props["iopub_port"] = self._get_socket_port(self.kernel.iopub_sock)
            props["stdin_port"] = self._get_socket_port(self.kernel.stdin_sock)
            props["hb_port"] = self._get_socket_port(self.kernel.hb_sock)

            connection_file_path = connection_file.write_file()
            hint = """To connect another client to this kernel, use:
        --existing {}""".format(path.basename(connection_file_path))
            print(hint)
        
        return task.react(lambda r: self.kernel.run())
    
    def _get_default(self, env_var_suffix, default):
        """
        Get default value for arguments from environment variable
        or given default
        
        :param env_var_suffix: suffix of argument's environment variable
        :type env_var_suffix: string
        :param default: default argument value
        :type default: string
        :return: Decided value
        :rtype: string
        """

        return os.environ.get(self.env_var_prefix + env_var_suffix, default)

    @staticmethod
    def _get_socket_port(socket):
        """
        Get listening port from socket
        
        :param socket: socket to check
        :type socket: txzmq.ZmqConnection
        :return: listening port
        :rtype: int
        """

        # pylint: disable=maybe-no-member
        return urlparse(socket.socket.getsockopt(zmq.LAST_ENDPOINT)).port
