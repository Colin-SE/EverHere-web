import {t,h,m,locale} from './i18n.js';
/* 展开只改变视图；每个分支维护自己的引用，共享节点和环不会重复创建。 */
export class LifeGraphState {
  constructor(){this.reset();}
  reset(root='now'){this.root=root;this.nodes=new Map();this.branches=new Map();this.positions=new Map();}
  applyPage(page,append=false){
    const previous=append?this.branches.get(page.focus):null;
    const branch={keys:new Set(previous?.keys||[]),edges:new Map(previous?.edges||[]),cursor:page.nextCursor};
    for(const node of page.nodes)branch.keys.add(node.key);
    for(const edge of page.edges)branch.edges.set(edge.id,edge);
    const projected=new Set([...this.visible().nodes.map(node=>node.key),...branch.keys]);
    if(projected.size>80)throw new Error(t('当前已展开较多内容，请先收起一部分，或重新聚焦后继续探索。'));
    for(const node of page.nodes)this.nodes.set(node.key,node);
    this.branches.set(page.focus,branch);
  }
  visible(){
    const keys=new Set([this.root]),edges=new Map(),visited=new Set(),pending=[this.root];
    while(pending.length){
      const anchor=pending.shift();if(visited.has(anchor))continue;visited.add(anchor);
      const branch=this.branches.get(anchor);if(!branch)continue;
      const reachable=new Set([anchor]);let changed=true;
      while(changed){changed=false;for(const edge of branch.edges.values()){
        if(!this.nodes.has(edge.source)||!this.nodes.has(edge.target))continue;
        if(reachable.has(edge.source)||reachable.has(edge.target)){
          if(!reachable.has(edge.source)||!reachable.has(edge.target))changed=true;
          reachable.add(edge.source);reachable.add(edge.target);edges.set(edge.id,edge);
        }
      }}
      for(const key of reachable)if(!keys.has(key)){keys.add(key);pending.push(key);}
    }
    return {nodes:[...keys].map(key=>this.nodes.get(key)).filter(Boolean),edges:[...edges.values()].filter(edge=>keys.has(edge.source)&&keys.has(edge.target))};
  }
  collapse(key){this.branches.delete(key);this.prune();}
  prune(){const visible=new Set(this.visible().nodes.map(node=>node.key));for(const key of this.branches.keys())if(!visible.has(key))this.branches.delete(key);for(const key of this.nodes.keys())if(!visible.has(key)){this.nodes.delete(key);this.positions.delete(key);}}
  reconcile(snapshot){
    const live=new Map(snapshot.nodes.map(node=>[node.key,node]));
    this.nodes=live;
    const actual=new Map(snapshot.edges.map(edge=>[edge.id,edge]));
    for(const [anchor,branch] of this.branches){
      if(!live.has(anchor)){this.branches.delete(anchor);continue;}
      branch.keys=new Set([...branch.keys].filter(key=>live.has(key)));
      branch.edges=new Map([...actual].filter(([,edge])=>branch.keys.has(edge.source)&&branch.keys.has(edge.target)));
    }
    this.prune();
    return live.has(this.root);
  }
}
