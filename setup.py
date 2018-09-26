# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv3.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-3.0.txt
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
        ]
    },

    install_requires=['twisted', 'txzmq', 'txkernel', 'jupyter_core']
)