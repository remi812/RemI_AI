function drawSkillMap(graph, pilot, goal, results, enterNode) {
  graph.replaceChildren();
  const layout = RemiMapLayout.layout(pilot.nodes, pilot.edges, goal.competency_id);
  graph.style.height = `${layout.height}px`;
  graph.style.minWidth = `${layout.width}px`;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 1000 ${layout.height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  for (const edge of layout.edges) {
    const from = layout.points.get(edge.prerequisite_id), to = layout.points.get(edge.competency_id);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const middle = (from.y + to.y) / 2;
    line.setAttribute('d', `M ${from.x} ${from.y} C ${from.x} ${middle}, ${to.x} ${middle}, ${to.x} ${to.y}`);
    svg.append(line);
  }
  graph.append(svg);
  const labels = {preliminary_correct:'Предварительно верно', mastered:'Предварительно освоено', possible_gap:'Вероятный пробел', needs_review:'Требует уточнения', not_assessed:'Не проверено'};
  for (const node of layout.nodes) {
    const point = layout.points.get(node.competency_id);
    const result = results[node.name] || {status:'not_assessed', correct:0, total:0};
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `graph-node ${result.status}${node.competency_id === goal.competency_id ? ' goal' : ''}`;
    button.style.left = `${point.x / 10}%`;
    button.style.top = `${point.y}px`;
    const name = document.createElement('strong'); name.textContent = node.name;
    const status = document.createElement('small');
    status.textContent = `${labels[result.status]}${result.total ? ` · ${result.correct} из ${result.total}` : ''}`;
    button.append(name, status);
    button.addEventListener('click', () => enterNode(node, button, graph));
    graph.append(button);
  }
}

