
import {esc, sample, validate, scenarios, rows, command, steps, diagram, concepts, icon, publicFigure, buildInputs, platforms} from "./model.js";
import {diagramMarkup} from "./diagrams.js";
const $=id=>document.getElementById(id);
const SITE_ROOT=new URL("../",import.meta.url);
const resource=path=>new URL(path,SITE_ROOT).href;
let diagramIndexPromise;
const loadDiagramIndex=()=>diagramIndexPromise ||= fetch(resource("app/diagram-index.json")).then(r=>{if(!r.ok)throw Error("Missing diagram index");return r.json();}).catch(()=>({diagrams:{}}));
const state={scenario:"offline",site:"A",step:0,plans:{A:sample("A"),B:sample("B"),C:sample("C")},edited:new Set(),platformChosen:new Set(),private:false};
const fields=[["mainRouter","Home router label"],["labRouter","Experimental router label"],["firewall","Trusted firewall label"],["labCidr","Lab subnet · /24"],["target","Linux target address"],["pico","Pico W address"],["relayCidr","Relay subnet · /24"],["managementCidr","Management subnet · /24"],["serviceCidr","Services subnet · /24"],["homeCidr","Home subnet · optional /24"],["relayHost","Approved relay VPN IP / DNS"],["gameHost","Approved game VPN IP / DNS"]];
const docs=[
 ["Start here","docs/START-HERE.md"],["Networking foundations","docs/01-foundations.md"],["Compare architectures","network/ARCHITECTURES.md"],["Choose firewall software","docs/PLATFORMS.md"],["Build the first lab","docs/03-build.md"],["OpenWrt firewall","network/OPENWRT.md"],["pfSense / OPNsense layouts","network/PFSENSE-OPNSENSE.md"],["Connect participants","network/REMOTE-ACCESS.md"],["WireGuard alternative","network/wireguard/README.md"],["Uno, Pico & Linux code","firmware/README.md"],["Firmware analysis","docs/FIRMWARE-ANALYSIS.md"],["Minecraft & Factorio","games/README.md"],["Verify isolation","network/VALIDATION.md"],["Operate & recover","docs/06-operations.md"],["Scope & worksheets","docs/07-worksheets.md"],["Sources","docs/SOURCES.md"],["Publish safely","README.md"],["Publish on GitHub","docs/PUBLISHING.md"]
];
let currentDoc="docs/START-HERE.md",docCounter=0,toastTimer;
function toast(text){$("toast").textContent=text;$("toast").classList.add("visible");clearTimeout(toastTimer);toastTimer=setTimeout(()=>$("toast").classList.remove("visible"),3000);}
function download(name,body,type="application/json"){const url=URL.createObjectURL(new Blob([body],{type}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function table(items){return '<table class="address-grid"><tbody>'+items.map(([a,b])=>'<tr><th scope="row">'+esc(a)+'</th><td>'+esc(b)+'</td></tr>').join("")+'</tbody></table>';}
fields.splice(9,0,["homeTransitCidr","Home-transit subnet · edge /24"]);
function renderForm(){const p=state.plans[state.site];$("plan-fields").innerHTML='<input type="hidden" name="firewallPlatform" value="'+esc(p.firewallPlatform)+'">'+fields.map(([key,label])=>'<label>'+label+'<input name="'+key+'" value="'+esc(p[key])+'" maxlength="'+(["mainRouter","labRouter","firewall"].includes(key)?48:253)+'" autocomplete="off" spellcheck="false"></label>').join("");$("plan-error").textContent="";}
function render(){
 const p=state.plans[state.site],s=scenarios.find(x=>x.id===state.scenario),flow=steps(s.id,p),step=flow[state.step];
 $("scenario-buttons").innerHTML=scenarios.map((item,i)=>'<button data-scenario="'+item.id+'" aria-pressed="'+(s.id===item.id)+'"><span>0'+(i+1)+'</span>'+item.title+'</button>').join("");
 document.querySelectorAll("[data-site]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.site===state.site)));
 $("scenario-status").textContent=s.label;$("scenario-description").textContent=s.description;
 $("firewall-platform").value=p.firewallPlatform;
 $("platform-note").textContent=s.id==="offline"?"An offline bench needs no new firewall. This selection applies when planning an online boundary.":platforms[p.firewallPlatform]+" is a software choice; the selected wiring still needs supported hardware and explicit rules. "+((p.firewallPlatform!=="openwrt" || s.id!=="tunnel")?"This layout has a manual firewall recipe.":"A reviewed OpenWrt candidate can be prepared for the dedicated firewall.");
 $("diagram").innerHTML=diagram(s.id,p,step[2]);
 $("packet-title").textContent=step[0];$("packet-description").textContent=step[1];$("packet-count").textContent=String(state.step+1).padStart(2,"0")+" / 05";
 $("packet-prev").disabled=state.step===0;$("packet-next").textContent=state.step===4?"Start again ↺":"Next hop →";
 $("address-table").innerHTML=table(rows(s.id,p));$("requirements").innerHTML=s.requirements.map(r=>'<li>'+esc(r)+'</li>').join("");
 $("recipe-link").dataset.doc=(["single","tunnel"].includes(s.id)&&p.firewallPlatform!=="openwrt")?"network/PFSENSE-OPNSENSE.md":s.doc;$("connection-command").textContent=command(s.id,p);
 $("data-caption").textContent=state.edited.has(state.site)?"LOCAL PLAN · NOT AUTO-VERIFIED":state.private&&state.site==="A"?"LOCAL LABELS · PROPOSED EXAMPLE ADDRESSES":"FICTIONAL ADDRESS PLAN";
 $("edition").textContent=state.private?"PRIVATE LOCAL EDITION":state.edited.size?"LOCAL EDITS · DO NOT PUBLISH":"PUBLIC · FICTIONAL DATA";
 renderForm();
}
$("scenario-buttons").addEventListener("click",e=>{const b=e.target.closest("[data-scenario]");if(b){state.scenario=b.dataset.scenario;if(!state.platformChosen.has(state.site))state.plans[state.site].firewallPlatform=["edge","split"].includes(state.scenario)?"pfsense":"openwrt";state.step=0;render();}});
$("firewall-platform").onchange=e=>{state.plans[state.site].firewallPlatform=e.target.value;state.platformChosen.add(state.site);render();};
document.querySelectorAll("[data-site]").forEach(b=>b.addEventListener("click",()=>{state.site=b.dataset.site;if(!state.platformChosen.has(state.site))state.plans[state.site].firewallPlatform=["edge","split"].includes(state.scenario)?"pfsense":"openwrt";state.step=0;render();}));
$("packet-prev").onclick=()=>{state.step=Math.max(0,state.step-1);render();};
$("packet-next").onclick=()=>{state.step=(state.step+1)%5;render();};
$("plan-form").onsubmit=e=>{e.preventDefault();const plan={site:state.site,...Object.fromEntries(new FormData(e.target))};for(const k of Object.keys(plan))plan[k]=plan[k].trim();const errors=validate(plan);if(errors.length){$("plan-error").textContent=errors.join(" ");return;}state.plans[state.site]=plan;state.edited.add(state.site);render();toast("Local plan updated. No network settings changed.");};
$("reset-plan").onclick=()=>{state.plans[state.site]=sample(state.site);if(["edge","split"].includes(state.scenario))state.plans[state.site].firewallPlatform="pfsense";state.platformChosen.delete(state.site);state.edited.delete(state.site);render();toast("Fictional example restored.");};
$("download-plan").onclick=()=>{download("PRIVATE-site-"+state.site+"-plan.json",JSON.stringify({classification:"PRIVATE — DO NOT PUBLISH",scenario:state.scenario,address_status:state.edited.has(state.site)?"operator supplied; unverified":"proposed fictional examples",...state.plans[state.site]},null,2)+"\n");toast("Private plan downloaded. Store it outside the public package.");};
$("download-config").onclick=()=>{try{download("config.local.json",JSON.stringify(buildInputs(state.plans[state.site],state.scenario),null,2)+"\n");toast("Private builder inputs downloaded. Wi-Fi and deployment remain disabled.");}catch(error){toast(error.message);}};
$("public-figure").onclick=()=>{const svg=publicFigure(state.scenario,state.site);download("public-"+state.scenario+"-site-"+state.site+".svg",svg,"image/svg+xml");toast("Figure rebuilt from fictional defaults. Local fields were excluded.");};
$("copy-command").onclick=async()=>{try{await navigator.clipboard.writeText($("connection-command").textContent);toast("Connection example copied.");}catch{toast("Clipboard unavailable. Select the command text to copy.");}};

function renderConcept(index){
 $("concept-tabs").innerHTML=concepts.map((c,i)=>'<button data-concept="'+i+'" aria-pressed="'+(i===index)+'">'+esc(c[0])+'</button>').join("");
 const c=concepts[index];$("concept-panel").innerHTML='<div><div class="term-number">'+esc(c[0])+'</div><h3>'+esc(c[1])+'</h3><p>'+esc(c[2])+'</p></div><dl>'+c[3].map(([term,definition])=>'<dt>'+esc(term)+'</dt><dd>'+esc(definition)+'</dd>').join("")+'</dl>';
}
$("concept-tabs").onclick=e=>{const b=e.target.closest("[data-concept]");if(b)renderConcept(Number(b.dataset.concept));};
const hardware=[
 ["board","MICROCONTROLLER","Arduino Uno / Uno R3","Runs one small program. USB serial provides a command terminal. Classic Uno boards have no built-in Ethernet or Wi-Fi.","START: USB → SERIAL COMMAND → LED"],
 ["board","WI-FI MICROCONTROLLER","Raspberry Pi Pico W","Runs MicroPython or C/C++ firmware. Suitable for a small Wi-Fi service and GPIO experiments. It does not run Raspberry Pi OS.","START: LAB WI-FI → HTTP → LED"],
 ["server","FULL COMPUTER","Linux Pi / PC","A full Linux Raspberry Pi, suitable PC or VM can run a relay or target. A Docker target host shares its kernel with containers; keep the trusted relay and clean game server separate.","ONE ROLE PER TRUST BOUNDARY"],
 ["firewall","FIREWALL COMPUTER","Supported router / appliance","pfSense and OPNsense commonly use compatible 64-bit x86 computers. OpenWrt supports specific router and board revisions. A red case or Ethernet socket does not establish compatibility.","CHECK MODEL, CPU, NICs & MAINTAINED IMAGE"]
];
$("hardware-cards").innerHTML=hardware.map(([symbol,label,title,body,role])=>'<div class="hardware-card"><svg viewBox="0 0 120 75" aria-hidden="true">'+icon(symbol,36,7,1.5)+'</svg><span class="small-label">'+label+'</span><h3>'+title+'</h3><p>'+body+'</p><div class="role">'+role+'</div></div>').join("");
// Markdown is escaped before formatting. Raw HTML is never interpreted.
function inline(text,path){
 const tokens=[]; const hold=html=>{const n=tokens.length;tokens.push(html);return "\u0001"+n+"\u0002";};
 let value=text.replace(/`([^`]+)`/g,(_,code)=>hold("<code>"+esc(code)+"</code>"));
 value=value.replace(/\[([^\]]+)\]\(([^)]+)\)/g,(_,label,url)=>{
  if(/^(https?:\/\/)/i.test(url))return hold('<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>');
  if(/^(?:[a-z]+:|\/\/)/i.test(url))return esc(label);
  try{const resolved=new URL(url,resource(path));if(resolved.origin!==SITE_ROOT.origin || !resolved.pathname.startsWith(SITE_ROOT.pathname))return esc(label);const doc=resolved.pathname.slice(SITE_ROOT.pathname.length);return hold('<a href="'+esc(resolved.pathname+resolved.hash)+'"'+(doc.endsWith(".md")?' data-doc="'+esc(doc)+'" data-section="'+esc(resolved.hash.slice(1))+'"':' target="_blank" rel="noopener"')+'>'+esc(label)+'</a>');}catch{return esc(label);}
 });
 value=esc(value).replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/\*([^*]+)\*/g,"<em>$1</em>");
 return value.replace(/\u0001(\d+)\u0002/g,(_,n)=>tokens[Number(n)]);
}
function markdown(text,path,diagramIndex){
 const lines=text.replace(/\r/g,"").split("\n");let out="",list=null;const headingCounts=new Map();
 const close=()=>{if(list){out+="</"+list+">";list=null;}};
 for(let i=0;i<lines.length;i++){const line=lines[i];
  const fence=line.match(/^\s*(`{3,}|~{3,})([^`~]*)$/);
  if(fence){close();const language=fence[2].trim().toLowerCase(),end=new RegExp("^\\s*"+fence[1][0]+"{"+fence[1].length+",}\\s*$");let code=[];while(++i<lines.length&&!end.test(lines[i]))code.push(lines[i]);const source=code.join("\n");out+=language==="mermaid"?diagramMarkup(source,diagramIndex,resource):"<pre><code>"+esc(source)+"</code></pre>";continue;}
  if(!line.trim()){close();continue;}
  const illustration=line.match(/^!\[([^\]]*)\]\(([^)]+\.svg)\)$/);if(illustration){close();try{const url=new URL(illustration[2],resource(path));if(url.origin===SITE_ROOT.origin && url.pathname.startsWith(SITE_ROOT.pathname+"figures/"))out+='<figure class="doc-figure"><img src="'+esc(url.href)+'" alt="'+esc(illustration[1])+'"><figcaption>'+esc(illustration[1])+'</figcaption></figure>';}catch{}continue;}
  const h=line.match(/^(#{1,6})\s+(.+)$/);if(h){close();const slug=h[2].toLowerCase().replace(/[^\p{L}\p{N}_\-\s]/gu,"").replace(/\s/g,"-");const count=headingCounts.get(slug)||0;headingCounts.set(slug,count+1);out+='<h'+h[1].length+' id="'+esc(slug+(count?"-"+count:""))+'">'+inline(h[2],path)+"</h"+h[1].length+">";continue;}
  if(line.includes("|")&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){close();const cells=l=>l.trim().replace(/^\||\|$/g,"").split("|").map(x=>x.trim());out+="<table><thead><tr>"+cells(line).map(x=>"<th>"+inline(x,path)+"</th>").join("")+"</tr></thead><tbody>";i++;while(i+1<lines.length&&lines[i+1].includes("|")&&lines[i+1].trim()){i++;out+="<tr>"+cells(lines[i]).map(x=>"<td>"+inline(x,path)+"</td>").join("")+"</tr>";}out+="</tbody></table>";continue;}
  const li=line.match(/^\s*(?:[-*]|\d+\.)\s+(.+)$/);if(li){const type=/^\s*\d+\./.test(line)?"ol":"ul";if(list!==type){close();list=type;out+="<"+type+">";}out+="<li>"+inline(li[1],path)+"</li>";continue;}
  close();if(/^>\s?/.test(line)){out+="<blockquote>"+inline(line.replace(/^>\s?/,""),path)+"</blockquote>";continue;}
  if(/^[-_]{3,}\s*$/.test(line)){out+="<hr>";continue;}
  let para=line;while(i+1<lines.length&&lines[i+1].trim()&&!/^(?:\s*[-*]\s|\s*\d+\.\s|#{1,6}\s|\s*(?:`{3,}|~{3,})|>|\|)/.test(lines[i+1]))para+=" "+lines[++i];
  out+="<p>"+inline(para,path)+"</p>";
 }close();return out;
}
async function loadDoc(path,section=""){
 const generation=++docCounter;currentDoc=path;
 document.querySelectorAll("#doc-nav button").forEach(b=>b.classList.toggle("active",b.dataset.doc===path));
 $("doc-content").setAttribute("aria-busy","true");
 try{const [response,diagramIndex]=await Promise.all([fetch(resource(path)),loadDiagramIndex()]);if(!response.ok)throw new Error("Unavailable document");const text=await response.text();if(generation!==docCounter)return;
 $("doc-content").innerHTML='<div class="doc-actions"><span>REFERENCE / '+esc(path)+'</span><a href="'+esc(resource(path))+'" target="_blank" rel="noopener">Open source ↗</a></div>'+markdown(text,path,diagramIndex);$("doc-content").scrollTop=0;
 if(section){let id=section;try{id=decodeURIComponent(section);}catch{}const target=Array.from($("doc-content").querySelectorAll("[id]")).find(n=>n.id===id);if(target)target.scrollIntoView({block:"start"});}
 }catch{if(generation===docCounter)$("doc-content").innerHTML="<p>This chapter could not be loaded. Start the local server from the complete public package, then reload.</p>";}
 finally{if(generation===docCounter)$("doc-content").setAttribute("aria-busy","false");}
}
$("doc-nav").innerHTML=docs.map(([label,path],i)=>'<button data-doc="'+path+'">'+String(i+1).padStart(2,"0")+' / '+label+'</button>').join("");
document.addEventListener("click",e=>{const link=e.target.closest("[data-doc]");if(link){e.preventDefault();loadDoc(link.dataset.doc,link.dataset.section||"");if(!link.closest("#doc-content")&&!link.closest("#doc-nav"))$("library").scrollIntoView();}});
document.querySelectorAll(".sidebar nav a").forEach(a=>a.onclick=()=>{document.querySelectorAll(".sidebar nav a").forEach(x=>x.classList.remove("selected"));a.classList.add("selected");});
async function initPrivate(){
 if(document.querySelector('meta[name="lab-edition"][content="public-static"]') || !["127.0.0.1","localhost"].includes(location.hostname) || SITE_ROOT.pathname!=="/")return;
 try{const r=await fetch("/api/mode");if(!r.ok)return;const mode=await r.json();if(!mode.private_available)return;
 $("private-toggle").hidden=false;
 $("private-toggle").onclick=async()=>{
  if(state.private){location.reload();return;}
  const response=await fetch("/api/private-profile");if(!response.ok){toast("Private profile unavailable.");return;}
  const data=await response.json();state.private=true;
  Object.assign(state.plans.A,{mainRouter:data.labels.mainRouter,labRouter:data.labels.labRouter,firewall:data.labels.firewall});
  $("private-toggle").textContent="Return to public";$("hardware-edition").textContent="IDENTIFIED EQUIPMENT · LOCAL ONLY";
  $("private-inventory").hidden=false;$("private-inventory").innerHTML='<span class="tag">PRIVATE INVENTORY / PHOTO REVIEW</span><h3 class="inventory-title">The current equipment path</h3><ul>'+data.inventory.map(item=>'<li><strong>'+esc(item.name)+':</strong> '+esc(item.note)+'</li>').join("")+'</ul><p>'+esc(data.address_note)+'</p><p><a href="/api/private-guide" target="_blank" rel="noopener">Open the local start guide ↗</a> · <a href="/api/private-inventory" target="_blank" rel="noopener">Open the full photo inventory ↗</a></p>';
  state.site="A";render();toast("Local hardware loaded. All shown addresses remain proposed examples.");
 };
 }catch{/* Public-only static deployments have no private endpoints. */}
}
render();renderConcept(0);loadDoc(currentDoc);initPrivate();

