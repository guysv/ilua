# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.
import os.path
import glob
from setuptools import setup, find_packages

here = os.path.dirname(__file__)

setup(
    data_files=[
        ("share/jupyter/kernels/lua",
         glob.glob(os.path.join(here, "defaultspec/*")))
    ]
)
