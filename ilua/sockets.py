# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

"""
This module implements the different ZeroMQ
sockets used in the Jupyter protocol

The sockets provide a simple API for the
kernel to communicate with the frontend
"""
import txzmq

class HearbeatConnection(txzmq.ZmqREPConnection):
    """
    Simple echo socket for heartbeats, init and
    forget
    """

    def gotMessage(self, messageId, *messageParts):
        self.reply(messageId, *messageParts)

class ShellConnection(txzmq.ZmqRouterConnection):
    """
    Shell connection socket, handling requests
    from the frontend
    """

    def __init__(self, message_handler, *args, **kwargs):
        self.message_handler = message_handler
        super(ShellConnection, self).__init__(*args, **kwargs)
    
    def gotMessage(self, sender_id, *messageParts):
        self.message_handler(self, sender_id, messageParts)
    
class IOPubConnection(txzmq.ZmqPubConnection):
    """
    IOPub socket for message broadcasts
    """

    def publish(self, message):
        self.send(message)

class StdinConnection(txzmq.ZmqRouterConnection):
    # TODO: unused
    pass
