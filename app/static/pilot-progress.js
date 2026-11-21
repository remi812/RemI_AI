// Локальный результат одного учебного пилота. Ответы и персональные данные не записываются.
(function (root) {
  function key(pilot) {
    const slug = pilot?.slug || 'derivatives';
    return `remi.${slug}.progress.v1`;
  }
  const labels = new Set(['preliminary_correct', 'needs_review', 'not_assessed']);
  function graphKey(pilot) {
    const nodes = pilot.nodes.map(node => [node.competency_id, node.name]).sort((a, b) => a[0] - b[0]);
    const edges = pilot.edges.map(edge => [edge.prerequisite_id, edge.competency_id])
      .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return JSON.stringify([pilot.goal, nodes, edges]);
  }
  function valid(results, pilot) {
    if (!results || typeof results !== 'object' || Array.isArray(results)) return false;
    const names = pilot.nodes.map(node => node.name);
    if (Object.keys(results).length !== names.length || new Set(names).size !== names.length) return false;
    return names.every(name => {
      const r = results[name];
      if (!r || !labels.has(r.status) || !Number.isInteger(r.total) || !Number.isInteger(r.correct)) return false;
      if (r.total < 0 || r.correct < 0 || r.correct > r.total) return false;
      if (r.status === 'not_assessed') return r.total === 0 && r.correct === 0;
      if (r.total !== 2) return false;
      return r.status === (r.correct === r.total ? 'preliminary_correct' : 'needs_review');
    });
  }
  function save(storage, pilot, results) {
    if (!valid(results, pilot)) return false;
    try {
      storage.setItem(key(pilot), JSON.stringify({version: 1, graph: graphKey(pilot), results, savedAt: new Date().toISOString()}));
      return true;
    } catch { return false; }
  }
  function load(storage, pilot) {
    try {
      const value = JSON.parse(storage.getItem(key(pilot)));
      if (!value || value.version !== 1 || value.graph !== graphKey(pilot) || !valid(value.results, pilot)) return null;
      return value;
    } catch { return null; }
  }
  function clear(storage, pilot) {
    try { storage.removeItem(key(pilot)); return true; } catch { return false; }
  }
  root.RemiPilotProgress = { save, load, clear };
  if (typeof module !== 'undefined') module.exports = root.RemiPilotProgress;
})(globalThis);
