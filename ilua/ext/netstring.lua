--
-- netstring.lua
--
-- Copyright (c) 2018 guysv
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy of
-- this software and associated documentation files (the "Software"), to deal in
-- the Software without restriction, including without limitation the rights to
-- use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
-- of the Software, and to permit persons to whom the Software is furnished to do
-- so, subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in all
-- copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
-- IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
-- FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
-- AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
-- LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
-- OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
-- SOFTWARE.
--

--- A lightweight Netstring library for Lua
-- @module netstring

local netstring = {_version = "0.2.0"}

--- Default maximum data length for read and write operations
-- @see netstring.read
-- @see netstring.write
netstring.DEFAULT_MAX_LENGTH = 9999999

-- Calculate upper limit of number of length characters
local function length_str_size(length)
    return math.ceil(math.log(length,10)) + 1
end

-- Build a netstring from data
local function format_net_string(data)
    return ("%i:%s,"):format(#data, data)
end

--- Read a single netstring from stream with optional maximum
-- length max_length, decode it and return the decoded data
-- @param stream io.file-like object to read data from
-- @param max_length maximum length of payload to read
--                   before dropping
--                   (Defaults to @{DEFAULT_MAX_LENGTH})
-- @return the decoded data from the netstring
function netstring.read(stream, max_length)
    -- Calculate upper limits on length section
    local max_length = max_length or
        netstring.DEFAULT_MAX_LENGTH
    local max_length_str = length_str_size(max_length)

    local length = {}

    -- Read length
    while true do
        -- Length is log10(#data) so it's not that bad
        local char_read = assert(stream:read(1))
        -- End of length characters
        if char_read == ":" then
            break
        end

        table.insert(length, char_read)
        -- Test if length string exeeds its limit
        if #length > max_length_str then
            error("Length exeeds maximum length allowed")
        end
    end

    length = table.concat(length)
    -- Test length string against spec format
    if not length:match("[1-9][0-9]*") and length ~= "0" then
        error("Length is invalid")
    end

    -- Convert to number
    length = tonumber(length)
    if length > max_length then
        error("Length exeeds maximum length allowed")
    end

    -- Read string
    local data = assert(stream:read(length))

    -- Find ending character
    if stream:read(1) ~= "," then
        error("Could not read ending character")
    end

    return data
end

--- Write data (with optional enforced length of max_length)
-- into stream, encoded as netstring
-- @param stream io.file-like object to write data into
-- @param data data to encode into the stream
-- @param max_length maximum length of payload to write
--                   (Defaults to @{DEFAULT_MAX_LENGTH})
-- @return true on success
function netstring.write(stream, data, max_length)
    -- Calculate upper limits on length
    local max_length = max_length or
        netstring.DEFAULT_MAX_LENGTH

    -- Test length
    if #data > max_length then
        error("Length exeeds maximum length allowed")
    end

    -- Write string to stream
    assert(stream:write(format_net_string(data)))
    return true
end

return netstring
