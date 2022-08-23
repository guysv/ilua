-- ILua
-- Copyright (C) 2018  guysv

-- This file is part of ILua which is released under GPLv2.
-- See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
-- for full license details.

local cjson = require "cjson"
local inspect = require"inspect"
local builtins = require "builtins"

-- Compatibility setup
table.pack = table.pack or function (...)
    return {n=select('#',...); ...}
end
table.unpack = table.unpack or unpack

local load_compat

if setfenv then
    function load_compat(code, env)
        local loaded, err
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
    local outcome = table.pack(xpcall(loaded, debug.traceback))

    dynamic_env.io.stdout:flush()
    dynamic_env.io.stderr:flush()

    local success = outcome[1]
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
    -- TODO: currently only works on lua implementations
    --       that mimic the original lua error format
    --       gopher-lua for example does not work
    elseif err:match"['\"]?<eof>['\"]?$" then
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

local _M = {}

function _M.handle_websocket_message(data)
    local message = cjson.decode(data)
    if not message then
        return
    end

    if message.type == "echo" then
        return cjson.encode(message)
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
        return cjson.encode({
            type = "execute",
            payload = {
                success = success,
                returned = ret_val
            }
        })
    elseif message.type == "is_complete" then
        local status = handle_is_complete(message.payload)
        return cjson.encode({
            type = "is_complete",
            payload = status
        })
    elseif message.type == 'complete' then
        local matches = handle_complete(message.payload.breadcrumbs,
                                        message.payload.only_methods)
        return cjson.encode({
            type = "complete",
            payload = matches
        })
    elseif message.type == 'info' then
        local info = handle_info(message.payload.breadcrumbs)
        return cjson.encode({
            type = "info",
            payload = info
        })
    else
        return cjson.encode({
            type = "error",
            payload = "Unknown message type" .. message.type
        })
    end
end

return _M