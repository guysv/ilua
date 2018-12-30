# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
This module is in charge of loading the history
from previous sessions, and making it available
in the frontend
"""

import os
import json
import threading
from twisted.internet import defer
from twisted.enterprise import adbapi

class HistoryManager(object):
    """
    SQLite DB manager capable of retreiving and appending
    history to a database on disk
    """

    def __init__(self, history_path):
        """
        :param history_path: Path to database (created if
                             does not exist)
        :type history_path: string
        """

        self.history_path = history_path
        self.connected = False
        self.session = None
    
    @defer.inlineCallbacks
    def connect(self):
        """
        Connect to history database

        :return: a deferred firing when db is connected
                 and initialized
        :rtype: twisted.internet.deferred.Deferred
        """
        self.db = adbapi.ConnectionPool("sqlite3", self.history_path,
                                        check_same_thread=False)
        yield self.db.runOperation("""CREATE TABLE IF NOT EXISTS history (
                                          session integer,
                                          line integer,
                                          source text,
                                          PRIMARY KEY(session, line)
                                      );
                                   """)
        
        result = yield self.db.runQuery(r"SELECT max(session) FROM history")
        self.session = result[0][0] + 1 if result[0][0] else 1

        self.connected = True
    
    def tail(self, lines_back):
        """
        Get last `lines_back` entries from history
        database

        :param lines_back: number of lines back to retreive
        :type lines_back: int
        :return: a deferred containing requested history
        :rtype: twisted.internet.deferred.Deferred
        """
        return self.db.runQuery("""SELECT session, line, source FROM history
                                   ORDER BY session, line
                                   LIMIT ?
                                """, (lines_back,))
    
    @defer.inlineCallbacks
    def append(self, source, line):
        """
        Append entry `source` at line `line`
        line should be the execution count

        :param source: evaluated code to save
        :type source: string
        :param line: code line (source's execution count
        :type line: int
        :return: a deferred firing when insertion is done
        :rtype: twisted.internet.deferred.Deferred
        """
        yield self.db.runOperation("""INSERT INTO history
                                      VALUES (?,?,?)
                                   """, (self.session, line, source))
