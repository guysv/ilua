# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
"""
ILua's kernel app entry point and command-line tweaks
"""

from .appbase import AppBase
from .kernel import ILuaKernel

class ILuaApp(AppBase):
    def __init__(self, *args, **kwargs):
        super(ILuaApp, self).__init__(ILuaKernel, *args, **kwargs)
        self.parser.add_argument("-i", "--lua-interpreter", metavar="LUA",
                                 default=self._get_default("LUA_INTERPRETER",
                                                           'lua'),
                                 help="Lua interpreter to use for code "
                                      "evaluations")

def main():
    ILuaApp().run()

if __name__ == '__main__':
    main()
