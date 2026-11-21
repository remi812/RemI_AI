const test = require('node:test');
const assert = require('node:assert/strict');
const {layout} = require('../app/static/map-layout.js');

test('общая основа отображается один раз и сохраняет обе связи', () => {
  const nodes = [1, 2, 3, 4, 5].map(competency_id => ({competency_id}));
  const edges = [
    {prerequisite_id:1, competency_id:2}, {prerequisite_id:1, competency_id:3},
    {prerequisite_id:2, competency_id:4}, {prerequisite_id:3, competency_id:4},
  ];
  const graph = layout(nodes, edges, 4);
  assert.deepEqual(graph.nodes.map(n => n.competency_id), [1, 2, 3, 4]);
  assert.equal(graph.edges.length, 4);
  assert.ok(graph.points.get(1).y < graph.points.get(2).y);
  assert.ok(graph.points.get(4).y > graph.points.get(3).y);
  assert.notEqual(graph.points.get(2).x, graph.points.get(3).x);
  assert.equal(layout(nodes, edges, 2).nodes.length, 2);
});

test('ошибочные циклические связи не скрываются и не вызывают зависание', () => {
  const nodes = [1, 2].map(competency_id => ({competency_id}));
  const edges = [{prerequisite_id:1, competency_id:2}, {prerequisite_id:2, competency_id:1}];
  assert.throws(() => layout(nodes, edges, 2), /цикл/);
});

test('узлы ответвления располагаются по разным сторонам', () => {
  const nodes = [1, 2, 21, 25, 26, 28].map(competency_id => ({competency_id}));
  const edges = [
    {competency_id:2, prerequisite_id:1}, {competency_id:25, prerequisite_id:26},
    {competency_id:26, prerequisite_id:1}, {competency_id:28, prerequisite_id:2},
    {competency_id:2, prerequisite_id:25}, {competency_id:1, prerequisite_id:21},
  ];
  const graph = layout(nodes, edges, 28);
  assert.ok(graph.points.get(25).x < graph.points.get(1).x);
  assert.equal(graph.nodes.length, 6);
  assert.equal(graph.edges.length, 6);
});
