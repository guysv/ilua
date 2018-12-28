import os
import json
import threading
from twisted.internet import defer
from twisted.enterprise import adbapi

class HistoryManager(object):
    def __init__(self, history_path):
        self.history_path = history_path
        self.connected = False
        self.session = None
    
    @defer.inlineCallbacks
    def connect(self):
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

        self.connected = True;
    
    def tail(self, lines_back):
        return self.db.runQuery("""SELECT session, line, source FROM history
                                   ORDER BY session, line
                                   LIMIT ?
                                """, (lines_back,))
    
    @defer.inlineCallbacks
    def append(self, source, line):
        yield self.db.runOperation("""INSERT INTO history
                                      VALUES (?,?,?)
                                   """, (self.session, line, source))
