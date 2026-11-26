// Shared layout for both the topic preview and the map after diagnosis.
(function (root) {
  function layout(nodes, edges, goalId, spacing = 145, padding = 60) {
    const byId = new Map(nodes.map(node => [node.competency_id, node]));
    const parents = new Map();
    for (const edge of edges) {
      if (!parents.has(edge.competency_id)) parents.set(edge.competency_id, []);
      parents.get(edge.competency_id).push(edge.prerequisite_id);
    }
    const depths = new Map(), visiting = new Set(), usedEdges = new Map();
    function visit(id) {
      if (depths.has(id)) return depths.get(id);
      if (visiting.has(id)) throw new Error('В связях карты найден цикл. Нужна проверка данных.');
      if (!byId.has(id)) throw new Error('Связанная тема не найдена. Нужна проверка данных.');
      visiting.add(id);
      const dependencies = parents.get(id) || [];
      const levels = dependencies.map(parent => {
        const depth = visit(parent);
        usedEdges.set(`${parent}:${id}`, {prerequisite_id:parent, competency_id:id});
        return depth;
      });
      visiting.delete(id);
      const depth = levels.length ? Math.max(...levels) + 1 : 0;
      depths.set(id, depth);
      return depth;
    }
    const maxDepth = visit(goalId);
    const rows = Array.from({length:maxDepth + 1}, () => []);
    for (const node of nodes) if (depths.has(node.competency_id)) rows[depths.get(node.competency_id)].push(node);
    const maxRow = Math.max(...rows.map(row => row.length));
    const width = Math.max(620, maxRow * 245);
    const height = maxDepth * spacing + 2 * padding;
    const points = new Map();
    // Spread prerequisites only where a node has multiple incoming links.
    // A simple chain stays centered; a shared prerequisite remains one node.
    const preferred = new Map();
    for (const [child, dependencies] of parents) {
      if (!depths.has(child) || dependencies.length < 2) continue;
      dependencies.forEach((id, index) => {
        if (!preferred.has(id)) preferred.set(id, index % 2 === 0 ? 0.66 : 0.34);
      });
    }
    for (const [depth, row] of rows.entries()) {
      row.forEach((node, index) => {
        const x = row.length === 1
          ? (preferred.get(node.competency_id) ?? 0.5)
          : (index + .5) / row.length;
        points.set(node.competency_id, {x:x * 1000, y:padding + depth * spacing});
      });
    }
    return {nodes:nodes.filter(node => depths.has(node.competency_id)), edges:[...usedEdges.values()], points, width, height};
  }
  root.RemiMapLayout = {layout};
  if (typeof module !== 'undefined') module.exports = root.RemiMapLayout;
})(globalThis);
