#!/bin/env python
"""
A quick script to download the lua manuals, and convert them to json

Using some oneliner like 
```bash
manualparser.py | \
lua -e 'pretty = require"pl.pretty" json = require"json" io.stdout:write(pretty.write(json.decode(io.stdin:read"*a")))'
```
will convert it the json to a lua table, used to write builtins.lua
note: oneliner requires penlight and some json library
"""
from __future__ import print_function
import sys
import re
import json
import requests
import html2text

def get_docs(manual_url, starting_line, ending_line):
    manual_text = html2text.html2text(requests.get(manual_url).text)
    lib_text = "\n".join(manual_text.split("\n")[starting_line:ending_line])
    return {
        func: {
            'signature': func + proto,
            'documentation': doc
        }
        for func, proto, doc in re.findall(r"\* \* \*\n\n### `([\w:.]+) "
                                           r"(\(.*?\))`\n\n(.*?)"
                                           r"(?=\n\n\* \* \*|\n\n#{1,3}(?!#))",
                                           lib_text, re.DOTALL)
    }

def main():
    docs_dict = {}
    docs_dict.update(get_docs("https://www.lua.org/manual/5.1/manual.html",
                              4386, 6018))
    docs_dict.update(get_docs("https://www.lua.org/manual/5.2/manual.html",
                              5215, 7071))
    docs_dict.update(get_docs("https://www.lua.org/manual/5.3/manual.html",
                              5306, 7227))
    json.dump(docs_dict, sys.stdout, indent=4)

if __name__ == '__main__':
    main()
