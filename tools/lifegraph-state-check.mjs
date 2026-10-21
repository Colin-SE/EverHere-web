/* 验证共享引用、收起与环的真实行为，避免画布出现幽灵节点。 */
import assert from 'node:assert/strict';
import {LifeGraphState} from '../app/static/js/lifegraph-state.js';

const node=key=>({key,label:key}),edge=(a,b)=>({id:a+'|'+b,source:a,target:b});
const graph=new LifeGraphState();
graph.applyPage({focus:'now',nodes:['now','a','b'].map(node),edges:[edge('now','a'),edge('now','b')],nextCursor:null});
graph.applyPage({focus:'a',nodes:['a','shared'].map(node),edges:[edge('a','shared')],nextCursor:null});
graph.applyPage({focus:'b',nodes:['b','shared'].map(node),edges:[edge('b','shared')],nextCursor:null});
graph.applyPage({focus:'shared',nodes:['shared','a'].map(node),edges:[edge('a','shared')],nextCursor:null});
assert.equal(graph.visible().nodes.length,4);
graph.collapse('a');assert.equal(graph.visible().nodes.filter(node=>node.key==='shared').length,1);
graph.collapse('b');assert.deepEqual(new Set(graph.visible().nodes.map(node=>node.key)),new Set(['now','a','b']));
assert.equal(graph.branches.has('shared'),false);
graph.reconcile({nodes:['now','a'].map(node),edges:[edge('now','a')]});
assert.deepEqual(new Set(graph.visible().nodes.map(node=>node.key)),new Set(['now','a']));
console.log('PASS: 共享节点引用、环去重、收起分支与删除后授权复核');