export async function preparePrintBook(){
 const diagramIndex=await loadDiagramIndex();
 const book=document.getElementById("print-book") || document.body.appendChild(Object.assign(document.createElement("div"),{id:"print-book",className:"print-book prose"}));
 const chapters=await Promise.all(docs.map(async ([title,path])=>{const r=await fetch(resource(path));if(!r.ok)throw Error("Missing chapter: "+path);return '<section class="book-chapter"><div class="eyebrow">FIELD MANUAL / '+esc(title)+'</div>'+markdown(await r.text(),path,diagramIndex)+'</section>';}));
 let local="";
 if(state.private){for(const [name,path] of [["Local start guide","/api/private-guide"],["Identified inventory","/api/private-inventory"]]){const r=await fetch(path);if(!r.ok)throw Error("Missing private chapter");local+='<section class="book-chapter"><div class="eyebrow">PRIVATE / '+name+'</div>'+markdown(await r.text(),"private/"+name+".md",diagramIndex)+'</section>';}}
 book.innerHTML='<section class="book-cover"><div class="eyebrow">LAB / FIELD MANUAL · '+(state.private?"PRIVATE LOCAL EDITION":"PUBLIC EDITION")+'</div><h1>Build a lab.<br>Keep home out.</h1><p>A visual guide to isolated networks, small devices and shared experiments.</p><p>September 2026. All public network examples are fictional. This manual prepares a design; physical hardware and isolation require on-site validation.</p><p>Code and editable documentation accompany this manual in the public package.</p><h2>Reading order</h2><ol>'+docs.map(([name])=>'<li>'+name+'</li>').join("")+'</ol></section>'+local+scenarios.map(s=>'<section class="book-chapter"><div class="eyebrow">ARCHITECTURE / '+s.label+'</div><h1>'+s.title+'</h1><p>'+s.description+'</p><div class="book-figure">'+publicFigure(s.id,"A")+'</div><ul>'+s.requirements.map(r=>'<li>'+r+'</li>').join("")+'</ul></section>').join("")+chapters.join("");
 await Promise.all(Array.from(book.querySelectorAll("img")).map(img=>img.decode()));
 document.body.classList.add("printing-book");return {chapters:chapters.length,private:state.private};
}
$("print").onclick=async()=>{const b=$("print");b.disabled=true;b.textContent="Preparing…";try{await preparePrintBook();window.print();}catch(error){toast("Unable to prepare the complete manual. Check that every chapter is installed.");}finally{b.disabled=false;b.textContent="Print / PDF ↗";}};
window.addEventListener("afterprint",()=>document.body.classList.remove("printing-book"));
