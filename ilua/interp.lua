local dynamic_env = {}
for key,val in pairs(_ENV) do
    dynamic_env[key] = val
end

local cmd_pipe_path, ret_pipe_path, lib_path = table.unpack(arg, 1, 3)

-- Windows supports / as dirsep
local netstring = dofile(lib_path .. "/netstring.lua/netstring.lua")
local json = dofile(lib_path .. "/json.lua/json.lua")

-- competabillity setup
if not table.pack then
    function table.pack (...)       -- luacheck: ignore
        return {n=select('#',...); ...}
    end
end

if not table.unpack then
    table.unpack = unpack
end

local handle_execute = nil
local handle_is_complete = nil
if getfenv then
    -- lua 5.1 impl
    error("Not implemented yet")
    handle_execute = function(code)

    end
else
    -- lua 5.2 impl
    handle_execute = function(code)
        local loaded, err = load(code, "=(ilua)", "t", dynamic_env)
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

    handle_is_complete = function(code)
        local loaded, err = load(code, "=(ilua)", "t", dynamic_env)
        if not loaded then
            return nil, err
        end
        return true
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
        netstring.write(ret_pipe, json.encode({
            type = "execute",
            payload = {
                success = success,
                returned = ret_val
            }
        }))
    elseif message.type == "is_complete" then
        local success, ret_val = handle_is_complete(message.payload)
        netstring.write(ret_pipe, json.encode({
            type = "is_complete",
            payload = {
                complete = success
            }
        }))
    else
        error("Unknown message type")
    end
    ret_pipe:flush()
end

cmd_pipe:close()
ret_pipe:close()
