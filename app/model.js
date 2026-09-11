
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
export function sample(site="A") {
 const n={A:10,B:20,C:30}[site] || 10;
 return {site, mainRouter:"Home router", labRouter:"Experimental router", firewall:"Trusted firewall", labCidr:"10.77."+n+".0/24", target:"10.77."+n+".20", pico:"10.77."+n+".30", relayCidr:"10.78."+n+".0/24", managementCidr:"10.79."+n+".0/24", serviceCidr:"10.80."+n+".0/24", homeCidr:"", relayHost:"relay-"+site.toLowerCase()+".example.invalid", gameHost:"games-"+site.toLowerCase()+".example.invalid"};
}
export function ipv4(value) {
 if(!/^\d{1,3}(\.\d{1,3}){3}$/.test(value)) return null;
 const a=value.split(".").map(Number);
 if(a.some((n,i)=>n>255 || String(n)!==value.split(".")[i])) return null;
 return a;
}
export function network(value) {
 const [ip,prefix,...rest]=value.split("/"); const a=ipv4(ip);
 if(!a || rest.length || prefix!=="24" || a[3]!==0) return null;
 return a;
}
export const base = cidr => cidr.split(".").slice(0,3).join(".");
export function validate(p) {
 const errors=[];
 for(const k of ["mainRouter","labRouter","firewall"]) if(!p[k] || p[k].length>48 || /[<>\x00-\x1f]/.test(p[k])) errors.push(k+": use a plain label of 1–48 characters.");
 const keys=["labCidr","relayCidr","managementCidr","serviceCidr",...(p.homeCidr?["homeCidr"]:[])];
 const nets=keys.map(k=>network(p[k]));
 keys.forEach((k,i)=>{ if(!nets[i]) errors.push(k+": enter a network ending in .0/24."); });
 if(new Set(keys.map(k=>p[k])).size!==keys.length) errors.push("Home, lab, relay, management and services must use distinct subnets.");
 for(const key of ["target","pico"]){const a=ipv4(p[key]);if(!a || !network(p.labCidr) || base(p[key])!==base(p.labCidr) || a[3]<2 || a[3]>254) errors.push(key+": use a host in the lab subnet, from .2 to .254.");}
 if(p.target===p.pico) errors.push("The Linux target and Pico need different addresses.");
 for(const k of ["relayHost","gameHost"]) if(!/^[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?$/.test(p[k]) || p[k].includes("..")) errors.push(k+": use an IPv4 address or a DNS hostname, with no spaces or shell characters.");
 return errors;
}
export const scenarios = [
 {id:"offline",title:"Offline bench",label:"START HERE",description:"An independent lab has no cable or wireless route to the home network or internet. Suitable for the first router and microcontroller experiments.",doc:"network/ARCHITECTURES.md",requirements:["Experimental router WAN port remains unplugged. Only lab devices join its LAN or lab Wi-Fi.","The lab laptop has home Wi-Fi, other network adapters, forwarding and connection sharing disabled during the session.","No remote participation yet. Download tools and firmware before disconnecting; use the current boards with their onboard LEDs."]},
 {id:"single",title:"One capable router",label:"CAPABILITY REQUIRED",description:"One maintained firewall can separate home, management, services and targets using independent ports or properly configured VLANs. A consumer DMZ-host checkbox does not provide these zones.",doc:"network/ARCHITECTURES.md",requirements:["A maintained router with independently filtered zones; a guest-network label alone is insufficient evidence.","Separate physical ports, or a managed switch and correctly assigned VLANs. An unmanaged switch does not create isolation.","The experimental router stays inside the target zone. Home access, router management, IPv6 and internet egress are denied from targets."]},
 {id:"tunnel",title:"Connect the sites",label:"RECOMMENDED ONLINE PATH",description:"A separate trusted firewall contains the targets. A dedicated relay accepts narrowly permitted encrypted connections; only an approved service crosses into the lab.",doc:"network/REMOTE-ACCESS.md",requirements:["Add a maintained firewall and a Linux relay. The relay and target occupy separate networks; the relay is not an attack target.","Create a private overlay with explicit participant policy, individual accounts and restricted SSH forwarding. No home subnet advertisements or exit nodes.","Keep target-initiated traffic blocked, including internet access. Validate from an actual target before enabling remote participation."]},
 {id:"games",title:"Host a game",label:"CLEAN SERVICES ZONE",description:"Minecraft or Factorio runs on a suitable Linux computer in a separate services zone. Participants connect to its private overlay address, with game ports explicitly allowed.",doc:"games/README.md",requirements:["A full Linux computer with sufficient CPU, RAM and storage. A Pico W or Uno cannot host these game servers.","Use a clean server outside the attack zone; restrict access to Minecraft Java TCP 25565 or Factorio UDP 34197.","Back up worlds, configure authentication and allowlists, and match client/server versions. Broad public-internet access is not required."]},
 {id:"dmz",title:"Understand DMZ",label:"EXPLANATION · DO NOT DEPLOY",description:"A consumer DMZ host forwards unsolicited incoming traffic to one device. It does not create a separate security zone or stop a compromised device from contacting the home LAN.",doc:"network/ARCHITECTURES.md",requirements:["Leave the home router's DMZ-host option off for this project.","A real DMZ is a separate network with firewall rules toward home, internet and management.","Two nested routers usually permit downstream-to-upstream connections. NAT is address translation; it is not proof of isolation."]}
];
export function rows(id,p) {
 const lab=[["Lab subnet",p.labCidr],["Lab gateway / router",base(p.labCidr)+".1"],["Linux target",p.target+":8081"],["Pico W",p.pico+":8080"]];
 if(id==="offline") return [...lab,["Home / internet","Disconnected"],["Remote access","Unavailable"]];
 if(id==="dmz") return [["Public incoming traffic","Forwarded broadly to DMZ host"],["Home subnet",p.homeCidr||"Not collected"],["Isolation","Not established by DMZ host"]];
 if(id==="games") return [["Services subnet",p.serviceCidr],["Linux server (planned)",base(p.serviceCidr)+".20"],["Overlay destination",p.gameHost],["Minecraft Java","TCP 25565"],["Factorio","UDP 34197"],["Target-to-services traffic","Denied"]];
 return [...lab,["Relay subnet",p.relayCidr],["Relay address",base(p.relayCidr)+".2"],["Management subnet",p.managementCidr],["Home subnet",p.homeCidr||"Not collected"],["Overlay destination",id==="tunnel"?p.relayHost:"Not configured"]];
}
export function command(id,p) {
 if(id==="offline") return "# Run on the isolated lab laptop after assigning the lab addresses.\n# Pico token mode requires the Authorization header; see firmware guide.\ncurl --max-time 3 http://"+p.pico+":8080/status";
 if(id==="tunnel") return "# Replace the reserved example hostname with the approved relay VPN IP.\n# Account name and key must match the privately assigned forwarding account.\n# Keep this terminal open. Read network/REMOTE-ACCESS.md first.\nssh -N -T -i ~/.ssh/lab_forwarding -o ExitOnForwardFailure=yes -L 127.0.0.1:18080:"+p.pico+":8080 lab-operator-a@"+p.relayHost+"\n\n# In another terminal: add the private token header in token mode.\ncurl --max-time 3 http://127.0.0.1:18080/status";
 if(id==="games") return "# Enter the approved private destination in the game client.\nMinecraft Java: "+p.gameHost+":25565\nFactorio: "+p.gameHost+":34197\n\n# See games/README.md for the guarded launchers and server configuration.";
 if(id==="dmz") return "# No DMZ-host configuration is generated.\n# Select a genuinely separated firewall design first.";
 return "# Configure separate interfaces/zones before connecting any target.\n# Generate and review a dedicated firewall candidate using:\npython3 network/generate_firewall.py --help\n\n# The dedicated-firewall recipe is not a replacement config for a home router.\n# See network/OPENWRT.md for interface mapping and recovery.";
}
export function steps(id,p){
 const table={
 offline:[["A request starts on the bench","The lab laptop addresses "+p.pico+" directly. No VPN is involved.","client"],["The local network carries it","The experimental router's LAN switch or access point delivers local traffic. Its WAN cable remains unplugged.","labrouter"],["The Pico receives HTTP","TCP port 8080 reaches the LED/status program. Token mode checks a credential; HTTP remains plaintext on this local hop.","target"],["The reply returns locally","The board replies to the lab laptop. A separate routed network is not involved.","client"],["Home stays disconnected","No shared Wi-Fi, Ethernet bridge or connection-sharing path may join the lab to home.","home"]],
 single:[["Separate networks share a firewall","Each port or VLAN maps to one zone. Traffic within a VLAN may bypass routed firewall checks.","firewall"],["The target initiates a connection","A compromised target may try to contact home, management, services or the internet.","target"],["The trusted boundary denies it","The target zone has no forwarding permission to these destinations. IPv6 must be contained as well.","firewall"],["A permitted session is specific","An administrator or relay receives a narrowly defined exception, with return traffic tracked.","relay"],["The boundary is not the experiment","Root access on the experimental router must not grant access to the firewall or its administration credentials.","target"]],
 tunnel:[["A remote participant starts SSH","The destination is "+p.relayHost+". The operator shares its actual address privately after granting access.","remote"],["The overlay encrypts transport","Tailscale establishes a direct or relayed encrypted path. The home router needs no broad inbound forwarding.","internet"],["A dedicated relay checks access","Overlay policy and an individual SSH key permit only a forwarding account; no general shell is required.","relay"],["The firewall permits one destination","The relay may reach "+p.pico+":8080 through the trusted firewall. Target-initiated connections remain denied.","firewall"],["The last hop reaches the Pico","HTTP reaches the board over the isolated lab. That final hop is not end-to-end TLS; other lab devices may observe or interfere with it.","target"]],
 games:[["A player opens the private server","The client selects "+p.gameHost+" and the appropriate game port.","remote"],["The overlay checks permission","Only the approved player identities reach game ports. Router administration and attack targets are outside this grant.","internet"],["The service runs on Linux","The server binds to its approved overlay address. Authentication and the game allowlist still apply.","game"],["The worlds stay separate","The services zone has no target-to-server path. Backups belong outside the writable game account.","firewall"],["Traffic returns through the tunnel","The game response follows the existing encrypted session. Game updates and public HTTPS egress require a separate reviewed policy.","remote"]],
 dmz:[["An outside packet arrives","A DMZ-host setting may send otherwise unmatched public incoming traffic to one LAN device.","internet"],["The home router forwards it","This is broad address/port forwarding, not the creation of another network.","home"],["The exposed device is still inside","Its attachment point has not moved into an independently filtered zone.","target"],["A downstream WAN also points inward","A second router connected WAN-to-home-LAN normally permits its clients to initiate connections to that upstream LAN.","labrouter"],["Replace the assumption with a boundary","Use an offline bench or separate trusted zones. Do not use the consumer DMZ-host setting for these experiments.","home"]]
 };return table[id];
}
const iconPaths={
 router:'<rect x="2" y="17" width="38" height="15" rx="2"/><path d="M8 17V4m26 13V4M8 26h1m6 0h1m6 0h1"/><path d="M4 7q4-6 8 0M30 7q4-6 8 0"/>',
 firewall:'<path d="M21 3 38 10v13q-2 10-17 17Q6 33 4 23V10z"/><path d="m12 21 6 6 12-13"/>',
 laptop:'<rect x="6" y="5" width="30" height="23" rx="1"/><path d="M6 28 2 35h38l-4-7M17 32h8"/>',
 board:'<rect x="10" y="2" width="22" height="36" rx="2"/><rect x="16" y="15" width="10" height="10"/><path d="M16 2v6h10V2M5 11h5m-5 7h5m-5 7h5m-5 7h5m22-21h5m-5 7h5m-5 7h5m-5 7h5"/>',
 server:'<rect x="7" y="2" width="28" height="36"/><path d="M7 14h28M7 26h28M13 8h3m-3 12h3m-3 12h3m7-24h6m-6 12h6m-6 12h6"/>',
 globe:'<circle cx="21" cy="21" r="18"/><ellipse cx="21" cy="21" rx="8" ry="18"/><path d="M3 21h36M7 10h28M7 32h28"/>',
 home:'<path d="m2 19 19-16 19 16M7 15v23h28V15M17 38V25h8v13"/>'
};
export function icon(type,x=0,y=0,scale=1){return '<g transform="translate('+x+' '+y+') scale('+scale+')" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'+iconPaths[type]+'</g>';}
function node(id,x,y,title,subtitle,type,active,w=195){
 const fill=active===id?"#111":"#fff",ink=active===id?"#fff":"#111";
 return '<g data-node="'+id+'" color="'+ink+'"><rect x="'+x+'" y="'+y+'" width="'+w+'" height="88" fill="'+fill+'" stroke="#111"/>'+icon(type,x+15,y+20,.85)+'<text x="'+(x+61)+'" y="'+(y+36)+'" fill="'+ink+'" font-size="12" font-weight="600">'+esc(title)+'</text><text x="'+(x+61)+'" y="'+(y+57)+'" fill="'+ink+'" font-size="9" font-family="monospace">'+esc(subtitle)+'</text></g>';
}
function link(x1,y1,x2,y2,label="",dashed=false){return '<path d="M'+x1+' '+y1+' L'+x2+' '+y2+'" fill="none" stroke="#111" stroke-width="1.3" '+(dashed?'stroke-dasharray="6 5"':'')+'/>'+(label?'<text x="'+((x1+x2)/2)+'" y="'+((y1+y2)/2-10)+'" text-anchor="middle" font-size="9" fill="#555">'+esc(label)+'</text>':'');}
function boundary(x,y,w,h,title){return '<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" fill="#f5f5f3" stroke="#bbb"/><text x="'+(x+15)+'" y="'+(y+24)+'" font-size="9" font-family="monospace" letter-spacing="1.2">'+esc(title)+'</text>';}
export function diagram(id,p,active=""){
 let body='<title id="diagram-title">'+esc(scenarios.find(s=>s.id===id).title)+' — Site '+p.site+'</title><desc id="diagram-desc">'+esc(scenarios.find(s=>s.id===id).description)+'</desc><rect width="1100" height="470" fill="white"/>';
 const short=s=>s.length>21?s.slice(0,19)+"…":s;
 if(id==="offline"){
 body+=boundary(20,30,270,405,"HOME / OUTSIDE THE LAB")+boundary(340,30,740,405,"ISOLATED BENCH / NO UPLINK");
 body+=link(390,182,660,182,"Local Ethernet / lab Wi-Fi")+link(855,182,945,182)+link(755,226,755,327,"LAN only");
 body+=node("home",55,142,short(p.mainRouter),"Ordinary home devices","home",active)+node("client",365,138,"Lab laptop",base(p.labCidr)+".10","laptop",active)+node("labrouter",660,138,short(p.labRouter),base(p.labCidr)+".1","router",active)+node("target",660,327,"Pico W",p.pico+":8080","board",active);
 body+='<text x="610" y="280" font-size="12" text-anchor="middle">× WAN unplugged · home Wi-Fi off</text><text x="150" y="345" font-size="11" text-anchor="middle">No physical or wireless path</text><text x="950" y="200" font-size="10" text-anchor="middle">WAN ×</text>';
 }else if(id==="single"){
 body+=boundary(20,30,275,405,"TRUSTED HOME ZONE")+boundary(695,30,385,240,"UNTRUSTED TARGET ZONE")+boundary(695,290,385,145,"RELAY / SEPARATE ZONE");
 body+=link(247,178,430,178,"Separate port / VLAN")+link(625,178,755,178,"Filtered")+link(526,222,526,370)+link(526,370,755,370,"Specific permission");
 body+=node("home",52,134,"Home devices","Protected zone","home",active)+node("firewall",430,134,short(p.firewall),"One maintained gateway","firewall",active)+node("target",755,134,"Lab targets",p.labCidr,"board",active)+node("relay",755,327,"Dedicated relay",p.relayCidr,"server",active);
 body+='<text x="487" y="64" font-size="11">Internet uplink</text>'+link(526,73,526,134)+'<text x="485" y="281" font-size="11">× Targets → home / internet</text>';
 }else if(id==="tunnel"){
 body+=boundary(20,262,280,176,"PROTECTED HOME")+boundary(340,262,335,176,"TRUSTED BOUNDARY")+boundary(715,262,365,176,"TARGETS / NO INTERNET EGRESS");
 body+=link(237,103,400,103,"Encrypted overlay",true)+link(595,103,815,103,"Encrypted overlay",true)+link(915,147,915,229)+link(915,229,530,229,"Relay → firewall → one permitted target")+link(530,229,530,327)+link(245,371,430,371,"Uplink")+link(625,371,785,371,"TCP 8080 only");
 body+=node("remote",42,59,"Remote participant","Site "+(p.site==="A"?"B / C":p.site==="B"?"A / C":"A / B"),"laptop",active)+node("internet",400,59,"Private overlay","Direct / relayed","globe",active)+node("relay",815,59,"Dedicated Linux relay",base(p.relayCidr)+".2","server",active)+node("home",50,327,short(p.mainRouter),"WAN transport only","home",active)+node("firewall",430,327,short(p.firewall),"Deny targets → uplink","firewall",active)+node("target",785,327,"Pico / lab target",p.pico+":8080","board",active);
 body+='<text x="442" y="195" font-size="10">Relay has a separate interface / VLAN, never a bridge into home.</text>';
 }else if(id==="games"){
 body+=boundary(20,260,275,175,"HOME / PROTECTED")+boundary(705,30,375,210,"CLEAN SERVICES ZONE")+boundary(705,260,375,175,"SEPARATE ATTACK ZONE");
 body+=link(257,137,408,137,"Encrypted tunnel",true)+link(603,137,765,137,"Game ports only",true)+link(508,181,508,336)+link(247,371,408,371,"Uplink")+link(603,371,765,371);
 body+=link(862,181,862,248)+link(862,248,645,248,"Services interface")+link(645,248,645,371)+link(645,371,603,371);
 body+=node("remote",62,93,"Approved player","Individual identity","laptop",active)+node("internet",408,93,"Private overlay","No public game forward","globe",active)+node("game",765,93,"Linux game server","TCP 25565 / UDP 34197","server",active)+node("home",52,327,short(p.mainRouter),"Home network","home",active)+node("firewall",408,327,short(p.firewall),"Separate services zone","firewall",active)+node("target",765,327,"Experiment targets",p.labCidr,"board",active);
 body+='<text x="704" y="355" text-anchor="middle" font-size="24">×</text><text x="770" y="218" font-size="10">Bind to the approved overlay address.</text>';
 }else{
 body+=boundary(20,250,1060,185,"SAME HOME LAN / NO ISOLATION CREATED");
 body+=link(275,118,450,118,"Public incoming traffic")+link(548,162,548,306)+link(548,350,788,350,"Broad forwarding")+link(188,350,450,350,"Same LAN");
 body+=node("internet",80,74,"Internet","Unsolicited traffic","globe",active)+node("home",450,74,short(p.mainRouter),"Consumer DMZ setting","router",active)+node("labrouter",450,306,"Experimental router","WAN on the home LAN","router",active)+node("target",788,306,"DMZ host","Exposed device","server",active)+node("client",90,306,"Home devices","Still reachable upstream","home",active);
 body+='<text x="766" y="122" font-size="26">DMZ host ≠ isolated zone</text><text x="766" y="148" font-size="11">This drawing explains the failure, not a setup to deploy.</text>';
 }
 return body;
}
export const concepts=[
 ["01 / Local network","Addresses & neighbours","A device first needs an address on the local network. Nearby devices exchange traffic through a switch or Wi-Fi access point.",[["IP address","A delivery address for one network interface. It is not a password or a permanent identity."],["Subnet","A group of neighbouring addresses. In these examples, /24 groups addresses with the same first three numbers."],["DHCP","A service that lends addresses automatically. A reservation keeps a chosen device at a predictable address."]]],
 ["02 / Between networks","Routes & translation","Traffic for a different subnet goes to a gateway. The gateway needs a route and must also allow the traffic.",[["Router / gateway","A device that forwards packets between networks. A route describes where to send them."],["WAN and LAN","Port roles: WAN points upstream; LAN faces the local network. The labels do not guarantee a security boundary."],["NAT","Network address translation changes packet addresses. It often hides inbound hosts, but commonly permits outbound access to upstream home devices."]]],
 ["03 / A boundary","Zones & permission","Separate address ranges describe the design. Independent attachment points and firewall rules enforce it.",[["Firewall zone","A group of interfaces with a shared policy. Deny-by-default means a connection needs an explicit exception."],["VLAN","A logical separation on Ethernet. A managed switch and correct port assignment are needed; the firewall controls traffic between VLANs."],["Stateful filtering","The firewall remembers an allowed connection so its replies can return. A reply is different from a new target-initiated connection."]]],
 ["04 / Between sites","Tunnels & services","Remote access carries a specific service across an untrusted network. The lab still needs local containment.",[["VPN / overlay","An encrypted network between approved machines. It does not automatically isolate those machines from their physical LANs."],["Port / protocol","A service endpoint: Minecraft Java commonly uses TCP 25565; Factorio uses UDP 34197. TCP and UDP are different transports."],["Reverse proxy","An application intermediary, often for HTTP. It can publish a service, but is neither a general VPN nor a boundary around a compromised host."]]]
];

export function publicFigure(id,site="A") {
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 505" font-family="Arial,Helvetica,sans-serif">'+diagram(id,sample(site))+'<text x="25" y="490" font-size="10" fill="#555">PUBLIC EXAMPLE · ALL ADDRESSES FICTIONAL · '+esc(scenarios.find(s=>s.id===id).title)+'</text></svg>';
}

export function buildInputs(plan) {
 const errors=validate(plan);
 if(!["A","B","C"].includes(plan.site)) errors.push("Choose site A, B or C.");
 if(errors.length) throw new Error(errors.join(" "));
 for(const key of ["labCidr","relayCidr","managementCidr"]){
  const address=network(plan[key]);
  if(!(address[0]===10 || (address[0]===172 && address[1]>=16 && address[1]<=31) || (address[0]===192 && address[1]===168))) throw new Error(key+": the private builder requires an RFC1918 network.");
 }
 return {
  site:plan.site, addresses_confirmed:false, isolated_lab_confirmed:false,
  lab_cidr:plan.labCidr, relay_cidr:plan.relayCidr, management_cidr:plan.managementCidr,
  target_ip:plan.target, pico_ip:plan.pico,
  protected_home_cidrs:plan.homeCidr?[plan.homeCidr]:[], protected_external_cidrs:[],
  relay_internet_https:false,
  pico:{enable_network:false,ssid:null,wifi_password:null,country:"XX"}
 };
}
