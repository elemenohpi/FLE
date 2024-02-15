-- This file implements handling of jsonrpc-ish requests arriving as strings

-- In addition to json serialization, this code also replaces empty objects with empty arrays
-- due to the fact that lua cannot differentiate.
-- This means we cannot have empty objects, however it is easier to add an unused key
-- to an object to avoid empty objects than to add an unused element to every array.
function serialize(value)
  if value == nil then
    return 'null'
  elseif type(value) == 'string' then
    return '"' .. value .. '"'
  end
  -- Wrapped with () to prevent gsub returning a multival
  return (string.gsub(game.table_to_json(value), '{}', '[]'))
end

local function invoke_rpc(procedures, request_string)
  local deserialize_succeeded, deserialize_result = xpcall(
    game.json_to_table,
    debug.traceback,
    request_string)
  if not deserialize_succeeded then
    return {
      error = {
        code = 400,
        message = 'Failed to deserialize request_string',
        data = deserialize_result
      }
    }
  end
  local request = deserialize_result
  local method = procedures[request.method]
  if method == nil then
    return {
      error = {
        code = 404,
        message = string.format('No method named "%s"', request.method),
      }
    }
  end
  local method_succeeded, result = xpcall(method, debug.traceback, table.unpack(request.params))
  if method_succeeded then
    return {
      result = result,
      -- _preserve_table is a throwaway key to prevent
      -- crazy lua empty object == empty array shenanigans
      -- in the event that result == nil/null
      _preserve_table = true
    }
  else
    return {
      error = {
        code = 500,
        message = string.format('Error during "%s"', request.method),
        data = result
      }
    }
  end
end

local function call_and_serialize_result(procedures, request_string)
  return serialize(invoke_rpc(procedures, request_string))
end

-- procedures: A table of functions which can be called
-- request_string: the un-parsed RPC call
local function call_and_handle_unhandled_errors(procedures, request_string)
  local suceeded, response = xpcall(
    call_and_serialize_result,
    debug.traceback,
    procedures,
    request_string)
  if suceeded then
    return response
  else
    return serialize({
      error = {
        code = 500,
        message = 'Unhandled error',
        data = response
      }
    })
  end
end

return {
  dispatch_rpc = call_and_handle_unhandled_errors
}
