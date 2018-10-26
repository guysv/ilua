# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

from setuptools import setup, find_packages

setup(
    name='ilua',
    version='0.1.0',
    packages=find_packages(),

    package_data={
        'ilua': [
            'interp.lua',
            'lualibs/json.lua/json.lua',
            'lualibs/netstring.lua/netstring.lua',
            'lualibs/netstring.lua/inspect.lua',
        ]
    },

    install_requires=['twisted', 'termcolor', 'txkernel', 'jupyter_core',
                      'jupyter_client']
)