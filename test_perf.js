const perf_hooks = require('perf_hooks');

const agents = Array.from({ length: 10000 }, (_, i) => ({ id: `agent_${i}`, name: `Agent ${i}` }));
const agent_ids = Array.from({ length: 1000 }, (_, i) => `agent_${Math.floor(Math.random() * 10000)}`);

const team = { members: { agent_ids } };

// Baseline
const startBaseline = perf_hooks.performance.now();
const agentChipsBaseline = (team.members?.agent_ids ?? [])
  .map((id) => agents.find((a) => a.id === id))
  .filter((a) => Boolean(a));
const endBaseline = perf_hooks.performance.now();

// Optimized
const startOptimized = perf_hooks.performance.now();
const agentMap = new Map(agents.map(a => [a.id, a]));
const agentChipsOptimized = (team.members?.agent_ids ?? [])
  .map((id) => agentMap.get(id))
  .filter((a) => Boolean(a));
const endOptimized = perf_hooks.performance.now();

console.log(`Baseline: ${endBaseline - startBaseline} ms`);
console.log(`Optimized: ${endOptimized - startOptimized} ms`);
