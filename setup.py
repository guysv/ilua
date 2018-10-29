# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
import re
import os.path
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), "ilua/version.py")) as \
        version_file:
    version = re.match(r'version = "(.*)"', version_file.read()).group(1)

setup(
    name='ilua',
    version=version,
    packages=find_packages(),

    package_data={
        'ilua': [
            'interp.lua',
            'lualibs/builtins.lua',
            'lualibs/json.lua/json.lua',
            'lualibs/netstring.lua/netstring.lua',
            'lualibs/inspect.lua/inspect.lua',
        ]
    },

    install_requires=['twisted', 'termcolor', 'txkernel', 'jupyter_core',
                      'jupyter_client']
)