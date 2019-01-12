# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
A collection of lexer-involved routines
for lua code parsing
"""

from itertools import islice, takewhile
from pygments import token, highlight
from pygments.lexers import _lua_builtins
from pygments.lexers.scripting import LuaLexer
from pygments.formatters.terminal import TerminalFormatter

class Inspector(object):
    """
    Lua lexical inspection services
    """
    def __init__(self):
        self.lexer = LuaLexer(disabled_modules=list(_lua_builtins.MODULES))
        self.formatter = TerminalFormatter()
    
    def get_last_obj(self, code, cursor_pos):
        """
        Get the object under the cursor and break it to
        `breadcrumbs`
        i.e: break `assert(io.stdin:write|` to ['io','stdin','write']
        
        :param code: code to inspect
        :type code: string
        :param cursor_pos: cursor position in code
        :type cursor_pos: int
        :return: breadcrubs to last object in chain
        :rtype: list
        """

        all_tokens = list(self.lexer.get_tokens_unprocessed(code[:cursor_pos]))

        unordered_tokens = takewhile(lambda x: x[1] == token.Name or
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
    
    def get_doc(self, path, line):
        """
        Get doc string from lines above given line in
        a given lua file
        `line` is typically a starting line of a function
        
        :param path: path to source file
        :type path: string
        :param line: line in source
        :type line: int
        :return: extracted docstring
        :rtype: string
        """

        with open(path) as source:
            tokens = list(self.lexer.get_tokens_unprocessed("".join(islice(
                        source, line-1))))[::-1]
            doc_tokens = takewhile(lambda t: t[1].parent == token.Comment or
                                             t[2] == "\n" , tokens)
            return "".join([t[2] for t in list(doc_tokens)[::-1]])
    
    def get_source(self, path, start_line, end_line):
        """
        Get source code from file at `path`, cropped
        from `start_line` to `end_line`
        
        :param path: path to source file
        :type path: string
        :param start_line: starting line
        :type start_line: int
        :param end_line: ending line
        :type end_line: int
        :return: extracted source code
        :rtype: string
        """

        with open(path) as source:
            return highlight("".join(islice(source, start_line-1, end_line)),
                             self.lexer, self.formatter)