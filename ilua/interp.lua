-- ILua
-- Copyright (C) 2018  guysv

-- This file is part of ILua which is released under GPLv2.
-- See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
-- for full license details.

local cmd_pipe_path = assert(os.getenv("ILUA_CMD_PATH"))
local ret_pipe_path = assert(os.getenv("ILUA_RET_PATH"))

local netstring = require"ext.netstring"
local json = require"ext.json"
local inspect = require"ext.inspect"
local builtins = require"builtins"

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
    end
    return loaded, err
end

local function handle_execute(code)
    local loaded, err = load_chunk(code, dynamic_env)
    if not loaded then
        return nil, err
    end
    outcome = table.pack(xpcall(loaded, debug.traceback))

    dynamic_env.io.stdout:flush()
    dynamic_env.io.stderr:flush()

    success = outcome[1]
    if not success then
        local traceback = outcome[2]
        if type(traceback) ~= "string" then
            traceback = ("(error object is a %s value)"):format(type(traceback))
        end
        return nil, traceback
    end
    local returned = table.pack(select(2, table.unpack(outcome, 1, outcome.n)))
    if returned.n > 0 then
        dynamic_env['_'] = returned[1]
    else
        dynamic_env['_'] = nil
    end
    return success, returned
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

local function get_matches(obj, matches, only_methods)
    if type(obj) == 'table' then
        for key, value in pairs(obj) do
            if type(key) == 'string' and
                    key:match("^[_a-zA-Z][_a-zA-Z0-9]*$") and
                    (not only_methods or type(value) == 'function') then
                matches[#matches+1] = key
            end
        end
    end
    local mt = getmetatable(obj)
    if mt and mt.__index then
        get_matches(mt.__index, matches, only_methods)
    end
end

local function handle_complete(breadcrumbs, only_methods)
    local subject_obj = dynamic_env
    local matches = {}
    for _, key in ipairs(breadcrumbs) do
        subject_obj = subject_obj[key]
        if not subject_obj then
            return matches
        end
    end
    get_matches(subject_obj, matches, methods_only)
    return matches
end

local function handle_info(breadcrumbs)
    local subject_obj = dynamic_env
    for _, key in ipairs(breadcrumbs) do
        subject_obj = subject_obj[key]
        if not subject_obj then
            return false
        end
    end
    if type(subject_obj) ~= "function" then
        return false -- nil will be lost in json encoding
    else
        local info = debug.getinfo(subject_obj, "S")
        local builtin_info = builtins[subject_obj]
        if builtin_info then
            info.preloaded_info = true
            info.func_signature = builtin_info['signature']
            info.func_documentation = builtin_info['documentation']
        else
            info.preloaded_info = false
        end
        return info
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
        if not success then
            success = false
        end
        if success then
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
    elseif message.type == 'complete' then
        local matches = handle_complete(message.payload.breadcrumbs,
                                        message.payload.only_methods)
        netstring.write(ret_pipe, json.encode({
            type = "complete",
            payload = matches
        }))
    elseif message.type == 'info' then
        local info = handle_info(message.payload.breadcrumbs)
        netstring.write(ret_pipe, json.encode({
            type = "info",
            payload = info
        }))
    else
        error("Unknown message type")
    end
    ret_pipe:flush()
end

cmd_pipe:close()
ret_pipe:close()
