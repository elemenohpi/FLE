local rpc = require('rpc')

local function table_invert(t)
  local s={}
  for k,v in pairs(t) do
    s[v]=k
  end
  return s
end

local direction_to_string = table_invert(defines.direction)

local function get_direction(direction_name)
  local direction = defines.direction[direction_name]
  if direction == nil then
    error(string.format('Expected valid direction but got "%s"', direction_name))
  end
  return direction
end

local function EntityDescription(e)
  return {
    unit_number = e.unit_number,
    surface = e.surface.name,
    name = e.name,
    position = e.position,
    direction = direction_to_string[e.direction],
    force = e.force.name
  }
end

-- Checks for collision before creating
-- Currently returns nil iff can_place_entity returns false
-- If we introdure more reasons to not create the entity, consider adding a structured
-- response with a reason so that callers can decide which failures are acceptable
local function create_entity(config)
  local surface = game.surfaces[config.surface]
  if surface == nil then
    error(string.format('Could not find surface with id "%s"', config.surface))
  end
  local entity_creation_params = {
    name = config.name,
    position = config.position,
    direction = get_direction(config.direction),
    force = config.force,
    target = nil,
    source = nil,
    fast_replace = false,
    player = nil,
    spill = true,
    raise_built = true,
    create_build_effect_smoke = false,
    spawn_decorations = true,
    move_stuck_players = true,
    item = nil,
  }
  if config.entity_specific_parameters ~= nil then
    for k,v in pairs(config.entity_specific_parameters) do
      entity_creation_params[k] = v
    end
  end

  local can_place = surface.can_place_entity({
    name = entity_creation_params.name,
    position = entity_creation_params.position,
    direction = entity_creation_params.direction,
    force = entity_creation_params.force,
    build_check_type = defines.build_check_type.manual,
    forced = false,
    inner_name = entity_creation_params.inner_name
  })
  if not can_place then
    return nil
  end

  local e = surface.create_entity(entity_creation_params)
  if e == nil then
    error(string.format('Failed to create "%s"', config.name))
  end
  return EntityDescription(e)
end

local function find_entities(area, surface_name)
  local surface = game.surfaces[surface_name]
  if surface == nil then
    error(string.format('Could not find surface with id "%s"', surface_name))
  end
  entities = surface.find_entities(area)
  result = {}
  for _, e in ipairs(entities) do
    table.insert(result, EntityDescription(e))
  end
  return result
end

local function insert_items(entity_description, item_stack)
  local surface = game.surfaces[entity_description.surface]
  if surface == nil then
    error(string.format('Could not find surface with id "%s"', entity_description.surface))
  end
  local entity = surface.find_entity(entity_description.name, entity_description.position)
  if entity == nil then
    error(string.format('Could not find entity with name "%s"', entity_description.name))
  end
  return entity.get_output_inventory().insert(item_stack)
end

local function get_inventory_contents(entity_description)
  local surface = game.surfaces[entity_description.surface]
  if surface == nil then
    error(string.format('Could not find surface with id "%s"', entity_description.surface))
  end
  local entity = surface.find_entity(entity_description.name, entity_description.position)
  if entity == nil then
    error(string.format('Could not find entity with name "%s"', entity_description.name))
  end
  local contents = entity.get_output_inventory().get_contents()
  -- in case of empty tables
  contents._preserve_table = true
  return contents
end

local function destroy_all_entities(surface_id)
  local surface = game.surfaces[surface_id]
  if surface == nil then
    error(string.format('Could not find surface with id "%s"', surface_id))
  end
  local entities = surface.find_entities_filtered{}
  for _, e in ipairs(entities) do
    local succeeded = e.destroy()
    if not succeeded then
      error(string.format('Entity was valid and destruction failed, name: %s, x: %s, y: %s', e.name, e.position.x, e.position.y))
    end
  end
end

-- Multipliers: 1.0 = 60 "UPS" Factorio ticks per-second

-- When not simulating, we want to reduce game speed to reduce cpu usage because factorio still runs a certain amount of logic when ticks are paused.
-- But we also need to be careful no to introduce too much api-call latency as we must tick to handle RPCs.
local paused_speed = 1 -- 60 UPS
local step_speed = 100000 -- It is impossible to actually achieve this speed, we just want max possible sim speed.

local function step(num_ticks)
  global.target_tick = global.target_tick + num_ticks
  game.speed = step_speed
  game.ticks_to_run = game.ticks_to_run + num_ticks
end

script.on_event(defines.events.on_tick, function()
  if global.target_tick == game.tick then
    -- We don't need to pause, ticks_to_run takes care of that, just reduce sim rate again
    game.speed = paused_speed
  end
end)

rpcs = {
  step = step,
  create_entity = create_entity,
  find_entities = find_entities,
  insert_items = insert_items,
  get_inventory_contents = get_inventory_contents,
  destroy_all_entities = destroy_all_entities,
  -- Testing methods
  test_echo = function(x) return x end,
  test_error = function() error('Test error!') end,
  test_nil = function() return nil end,
}

local function call(request_string)
  -- log(string.format('fle REQUEST: %s', request_string))
  local response = rpc.dispatch_rpc(rpcs, request_string)
  -- log(string.format('fle RESPONSE: %s', response))
  return response
end

remote.add_interface('fle', { call = call })

script.on_init(function()
  global.target_tick = game.tick
  game.tick_paused = true -- Pause on init so that the game only simulates when instructed
  game.speed = paused_speed
end)
