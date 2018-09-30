-- ILua
-- Copyright (C) 2018  guysv

-- This file is part of ILua which is released under GPLv2.
-- See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
-- for full license details.

local cmd_pipe_path = assert(os.getenv("ILUA_CMD_PATH"))
local ret_pipe_path = assert(os.getenv("ILUA_RET_PATH"))
local lib_path = assert(os.getenv("ILUA_LIB_PATH"))

-- Windows supports / as dirsep
local netstring = assert(dofile(lib_path .. "/netstring.lua/netstring.lua"))
local json = assert(dofile(lib_path .. "/json.lua/json.lua"))
local inspect = assert(dofile(lib_path .. "/inspect.lua/inspect.lua"))

-- Compatibility setup
table.pack = table.pack or function (...)
    return {n=select('#',...); ...}
end
table.unpack = table.unpack or unpack

local load_compat

if setfenv then
    function load_compat(code, env)
        loaded, err = loadstring(code, "=(ilua)")
        if not loaded then
            return nil, err
        end
        setfenv(loaded, env)
        return loaded, err
    end
else
    function load_compat(code, env)
        return load(code, "=(ilua)", "t", env)
    end
end

-- shell environment setup
local dynamic_env = {}
local global_env
if getfenv then
    global_env = getfenv(0)    
else
    global_env = _ENV
end
for key, val in pairs(global_env) do
    dynamic_env[key] = val
end

-- shell logic
local function load_chunk(code, env)
    local loaded, err = load_compat("return " .. code, env)
    if not loaded then
        loaded, err = load_compat(code, env)
        if not loaded then
            return nil, err
        end
    end
    return loaded, err
end

local function handle_execute(code)
    local loaded, err = load_chunk(code, dynamic_env)
    if not loaded then
        return nil, err
    end
    outcome = table.pack(xpcall(loaded, debug.traceback))
    success = outcome[1]
    if not success then
        return nil, outcome[2]
    end
    return success, table.pack(select(2, table.unpack(outcome)))
end

local function handle_is_complete(code)
    local loaded, err = load_chunk(code, dynamic_env)
    if loaded then
        return 'complete'
    elseif string.sub(err, -#("<eof>")) == "<eof>" then
        return 'incomplete'
    else
        return 'invalid'
    end
end

local cmd_pipe = assert(io.open(cmd_pipe_path, "rb"))
local ret_pipe = assert(io.open(ret_pipe_path, "wb"))

while true do
    local message = json.decode(netstring.read(cmd_pipe))
    if message.type == "echo" then
        netstring.write(ret_pipe, json.encode(message))
    elseif message.type == "execute" then
        local success, ret_val = handle_execute(message.payload)
        success = success or false
        if success then
            dynamic_env['_'] = function()
                return table.unpack(ret_val)
            end
            local tmp = {}
            for i=1, ret_val.n do
                tmp[i] = inspect(ret_val[i], {newline="", indent=""})
            end
            ret_val = table.concat(tmp, "\t")
        end
        netstring.write(ret_pipe, json.encode({
            type = "execute",
            payload = {
                success = success,
                returned = ret_val
            }
        }))
    elseif message.type == "is_complete" then
        local status = handle_is_complete(message.payload)
        netstring.write(ret_pipe, json.encode({
            type = "is_complete",
            payload = status
        }))
    else
        error("Unknown message type")
    end
    ret_pipe:flush()
end

cmd_pipe:close()
ret_pipe:close()
