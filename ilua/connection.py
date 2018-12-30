# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

"""
This module is in charge of parsing the
kernel connection file as described in
https://jupyter-client.readthedocs.io/en/stable/kernels.html#connection-files
"""
import json
import os
import os.path

from jupyter_core.paths import jupyter_runtime_dir

class ConnectionFile(object):
    """
    This is really just internal code, so no need
    for exposing each property in a fancy way
    """
    DEFAULT_PROPERTIES = {
        "ip": "127.0.0.1",
        "transport": "tcp",
        "shell_port": 0,
        "control_port": 0,
        "iopub_port": 0,
        "stdin_port": 0,
        "hb_port": 0,
        "signature_scheme": "hmac-sha256",
        "key": "" # TODO: generate key?
    }

    def __init__(self, connection_props):
        self.connection_props = connection_props

        if not os.path.exists(jupyter_runtime_dir()):
            os.mkdir(jupyter_runtime_dir(), 0o1700)
    
    @classmethod
    def generate(cls, partial_props=None):
        """
        Generate new connection file props from
        defaults
        
        :param partial_props: predefined properties, defaults to None
        :param partial_props: dict, optional
        :return: ConnectionFile object with complete properties
        :rtype: ilua.connection.ConnectionFile
        """

        partial_props = partial_props or {}
        props = partial_props.copy()
        props.update(cls.DEFAULT_PROPERTIES)
        return cls(props)
    
    @classmethod
    def from_existing(cls, path):
        with open(path) as existing:
            return cls(json.load(existing))

    def write_file(self):
        """
        Write a new connection file to disk. and
        return its path

        :return: path to written connection file
        :rtype: string
        """
        name = "kernel-{pid}.json".format(pid=os.getpid())
        path = os.path.join(jupyter_runtime_dir(), name)

        # indentation, because why not.
        connection_json = json.dumps(self.connection_props, indent=2)

        with open(path, "w") as connection_file:
            connection_file.write(connection_json)
        
        return path
