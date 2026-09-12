import {esc} from './model.js';

export const normalizeDiagram = source => source.replace(/\r\n?/g, '\n').trim();

export function diagramMarkup(source, index, resource) {
 const key=normalizeDiagram(source), entries=index?.diagrams;
 const entry=entries && Object.hasOwn(entries,key)?entries[key]:null;
 const fallback='<pre><code>'+esc(source)+'</code></pre>';
 if(!entry || !/^figures\/mermaid\/[a-f0-9]{20}\.svg$/.test(entry.path)) return '<div class="diagram-unavailable"><p>The diagram is unavailable. Its source is shown below.</p>'+fallback+'</div>';
 const url=esc(resource(entry.path)), alt=esc(entry.alt||'Network diagram');
 return '<figure class="mermaid-figure"><div class="mermaid-canvas"><img src="'+url+'" alt="'+alt+'"></div><figcaption>'+alt+' <a href="'+url+'" target="_blank" rel="noopener">Open full size ↗</a></figcaption><details class="diagram-source"><summary>View diagram source</summary>'+fallback+'</details></figure>';
}
