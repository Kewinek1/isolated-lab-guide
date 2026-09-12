import test from 'node:test';
import assert from 'node:assert/strict';
import {diagramMarkup, normalizeDiagram} from '../app/diagrams.js';

const source='flowchart LR\n A --> B';
const path='figures/mermaid/0123456789abcdef0123.svg';
const resource=path=>'https://example.com/guide/'+path;
const index={diagrams:{[source]:{path,alt:'Route <example>'}}};

test('Mermaid produces an accessible local illustration with optional escaped source',()=>{
 const html=diagramMarkup('\r\n'+source.replaceAll('\n','\r\n')+'\r\n',index,resource);
 assert.match(html,/<figure class="mermaid-figure">/);
 assert.ok(html.includes('src="https://example.com/guide/'+path+'"'));
 assert.ok(html.includes('alt="Route &lt;example&gt;"'));
 assert.match(html,/<details class="diagram-source">/);
 assert.ok(!html.includes('<details class="diagram-source" open'));
 assert.equal(normalizeDiagram('\rA\rB\r'), 'A\nB');
});

test('Missing assets and untrusted asset paths show escaped source instead',()=>{
 for(const candidate of [null,{}, {diagrams:{[source]:{path:'https://example.com/remote.svg'}}},
                         {diagrams:{[source]:{path:'../private/image.svg'}}},
                         {diagrams:Object.create({[source]:{path}})}]){
  const html=diagramMarkup(source,candidate,resource);
  assert.match(html,/diagram-unavailable/);
  assert.ok(!html.includes('<img'));
 }
 assert.ok(!diagramMarkup('<script>alert(1)</script>',{},resource).includes('<script>'));
});
