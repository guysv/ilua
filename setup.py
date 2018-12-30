# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
import re
import os.path
import glob
from setuptools import setup, find_packages

here = os.path.dirname(__file__)

with open(os.path.join(here, "ilua/version.py")) as version_file:
    version = re.match(r'version = "(.*)"', version_file.read()).group(1)

with open(os.path.join(here, "README.md")) as readme_file:
    long_description = readme_file.read()

setup(
    name='ilua',
    version=version,
    description="Portable Lua kernel for Jupyter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/guysv/ilua",
    author="Guy Sviry",
    author_email="sviryguy@gmail.com",
    license="GPLv2",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Interpreters',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='lua interactive console jupyter kernel',

    packages=find_packages(),

    package_data={
        'ilua': [
            'interp.lua',
            'builtins.lua',
            'ext/json.lua',
            'ext/netstring.lua',
            'ext/inspect.lua',
        ]
    },

    entry_points={
        'console_scripts': [
            'ilua=ilua.consoleapp:main',
        ],
    },

    data_files=[
        ("share/jupyter/kernels/lua",
         glob.glob(os.path.join(here, "defaultspec/*")))
    ],

    # TODO: decide on minimal version for dependencies
    install_requires=['twisted', 'termcolor', 'pygments', 'txzmq', 'jupyter_core',
                      'jupyter_console', 'pywin32;sys_platform=="win32"',]
)
