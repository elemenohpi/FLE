local void_fast_inserter = table.deepcopy(data.raw["inserter"]["fast-inserter"])

void_fast_inserter.name = "fle-void-fast-inserter"
void_fast_inserter.energy_source = { type = "void" }

data:extend{void_fast_inserter}
