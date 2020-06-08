# ILua
*ILua* is a feature-packed, portable console and [Jupyter](http://jupyter.org/) kernel for the  [Lua](https://www.lua.org/) language.
![](demo.gif)
## Features
 * Lua-implementation agnostic
   * Should work with any lua interpreter out of the box
   * Works with Lua5.1-5.3, [LuaJIT](http://luajit.org/) and even some exotic implementations like [GopherLua](https://github.com/yuin/gopher-lua)
   * [Easy to port to embedded interpreters](https://eng.hroncok.cz/2020/05/14/ilua-rpm-console)
 * Code completions
 * Code inspection
   * Retrieve function documentation
   * Can even retrieve the function source if available (invoked with ??)
 * Pretty-printed results
 * Access last result with _
 * Cross-session execution history
 * Works on Linux and Windows
 * No native dependencies for Lua
 * Python's pip based installation

## Installation
```bash
pip install ilua

# From source
git clone https://github.com/guysv/ilua.git --recurse-submodules
cd ilua
pip install -e . --user
python setup.py install_data -d ~/.local # pip install -e . forgets data_files...
```

## A Bit on ILua's Architecture
As opposed to existing Lua Jupyter kernels which implement the Jupyter protocol in Lua (and depend on lzmq which is a native module), ILua implements the communication with Jupyter in Python, which in turn talks with Lua via named-pipe IPC. This frees ILua from being bounded to a single Lua implementation ABI. The Lua interpreter only needs to respect the `$LUA_PATH` environment variable and execute a file given as the first argument.
