(function(){
"use strict";

var COLORS=["#ff6174","#58c7ff","#78a5ff","#42df9c","#ffd34f","#9a65ff","#56e1d0","#ff8bc7","#b8e35d","#7bb6ff"];
var S={
  dashboard:null,incidents:[],system:null,groups:[],realtime:null,events:[],
  historyExt:[],historyDom:[],streamMinutes:60,detailId:null,diagId:null,
  faultId:null,view:"overview",poll:null,streamMeta:null,authRequired:false,
  owner:true,mapScale:1,metaCache:{},catalog:null,catalogSelected:{},customCatalogMatch:null,customAutoCatalogKey:null,
  dashboardPrefs:null
};

var DASHBOARD_PREFS_KEY="netweather_dashboard_v1";
var DASHBOARD_PANEL_LABELS={
  global_kpi:"Глобальная доступность",
  domestic_kpi:"Российский контур",
  personal_kpi:"Моя сеть",
  incidents_kpi:"Активные инциденты",
  realtime:"График доступности",
  events:"Последние события",
  pinned_resources:"Закреплённые ресурсы",
  map:"Карта сбоев",
  resources_table:"Таблица ресурсов",
  fault_domain:"Трассировка / fault domain"
};
var DASHBOARD_PANEL_ORDER=["global_kpi","domestic_kpi","personal_kpi","incidents_kpi","realtime","events","pinned_resources","map","resources_table","fault_domain"];

function defaultDashboardPreferences(){
  return{
    pinned_resource_ids:[],
    panels:{
      global_kpi:true,domestic_kpi:true,personal_kpi:true,incidents_kpi:true,
      realtime:true,events:true,pinned_resources:true,map:true,resources_table:true,fault_domain:true
    }
  }
}
function loadDashboardPreferences(){
  if(S.dashboardPrefs)return S.dashboardPrefs;
  var base=defaultDashboardPreferences();
  try{
    var raw=JSON.parse(localStorage.getItem(DASHBOARD_PREFS_KEY)||"null");
    if(raw&&typeof raw==="object"){
      if(Array.isArray(raw.pinned_resource_ids))base.pinned_resource_ids=raw.pinned_resource_ids.map(Number).filter(Number.isFinite).slice(0,6);
      if(raw.panels&&typeof raw.panels==="object")Object.keys(base.panels).forEach(function(k){if(typeof raw.panels[k]==="boolean")base.panels[k]=raw.panels[k]})
    }
  }catch(_e){}
  S.dashboardPrefs=base;
  return base
}
function saveDashboardPreferences(prefs){
  S.dashboardPrefs=prefs;
  localStorage.setItem(DASHBOARD_PREFS_KEY,JSON.stringify(prefs))
}
function dashboardCapabilities(){
  var resources=S.dashboard&&S.dashboard.resources||[],probes=S.dashboard&&S.dashboard.probes||[];
  var hasDomestic=probes.some(function(p){return p.scope==="DOMESTIC"&&p.online});
  var hasPersonal=probes.some(function(p){return ["PERSONAL","BROWSER","DEVICE","LOCAL"].indexOf(String(p.scope||"").toUpperCase())>=0&&p.online});
  var hasMap=probes.some(function(p){return Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))});
  var hasRealtime=!!(S.realtime&&S.realtime.resources&&S.realtime.resources.length);
  return{
    global_kpi:true,
    domestic_kpi:hasDomestic,
    personal_kpi:hasPersonal,
    incidents_kpi:true,
    realtime:hasRealtime,
    events:true,
    pinned_resources:resources.length>0,
    map:hasMap,
    resources_table:resources.length>0,
    fault_domain:resources.length>0
  }
}
function visiblePinnedResourceIds(){
  var resources=S.dashboard&&S.dashboard.resources||[],valid=new Set(resources.map(function(r){return Number(r.id)})),prefs=loadDashboardPreferences();
  var chosen=(prefs.pinned_resource_ids||[]).filter(function(id){return valid.has(Number(id))}).slice(0,6);
  if(!chosen.length)chosen=resources.slice(0,6).map(function(r){return Number(r.id)});
  return chosen
}
function applyDashboardPreferences(){
  if(!S.dashboard)return;
  var prefs=loadDashboardPreferences(),caps=dashboardCapabilities();
  qa("[data-dashboard-panel]").forEach(function(node){
    var key=node.dataset.dashboardPanel;
    var visible=!!caps[key]&&prefs.panels[key]!==false;
    node.classList.toggle("dashboard-hidden",!visible)
  });
  var kpis=qa(".kpi-grid > [data-dashboard-panel]").filter(function(n){return !n.classList.contains("dashboard-hidden")});
  q(".kpi-grid").classList.toggle("dashboard-row-hidden",kpis.length===0);
  q(".kpi-grid").style.gridTemplateColumns=kpis.length?"repeat("+kpis.length+",minmax(0,1fr))":"1fr";
  [[".overview-row-chart"],[".overview-row-middle"],[".overview-row-bottom"]].forEach(function(entry){
    var row=q(entry[0]);if(!row)return;
    var visible=Array.from(row.children).filter(function(n){return !n.classList.contains("dashboard-hidden")});
    row.classList.toggle("dashboard-row-hidden",visible.length===0);
    row.classList.toggle("single-panel",visible.length===1)
  });
  var grid=q(".overview-grid"),tracks=[];
  if(!q(".headline-row").classList.contains("dashboard-hidden"))tracks.push("55px");
  if(kpis.length)tracks.push("82px");
  if(!q(".overview-row-chart").classList.contains("dashboard-row-hidden"))tracks.push("minmax(0,1.1fr)");
  if(!q(".overview-row-middle").classList.contains("dashboard-row-hidden"))tracks.push("148px");
  if(!q(".overview-row-bottom").classList.contains("dashboard-row-hidden"))tracks.push("minmax(0,1fr)");
  grid.style.gridTemplateRows=tracks.join(" ");
}
function renderDashboardPreferencesModal(){
  if(!S.dashboard)return;
  var prefs=loadDashboardPreferences(),caps=dashboardCapabilities(),resources=S.dashboard.resources||[];
  var selected=new Set(visiblePinnedResourceIds());
  q("#pinnedResourceCount").textContent=selected.size+" / 6";
  var grouped=S.groups.map(function(g){
    var rows=resources.filter(function(r){return r.group_name===g.id});
    if(!rows.length)return "";
    return '<details class="preferences-resource-group" open><summary><span><i style="background:'+esc(g.color||"#55C7FF")+'"></i><b>'+esc(g.title)+'</b></span><em>'+rows.length+'</em></summary><div class="preferences-resource-list">'+rows.map(function(r){
      var checked=selected.has(Number(r.id));
      return '<label class="preferences-resource-row"><input type="checkbox" data-pin-resource="'+r.id+'" '+(checked?"checked":"")+'><span class="preferences-checkbox"></span>'+resourceIconHtml(r.target,r.name)+'<span><b>'+esc(r.name)+'</b><small>'+esc(r.target.replace(/^https?:\/\//,""))+'</small></span></label>'
    }).join("")+'</div></details>'
  }).join("");
  q("#pinnedResourceGroups").innerHTML=grouped||empty("Нет ресурсов","Сначала добавьте ресурсы в мониторинг.");
  q("#dashboardPanelChoices").innerHTML=DASHBOARD_PANEL_ORDER.filter(function(key){return caps[key]}).map(function(key){
    var checked=prefs.panels[key]!==false;
    return '<label class="dashboard-panel-choice"><input type="checkbox" data-dashboard-choice="'+key+'" '+(checked?"checked":"")+'><span class="preferences-checkbox"></span><b>'+esc(DASHBOARD_PANEL_LABELS[key])+'</b></label>'
  }).join("");
  qa("[data-pin-resource]").forEach(function(box){box.onchange=function(){
    var checked=qa("[data-pin-resource]:checked");
    if(checked.length>6){box.checked=false;toast("На главном экране можно закрепить максимум 6 ресурсов")}
    q("#pinnedResourceCount").textContent=qa("[data-pin-resource]:checked").length+" / 6"
  }});
  hydrateResourceIcons()
}
function openDashboardPreferences(){
  renderDashboardPreferencesModal();
  q("#dashboardPreferencesDialog").showModal()
}
function submitDashboardPreferences(e){
  e.preventDefault();
  var prefs=loadDashboardPreferences();
  prefs.pinned_resource_ids=qa("[data-pin-resource]:checked").map(function(x){return Number(x.dataset.pinResource)}).slice(0,6);
  DASHBOARD_PANEL_ORDER.forEach(function(key){
    var box=q('[data-dashboard-choice="'+key+'"]');
    if(box)prefs.panels[key]=box.checked
  });
  saveDashboardPreferences(prefs);
  q("#dashboardPreferencesDialog").close();
  renderOverview();
  toast("Главный экран обновлён")
}
function resetDashboardPreferences(){
  localStorage.removeItem(DASHBOARD_PREFS_KEY);S.dashboardPrefs=defaultDashboardPreferences();
  renderDashboardPreferencesModal();renderOverview();toast("Настройки Overview сброшены")
}

function q(s){return document.querySelector(s)}
function qa(s){return Array.prototype.slice.call(document.querySelectorAll(s))}
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"})[c]})}
function token(){return localStorage.getItem("netweather_token")||""}
function auth(){return token()?{"Authorization":"Bearer "+token()}:{}}
function toast(m){var e=q("#toast");if(!e)return;e.textContent=m;e.classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(function(){e.classList.remove("show")},3000)}
function fmt(ts){if(!ts)return "—";return new Date(ts*1000).toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"})}
function shortTime(ts){if(!ts)return "—";return new Date(ts*1000).toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"})}
function ago(ts){if(!ts)return "—";var d=Math.max(0,Math.floor(Date.now()/1000-ts));if(d<60)return d+" сек назад";if(d<3600)return Math.floor(d/60)+" мин назад";if(d<86400)return Math.floor(d/3600)+" ч назад";return Math.floor(d/86400)+" дн назад"}
function duration(sec){sec=Number(sec||0);if(sec<60)return sec+" сек";if(sec<3600)return Math.floor(sec/60)+" мин";if(sec<86400)return Math.floor(sec/3600)+" ч";return Math.floor(sec/86400)+" дн"}
function pct(v,digits){if(v==null||!Number.isFinite(Number(v)))return "—";return Number(v).toFixed(digits==null?(Number(v)%1?1:0):digits)+"%"}
function num(v,suffix){return v==null||!Number.isFinite(Number(v))?"—":Math.round(Number(v))+(suffix||"")}
function stText(s){return({OK:"Доступен",DNS_ERROR:"DNS ошибка",TCP_ERROR:"TCP ошибка",TLS_ERROR:"TLS ошибка",HTTP_ERROR:"HTTP ошибка",TIMEOUT:"Таймаут",BLOCKED_TARGET:"Заблокировано",UNKNOWN_ERROR:"Ошибка"})[s]||"Нет данных"}
function stClass(s){return s==="OK"?"ok":s==="TIMEOUT"?"warn":s?"bad":"neutral"}
function diagText(d){return({AVAILABLE:"Доступен",LIKELY_RESTRICTION:"Вероятное ограничение",LIKELY_OUTAGE:"Вероятное падение",EXTERNAL_PATH_ISSUE:"Проблема пути VPS",DOMESTIC_UNKNOWN:"Нет данных РФ",INSUFFICIENT_DATA:"Недостаточно данных"})[d]||"Нет данных"}
function diagClass(d){return d==="AVAILABLE"?"ok":d==="LIKELY_RESTRICTION"||d==="LIKELY_OUTAGE"?"bad":d==="EXTERNAL_PATH_ISSUE"?"warn":"neutral"}
function groupTitle(v){var found=S.groups.find(function(g){return g.id===v});return found?found.title:({"RUSSIAN":"Российские","INTERNATIONAL":"Международные","MESSENGERS":"Мессенджеры и соцсети","INFRASTRUCTURE":"Инфраструктура","CUSTOM":"Пользовательские"})[v]||v}
function resourceById(id){return(S.dashboard&&S.dashboard.resources||[]).find(function(r){return r.id===Number(id)})}
function targetUrl(value){
  var raw=String(value||"").trim();if(!raw)return null;
  try{return new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)?raw:"https://"+raw)}catch(_e){return null}
}
function targetMeta(value){
  var u=targetUrl(value);if(!u)return{name:"",host:"",favicon:"",known:false};
  var host=u.hostname.toLowerCase().replace(/^www\./,"");
  var known=[
    [/^(youtube\.com|youtu\.be)$/,"YouTube"],[/^(telegram\.org|t\.me)$/,"Telegram"],
    [/^github\.com$/,"GitHub"],[/^(cloudflare\.com|1\.1\.1\.1)$/,"Cloudflare"],
    [/^google\./,"Google"],[/^mail\.ru$/,"Mail.ru"],[/^vk\.com$/,"VK"],
    [/^wikipedia\.org$/,"Wikipedia"],[/^yandex\./,"Яндекс"],[/^whatsapp\.com$/,"WhatsApp"],
    [/^openai\.com$/,"OpenAI"],[/^netweather\.online$/,"NetWeather"],[/^apple\.com$/,"Apple"],
    [/^microsoft\.com$/,"Microsoft"],[/^discord\.com$/,"Discord"],[/^4pda\./i,"4PDA"]
  ];
  var name="",isKnown=false;
  for(var i=0;i<known.length;i++){if(known[i][0].test(host)){name=known[i][1];isKnown=true;break}}
  if(!name){var part=host.split(".")[0]||host;name=part.replace(/[-_]+/g," ").replace(/\b\w/g,function(c){return c.toUpperCase()})}
  var isLocal=host==="localhost"||/^127\./.test(host)||/^10\./.test(host)||/^192\.168\./.test(host)||/^172\.(1[6-9]|2\d|3[01])\./.test(host)||/^\[?::1\]?$/.test(host);
  return{name:name,host:host,favicon:isLocal?"":u.protocol+"//"+u.host+"/favicon.ico",known:isKnown}
}
function getTargetMetadata(value){
  var local=targetMeta(value),u=targetUrl(value);
  if(!u||!local.host)return Promise.resolve({name:local.name,host:local.host,favicon_url:local.favicon});
  var key=u.href;
  if(!S.metaCache[key]){
    S.metaCache[key]=api("/api/target-meta?target="+encodeURIComponent(value)).then(function(remote){
      return{name:local.known?local.name:(remote.name||local.name),host:remote.host||local.host,favicon_url:remote.favicon_url||local.favicon}
    }).catch(function(){return{name:local.name,host:local.host,favicon_url:local.favicon}})
  }
  return S.metaCache[key]
}
function brandIconMarkup(target,name){
  var text=String(name||"").toLowerCase(),host=(targetMeta(target).host||"").toLowerCase();
  if(text.indexOf("youtube")>=0||host.indexOf("youtube.")>=0||host==="youtu.be")
    return '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="2" y="7" width="28" height="18" rx="6" fill="#ff2738"/><path d="M13 11.5l8 4.5-8 4.5z" fill="#fff"/></svg>';
  if(text.indexOf("telegram")>=0||host.indexOf("telegram.")>=0||host==="t.me")
    return '<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="14" fill="#35aee2"/><path d="M8.5 15.4l14-5.4-2.4 12.2c-.2 1-1 1.2-1.8.7l-3.7-2.7-1.8 1.7c-.2.2-.4.4-.8.4l.3-3.8 7-6.3c.3-.3-.1-.5-.5-.2l-8.6 5.4-3.7-1.2c-.8-.3-.8-.8.1-1.1z" fill="#fff"/></svg>';
  if(text.indexOf("github")>=0||host==="github.com")
    return '<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="14" fill="#f4f7fb"/><path fill="#111827" d="M16 6.3a9.9 9.9 0 00-3.1 19.3c.5.1.7-.2.7-.5v-1.9c-2.8.6-3.4-1.2-3.4-1.2-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.6 1.1 1.6 1.1.9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.7-1.3-2.2-.3-4.6-1.1-4.6-4.9 0-1.1.4-2 1.1-2.7-.1-.3-.5-1.3.1-2.7 0 0 .9-.3 2.8 1a9.8 9.8 0 015.1 0c1.9-1.3 2.8-1 2.8-1 .6 1.4.2 2.4.1 2.7.7.8 1.1 1.7 1.1 2.7 0 3.8-2.3 4.6-4.6 4.9.4.3.7.9.7 1.8v2.7c0 .3.2.6.7.5A9.9 9.9 0 0016 6.3z"/></svg>';
  if(text.indexOf("cloudflare")>=0||host.indexOf("cloudflare.")>=0)
    return '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="#f48120" d="M10.2 22.7h14.9a4.5 4.5 0 00.5-8.9 7.6 7.6 0 00-14.4-1.9 5.5 5.5 0 00-6.6 5.4 5.4 5.4 0 005.6 5.4z"/><path fill="#faae40" d="M18.2 22.7h9.4a3.3 3.3 0 00.4-6.6 5.7 5.7 0 00-9.8 6.6z"/></svg>';
  if(text.indexOf("whatsapp")>=0||host.indexOf("whatsapp.")>=0)
    return '<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="14" fill="#25d366"/><path fill="#fff" d="M23.3 8.7A10.3 10.3 0 007 21.1l-1.4 5.1 5.2-1.4a10.3 10.3 0 0012.5-16.1zm-7.2 15.4c-1.6 0-3.2-.4-4.5-1.2l-.3-.2-3.1.8.8-3-.2-.3a8.3 8.3 0 1114.9-5 8.3 8.3 0 01-7.6 8.9zm4.6-6.2c-.2-.1-1.5-.8-1.7-.8-.2-.1-.4-.1-.6.1-.2.3-.7.9-.9 1-.1.2-.3.2-.6.1-2.1-1-3.5-3-3.6-3.2-.2-.3 0-.4.1-.6l.4-.5c.1-.2.2-.3.2-.5s0-.4-.1-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.4-.2.2-1 1-1 2.5s1 2.9 1.2 3.1c.1.2 2.1 3.2 5 4.4.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.6-.7 1.9-1.3.2-.7.2-1.2.2-1.3-.1-.2-.3-.3-.5-.4z"/></svg>';
  if(text.indexOf("server")>=0||text.indexOf("сервер")>=0)
    return '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 4l10 5.5v13L16 28 6 22.5v-13z" fill="#8196b5"/><path d="M16 4v24M6 9.5l10 5.5 10-5.5" fill="none" stroke="#dbe5f2" stroke-width="1.6"/></svg>';
  return ""
}
function resourceIconHtml(target,name){
  var canonical=brandIconMarkup(target,name),m=targetMeta(target),fallback=esc((name||m.name||"?").slice(0,2).toUpperCase());
  if(canonical)return '<i class="resource-glyph brand-glyph">'+canonical+'</i>';
  return '<i class="resource-glyph" data-icon-target="'+esc(target)+'" data-icon-name="'+esc(name||m.name||"")+'">'+(m.favicon?'<img class="resource-logo-img" src="'+esc(m.favicon)+'" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.querySelector(\'.resource-logo-fallback\').style.display=\'grid\'">':'')+'<span class="resource-logo-fallback"'+(m.favicon?' style="display:none"':'')+'>'+fallback+'</span></i>'
}

function paintResourceIcon(node,meta){
  if(!node||!meta)return;
  var fallback=esc((node.dataset.iconName||meta.name||"?").slice(0,2).toUpperCase()),src=meta.favicon_url||"";
  node.innerHTML=(src?'<img class="resource-logo-img" src="'+esc(src)+'" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.querySelector(\'.resource-logo-fallback\').style.display=\'grid\'">':'')+'<span class="resource-logo-fallback"'+(src?' style="display:none"':'')+'>'+fallback+'</span>'
}
function hydrateResourceIcons(){
  qa("[data-icon-target]").forEach(function(node){
    var value=node.dataset.iconTarget;if(!value)return;
    getTargetMetadata(value).then(function(meta){if(node.isConnected)paintResourceIcon(node,meta)})
  })
}
async function syncResourceIdentity(force){
  var target=q("#resourceTarget"),name=q("#resourceName"),preview=q("#resourceIdentityPreview"),hint=q("#resourceTargetHint");
  if(!target||!name||!preview)return;
  var raw=target.value,m=targetMeta(raw);
  if(!m.host){preview.innerHTML="<span>NW</span>";if(hint)hint.textContent="После ввода ссылки NetWeather предложит название и логотип ресурса.";return}
  var canFill=force||!name.value.trim()||name.dataset.autoSuggested==="1";
  if(canFill&&m.name){name.value=m.name;name.dataset.autoSuggested="1"}
  preview.innerHTML=(m.favicon?'<img src="'+esc(m.favicon)+'" alt="" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.innerHTML=\'<span>'+esc((m.name||"?").slice(0,2).toUpperCase())+'</span>\'">':'<span>'+esc((m.name||"?").slice(0,2).toUpperCase())+'</span>');
  if(hint)hint.textContent=m.host+" · определяем название и логотип…";
  var remote=await getTargetMetadata(raw);
  if(target.value!==raw)return;
  if((force||!name.value.trim()||name.dataset.autoSuggested==="1")&&remote.name){name.value=remote.name;name.dataset.autoSuggested="1"}
  var icon=remote.favicon_url||m.favicon,fallback=esc((remote.name||m.name||"?").slice(0,2).toUpperCase());
  preview.innerHTML=icon?'<img src="'+esc(icon)+'" alt="" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.innerHTML=\'<span>'+fallback+'</span>\'">':'<span>'+fallback+'</span>';
  if(hint)hint.textContent=(remote.host||m.host)+(remote.name?" · «"+remote.name+"»":"")
}

function realtimeById(id){return(S.realtime&&S.realtime.resources||[]).find(function(r){return r.id===Number(id)})}
function empty(title,text){return '<div class="empty-state"><div><b>'+esc(title)+'</b><div style="margin-top:5px">'+esc(text||"")+'</div></div></div>'}
function getCss(name){return getComputedStyle(document.documentElement).getPropertyValue(name).trim()||"#92a8c2"}

async function api(path,opt,secure){
  opt=opt||{};
  if(secure&&S.authRequired&&!S.owner&&!token()){
    var dlg=q("#tokenDialog");if(dlg)dlg.showModal();
    throw new Error("Войдите в режим владельца");
  }
  var headers={"Content-Type":"application/json"};
  Object.assign(headers,opt.headers||{});
  if(secure)Object.assign(headers,auth());
  var res=await fetch(path,Object.assign({},opt,{headers:headers}));
  if(!res.ok){
    var msg="HTTP "+res.status;
    try{var j=await res.json();msg=j.detail||msg}catch(_e){}
    throw new Error(msg)
  }
  if(res.status===204)return null;
  return res.json()
}

function openView(name){
  S.view=name;
  qa(".view").forEach(function(v){v.classList.toggle("active",v.id==="view-"+name)});
  qa(".side-item[data-view]").forEach(function(b){b.classList.toggle("active",b.dataset.view===name)});
  if(name==="history")renderHistory();
  if(name==="diagnostics")renderDiagnostics();
  if(name==="probes")renderProbes();
  if(name==="map")renderMapPage();
  document.querySelector(".content").scrollTop=0
}

function updateClock(){
  var d=new Date();
  var time=new Intl.DateTimeFormat("ru-RU",{timeZone:"Europe/Moscow",hour:"2-digit",minute:"2-digit",second:"2-digit"}).format(d);
  var date=new Intl.DateTimeFormat("ru-RU",{timeZone:"Europe/Moscow",day:"2-digit",month:"short",year:"numeric"}).format(d);
  q("#clockTime").textContent=time;
  q("#clockDate").textContent=date
}

async function loadAll(silent){
  try{
    var hours=Number(q("#historyRange")&&q("#historyRange").value||24);
    var a=await Promise.all([
      api("/api/dashboard"),
      api("/api/incidents?limit=100"),
      api("/api/system"),
      api("/api/groups"),
      api("/api/realtime?minutes="+S.streamMinutes+"&scope=EXTERNAL"),
      api("/api/events?limit=30"),
      api("/api/history?hours="+hours+"&scope=EXTERNAL"),
      api("/api/history?hours="+hours+"&scope=DOMESTIC"),
      api("/api/session")
    ]);
    S.dashboard=a[0];S.incidents=a[1];S.system=a[2];S.groups=a[3];S.realtime=a[4];S.events=a[5];S.historyExt=a[6];S.historyDom=a[7];
    S.authRequired=!!a[8].auth_required;S.owner=!S.authRequired||!!a[8].authenticated;
    renderAll();setCoreOnline(true)
  }catch(e){
    setCoreOnline(false);
    if(!silent)toast("Ошибка загрузки: "+e.message)
  }
}

function setCoreOnline(ok){
  q("#apiStatus").textContent=ok?"онлайн":"нет связи";
  var p=q(".pulse-dot");if(p)p.style.background=ok?"var(--green)":"var(--red)"
}

function historyAverage(h,key){
  if(!h||!h.length)return null;
  var vals=h.map(function(x){return Number(x[key])}).filter(function(x){return Number.isFinite(x)});
  return vals.length?vals.reduce(function(a,b){return a+b},0)/vals.length:null
}

function historyDelta(h,key){
  if(!h||h.length<4)return null;
  var mid=Math.floor(h.length/2);
  var a=historyAverage(h.slice(0,mid),key),b=historyAverage(h.slice(mid),key);
  return a==null||b==null?null:b-a
}

function renderAll(){
  renderOverview();
  renderGroups();
  renderResources();
  renderIncidents();
  renderDiagnostics();
  renderHistory();
  renderProbes();
  renderNotifications();
  renderSettings();
  renderSearch("");
  if(S.system)q("#versionLabel").textContent=S.system.version
}

function renderOverview(){
  if(!S.dashboard)return;
  var summary=S.dashboard.summary||{},legacy=S.dashboard.legacy_summary||{};
  var globalAvail=historyAverage(S.historyExt,"availability"),ruAvail=historyAverage(S.historyDom,"availability");
  var globalDelta=historyDelta(S.historyExt,"availability"),ruDelta=historyDelta(S.historyDom,"availability");
  var active=S.incidents.filter(function(i){return !i.closed_at});
  var unread=active.filter(function(i){return !i.acknowledged_at});

  q("#kpiGlobal").textContent=pct(globalAvail,2);
  q("#kpiGlobalDelta").textContent=globalDelta==null?"внешний VPS":((globalDelta>=0?"▲ +":"▼ ")+Math.abs(globalDelta).toFixed(2)+"%");
  q("#kpiGlobalDelta").style.color=globalDelta==null?"var(--muted)":globalDelta>=0?"var(--green)":"var(--red)";
  q("#kpiGlobalHint").textContent=globalAvail==null?"нет истории":"среднее за выбранный период";

  q("#kpiRu").textContent=pct(ruAvail,2);
  q("#kpiRuDelta").textContent=summary.domestic_probe_online?(ruDelta==null?"живые данные":((ruDelta>=0?"▲ +":"▼ ")+Math.abs(ruDelta).toFixed(2)+"%")):"нет probe";
  q("#kpiRuDelta").style.color=summary.domestic_probe_online?(ruDelta!=null&&ruDelta<0?"var(--red)":"var(--green)"):"var(--muted)";
  q("#kpiRuHint").textContent=summary.domestic_probe_online?"российский контур подключён":"российский probe не подключён";

  q("#kpiPersonal").textContent="—";
  q("#kpiPersonalHint").textContent="device-probe ещё не подключён";
  q("#kpiIncidents").textContent=active.length;
  q("#kpiIncidentDelta").textContent=unread.length?unread.length+" новых":"спокойно";
  q("#kpiIncidentDelta").style.color=unread.length?"var(--red)":"var(--muted)";
  q("#kpiIncidentHint").textContent=active.length?(unread.length+" непрочитанных из "+active.length):"критических событий нет";

  drawSpark(q("#kpiGlobalSpark"),S.historyExt.map(function(x){return x.availability}),COLORS[1]);
  drawSpark(q("#kpiRuSpark"),S.historyDom.map(function(x){return x.availability}),COLORS[0]);
  drawSpark(q("#kpiPersonalSpark"),[],COLORS[3]);
  drawBars(q("#kpiIncidentSpark"),incidentSpark(),COLORS[0]);

  var state=overviewState(summary,legacy,active.length);
  q("#welcomeTitle").textContent=state.title;q("#welcomeSubtitle").textContent=state.text;
  var health=q("#topSystemStatus");health.className="health-pill "+state.cls;health.querySelector("b").textContent=state.short;health.querySelector("span").textContent=state.healthText;

  q("#alertBadge").textContent=unread.length;q("#alertBadge").classList.toggle("hidden",!unread.length);
  q("#notifyCount").textContent=unread.length;q("#notifyCount").classList.toggle("hidden",!unread.length);

  renderRealtime();renderEvents();renderResourceCards();renderMap();renderOverviewTable();renderFaultPanel();applyDashboardPreferences()
}

function overviewState(s,legacy,incidents){
  if(s.mode==="RESTRICTIONS_DETECTED")return{title:"Есть сетевые ограничения",text:"Есть расхождения между внешней доступностью и российским контуром.",short:"Требуется внимание",healthText:"обнаружены расхождения",cls:"warn"};
  if(s.mode==="OUTAGES_DETECTED")return{title:"Есть недоступные ресурсы",text:"Часть ресурсов недоступна сразу из нескольких точек.",short:"Есть сбои",healthText:"проверьте инциденты",cls:"bad"};
  if(incidents)return{title:"Связь требует внимания",text:"Есть активные инциденты, требующие проверки.",short:"Есть инциденты",healthText:"не все сервисы стабильны",cls:"warn"};
  if(s.mode==="NO_DOMESTIC_PROBE")return{title:"Хорошая связь сегодня",text:"Глобальный мониторинг работает. Российский контур пока не подключён.",short:"Частичные данные",healthText:"глобальный контур работает",cls:"warn"};
  if(legacy.available)return{title:"Хорошая связь сегодня",text:"Мониторим доступность интернет-ресурсов по всему миру. В реальном времени. Для вас.",short:"Система в порядке",healthText:"Все основные сервисы работают",cls:""};
  return{title:"Собираем измерения",text:"NetWeather ждёт первые результаты мониторинга.",short:"Инициализация",healthText:"получаем первые данные",cls:"warn"}
}

function incidentSpark(){
  var now=Math.floor(Date.now()/1000),b=new Array(12).fill(0);
  S.incidents.forEach(function(i){var t=i.opened_at||0,d=Math.floor((now-t)/7200);if(d>=0&&d<12)b[11-d]++});
  return b
}

function renderRealtime(){
  var data=S.realtime&&S.realtime.resources||[];
  var withPoints=data.filter(function(r){return r.points&&r.points.some(function(p){return p.availability!=null})});
  q("#streamEmpty").classList.toggle("hidden",!!withPoints.length);
  drawAvailabilityChart(q("#streamChart"),withPoints);
  q("#streamLegend").innerHTML=withPoints.slice(0,7).map(function(r,i){return '<span class="legend-item"><i class="legend-dot" style="background:'+COLORS[i%COLORS.length]+'"></i>'+esc(r.name)+'</span>'}).join("")
}

function availabilityY(value,top,bottom){
  var v=Math.max(0,Math.min(100,Number(value))),ticks=[100,99,98,95,90];
  if(v>=100)return top;
  if(v<=90)return bottom;
  for(var i=0;i<ticks.length-1;i++){
    var hi=ticks[i],lo=ticks[i+1];
    if(v<=hi&&v>=lo){
      var band=(bottom-top)/(ticks.length-1),ratio=(hi-v)/(hi-lo);
      return top+(i+ratio)*band
    }
  }
  return bottom
}
function drawAvailabilityChart(canvas,series){
  if(!canvas)return;
  var rect=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1);
  canvas.width=Math.max(480,Math.floor(rect.width*dpr));canvas.height=Math.max(190,Math.floor(rect.height*dpr));
  var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);
  var w=rect.width,h=rect.height,p={l:54,r:12,t:13,b:29};ctx.clearRect(0,0,w,h);
  if(!series.length){S.streamMeta=null;return}
  var allTs=[];series.forEach(function(row){row.points.forEach(function(x){if(x.availability!=null)allTs.push(x.timestamp)})});
  if(!allTs.length){S.streamMeta=null;return}
  var ticks=[100,99,98,95,90],plotBottom=h-p.b;
  ctx.font='600 11px "Inter","Segoe UI",system-ui,sans-serif';
  ctx.textBaseline="middle";ctx.fillStyle=getCss("--muted");ctx.strokeStyle=getCss("--line-soft");ctx.lineWidth=1;
  ticks.forEach(function(v,i){
    var y=p.t+(plotBottom-p.t)*i/(ticks.length-1);
    ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();
    ctx.fillText(v+"%",5,y)
  });
  var tmin=Math.min.apply(null,allTs),tmax=Math.max.apply(null,allTs);if(tmax===tmin)tmax=tmin+1;
  series.slice(0,7).forEach(function(row,si){
    ctx.strokeStyle=COLORS[si%COLORS.length];ctx.lineWidth=1.75;ctx.lineJoin="round";ctx.lineCap="round";ctx.beginPath();
    var started=false;
    row.points.forEach(function(pt){
      if(pt.availability==null)return;
      var x=p.l+(w-p.l-p.r)*(pt.timestamp-tmin)/(tmax-tmin),y=availabilityY(pt.availability,p.t,plotBottom);
      if(!started){ctx.moveTo(x,y);started=true}else ctx.lineTo(x,y)
    });ctx.stroke()
  });
  ctx.font='500 10px "Inter","Segoe UI",system-ui,sans-serif';ctx.textBaseline="alphabetic";
  for(var j=0;j<=6;j++){
    var ts=tmin+(tmax-tmin)*j/6,x=p.l+(w-p.l-p.r)*j/6;
    ctx.fillStyle=getCss("--muted");ctx.fillText(shortTime(ts),Math.max(p.l-2,Math.min(x,w-42)),h-7)
  }
  S.streamMeta={series:series,tmin:tmin,tmax:tmax,min:90,max:100,p:p,w:w,h:h,key:"availability"}
}

function handleChartMove(e){
  var m=S.streamMeta;if(!m)return;
  var r=q("#streamChart").getBoundingClientRect(),x=e.clientX-r.left,ratio=Math.max(0,Math.min(1,(x-m.p.l)/(m.w-m.p.l-m.p.r))),ts=m.tmin+(m.tmax-m.tmin)*ratio;
  var rows=[];
  m.series.slice(0,7).forEach(function(s,si){
    if(!s.points.length)return;
    var pt=s.points.reduce(function(best,p){return Math.abs(p.timestamp-ts)<Math.abs(best.timestamp-ts)?p:best},s.points[0]);
    if(pt.availability!=null)rows.push({name:s.name,value:pt.availability,color:COLORS[si%COLORS.length],time:pt.timestamp})
  });
  if(!rows.length)return;
  var tip=q("#chartTooltip");tip.innerHTML='<b>'+new Date(rows[0].time*1000).toLocaleString("ru-RU",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"})+'</b>'+rows.map(function(x){return '<span><i class="legend-dot" style="background:'+x.color+'"></i><em>'+esc(x.name)+'</em><strong>'+pct(x.value,1)+'</strong></span>'}).join("");
  tip.classList.remove("hidden")
}

function renderEvents(){
  var el=q("#eventFeed"),rows=S.events||[];
  if(!rows.length){el.innerHTML=empty("Событий пока нет","Изменения состояния появятся здесь.");return}
  el.innerHTML=rows.slice(0,7).map(function(ev){
    var sev=ev.severity==="critical"?"critical":ev.severity==="warning"?"warning":"",label=sev==="critical"?"Критический":sev==="warning"?"Предупреждение":"Информация";
    var unread=ev.incident_id&&!ev.acknowledged_at;
    return '<div class="event-item '+(unread?"unread":"")+'" data-event-resource="'+(ev.resource_id||"")+'"><time class="event-time">'+shortTime(ev.time)+'</time><i class="event-dot '+sev+'"></i><div class="event-main"><b>'+esc(ev.title)+'</b><span>'+esc(ev.message||"")+'</span>'+(unread?'<button class="event-ack" data-ack="'+ev.incident_id+'">✓ Отметить прочитанным</button>':'')+'</div><span class="event-tag '+sev+'">'+label+'</span></div>'
  }).join("");
  qa("[data-event-resource]").forEach(function(row){row.onclick=function(e){if(e.target.closest("[data-ack]"))return;if(row.dataset.eventResource)openDetail(Number(row.dataset.eventResource))}});
  bindIncidentActions()
}

function renderResourceCards(){
  var el=q("#resourceCards"),rows=S.realtime&&S.realtime.resources||[];
  if(!rows.length){el.innerHTML=empty("Нет ресурсов","Добавьте первую цель.");return}
  var current=S.dashboard.resources||[],pinned=visiblePinnedResourceIds();
  var cards=pinned.map(function(id){return rows.find(function(r){return Number(r.id)===Number(id)})}).filter(Boolean).slice(0,6);
  el.innerHTML=cards.map(function(r,i){
    var rr=current.find(function(x){return x.id===r.id})||{},cls=diagClass(rr.diagnosis);
    var pts=(r.points||[]).filter(function(p){return p.availability!=null});
    var latency=(rr.domestic||rr.external||{}).response_time_ms;
    var delta=pts.length>2?Number(pts[pts.length-1].availability)-Number(pts[0].availability):0;
    return '<article class="resource-card" data-resource="'+r.id+'"><div class="resource-card-top"><div class="resource-card-name">'+resourceIconHtml(r.target,r.name)+'<b>'+esc(r.name)+'</b></div><span class="resource-state '+(cls==="bad"?"bad":cls==="warn"?"warn":"")+'">'+(delta>=0?"↑ ":"↓ ")+Math.abs(delta).toFixed(1)+'%</span></div><div class="resource-card-metrics"><strong>'+pct(r.availability_24h,1)+'</strong><span>'+num(latency," мс")+'</span></div><canvas data-card-spark="'+r.id+'"></canvas><div class="resource-card-foot"><span>◴ '+num(latency," мс")+'</span><span>'+esc(groupTitle(r.group_name))+'</span></div></article>'
  }).join("");
  qa(".resource-card").forEach(function(card){card.onclick=function(){openDetail(Number(card.dataset.resource))}});
  cards.forEach(function(r,i){var c=document.querySelector('[data-card-spark="'+r.id+'"]');drawSpark(c,(r.points||[]).map(function(p){return p.availability}).filter(function(v){return v!=null}),COLORS[i%COLORS.length])});
  hydrateResourceIcons()
}

function renderMap(){
  var probes=S.dashboard&&S.dashboard.probes||[];
  var map=q("#mapPoints"),emptyEl=q("#mapEmpty");
  if(map)map.innerHTML="";
  var located=probes.filter(function(p){return Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))});
  if(emptyEl)emptyEl.classList.toggle("hidden",!!located.length);
  if(!map||!located.length)return;
  located.forEach(function(p){
    var x=(Number(p.lon)+180)/360*760,y=(90-Number(p.lat))/180*320;
    var circle=document.createElementNS("http://www.w3.org/2000/svg","circle");
    circle.setAttribute("cx",x);circle.setAttribute("cy",y);circle.setAttribute("r",p.online?"5":"4");
    circle.setAttribute("fill",p.online?"#42df9c":"#ff6174");circle.setAttribute("class","map-point");
    map.appendChild(circle)
  })
}

function renderMapPage(){
  renderProbeLegend()
}

function renderProbeLegend(){
  var el=q("#probeMapLegend");if(!el||!S.dashboard)return;
  var probes=S.dashboard.probes||[];
  el.innerHTML=probes.length?probes.map(function(p){return '<div class="probe-map-item '+(p.online?"":"offline")+'"><i></i><div><b>'+esc(p.name)+'</b><span>'+esc(p.scope)+' · '+(p.online?"онлайн":"нет связи")+' · '+ago(p.last_seen_at)+'</span></div></div>'}).join(""):empty("Нет точек наблюдения","")
}

function renderOverviewTable(){
  var rows=S.dashboard.resources||[],el=q("#overviewResourceTable");
  if(!rows.length){el.innerHTML=empty("Нет ресурсов","Добавьте первую цель.");return}
  var visible=rows;
  el.innerHTML='<div class="table-head"><div>Ресурс</div><div>Статус</div><div>Доступность (24ч)</div><div>Время ответа</div><div>DNS</div><div>TCP</div><div>TLS</div><div>HTTP</div><div>Тренд (1ч)</div><div></div></div>'+visible.map(function(r){
    var rt=realtimeById(r.id)||{},x=r.domestic||r.external||{};
    return '<div class="table-row" data-resource="'+r.id+'"><div class="table-resource with-logo">'+resourceIconHtml(r.target,r.name)+'<div><b>'+esc(r.name)+'</b><span>'+esc(r.target)+'</span></div></div><div><span class="status-chip '+diagClass(r.diagnosis)+'">'+diagText(r.diagnosis)+'</span></div><div>'+pct(rt.availability_24h,1)+'</div><div>'+num(x.response_time_ms," мс")+'</div><div><i class="stage-dot '+stageState("DNS",r,x)+'"></i></div><div><i class="stage-dot '+stageState("TCP",r,x)+'"></i></div><div><i class="stage-dot '+stageState("TLS",r,x)+'"></i></div><div><i class="stage-dot '+stageState("HTTP",r,x)+'"></i></div><div><canvas class="trend-canvas" data-trend="'+r.id+'"></canvas></div><button class="row-more">⋮</button></div>'
  }).join("");
  qa("#overviewResourceTable .table-row").forEach(function(row){row.onclick=function(){openDetail(Number(row.dataset.resource))}});
  visible.forEach(function(r,i){var rt=realtimeById(r.id)||{},c=document.querySelector('[data-trend="'+r.id+'"]');drawSpark(c,(rt.points||[]).map(function(p){return p.availability}).filter(function(v){return v!=null}),COLORS[i%COLORS.length])});
  hydrateResourceIcons()
}

function stageState(stage,r,x){
  if(stage==="DNS")return x.dns_ms!=null?"ok":x.status==="DNS_ERROR"?"bad":"neutral";
  if(stage==="TCP")return x.tcp_ms!=null?"ok":x.status==="TCP_ERROR"?"bad":"neutral";
  if(stage==="TLS")return r.target.indexOf("https://")!==0?"ok":x.tls_ms!=null?"ok":x.status==="TLS_ERROR"?"bad":"neutral";
  if(stage==="HTTP")return x.status==="OK"?"ok":x.http_status!=null?"warn":x.status?"bad":"neutral";
  return "neutral"
}

function renderFaultPanel(){
  var rows=S.dashboard.resources||[],sel=q("#faultResourceSelect"),old=String(S.faultId||sel.value||"");
  sel.innerHTML=rows.map(function(r){return '<option value="'+r.id+'">'+esc(r.name)+'</option>'}).join("");
  if(old&&rows.some(function(r){return String(r.id)===old}))sel.value=old;else if(rows.length){sel.value=String(rows[0].id);S.faultId=rows[0].id}
  var r=resourceById(sel.value);if(!r){q("#faultPath").innerHTML="";return}
  S.faultId=r.id;
  var ext=r.external||{},dom=r.domestic||{};
  var nodes=[
    {name:"Ваше устройство",value:"device-probe",icon:"▣",state:"neutral"},
    {name:"Оператор",value:dom.response_time_ms!=null?num(dom.response_time_ms," мс"):"нет данных",icon:"✣",state:dom.status?stClass(dom.status):"neutral"},
    {name:"Транзит (RTT)",value:ext.tcp_ms!=null?num(ext.tcp_ms," мс"):"—",icon:"△",state:r.diagnosis==="LIKELY_RESTRICTION"?"bad":r.diagnosis==="EXTERNAL_PATH_ISSUE"?"warn":ext.status==="OK"?"ok":"neutral"},
    {name:"Сервер "+r.name,value:ext.response_time_ms!=null?num(ext.response_time_ms," мс"):"—",icon:"▦",state:ext.status?stClass(ext.status):"neutral"},
    {name:"Приложение",value:ext.status==="OK"?"OK":stText(ext.status),icon:"▣",state:ext.status?stClass(ext.status):"neutral"}
  ];
  q("#faultPath").innerHTML=nodes.map(function(n){return '<div class="fault-node '+n.state+'"><div class="node-icon">'+n.icon+'</div><b>'+esc(n.name)+'</b><span>'+esc(n.value)+'</span></div>'}).join("");
  var con=q("#faultConclusion"),cls=diagClass(r.diagnosis),title=diagText(r.diagnosis);
  if(r.diagnosis==="AVAILABLE"){title="Проблем не обнаружено";cls="ok"}
  else if(r.diagnosis==="LIKELY_RESTRICTION"){title="Вероятная проблема в сетевом пути";cls="bad"}
  else if(r.diagnosis==="LIKELY_OUTAGE"){title="Вероятная проблема у ресурса или его сети";cls="bad"}
  con.className="fault-conclusion "+cls;
  con.innerHTML='<b>'+esc(title)+'</b><span>'+esc(r.diagnosis_text||"Недостаточно данных для локализации.")+'</span>'
}

function renderSearch(value){
  var el=q("#searchResults");if(!el)return;var v=(value||"").trim().toLowerCase();
  if(!v){el.classList.add("hidden");el.innerHTML="";return}
  var rows=(S.dashboard&&S.dashboard.resources||[]).filter(function(r){return r.name.toLowerCase().indexOf(v)>=0||r.target.toLowerCase().indexOf(v)>=0||String(r.resolved_ip||"").indexOf(v)>=0}).slice(0,8);
  el.innerHTML=rows.length?rows.map(function(r){return '<button class="search-result" data-search-id="'+r.id+'"><div><b>'+esc(r.name)+'</b><span>'+esc(r.target)+'</span></div><em>'+diagText(r.diagnosis)+'</em></button>'}).join(""):empty("Ничего не найдено","");
  el.classList.remove("hidden");
  qa("[data-search-id]").forEach(function(b){b.onclick=function(){el.classList.add("hidden");openDetail(Number(b.dataset.searchId))}})
}

function groupStats(key){
  var rows=(S.dashboard&&S.dashboard.resources||[]).filter(function(r){return r.group_name===key}),ok=0,bad=0;
  rows.forEach(function(r){if(r.diagnosis==="AVAILABLE")ok++;else if(r.diagnosis==="LIKELY_RESTRICTION"||r.diagnosis==="LIKELY_OUTAGE")bad++});
  return{total:rows.length,ok:ok,bad:bad}
}

function renderGroups(){
  var el=q("#groupsGrid");if(!el)return;
  var groups=S.groups.filter(function(g){return g.resource_count||g.id==="CUSTOM"});
  if(!groups.length){el.innerHTML=empty("Групп пока нет","Создайте первую группу ресурсов.");return}
  el.innerHTML=groups.map(function(g){var s=groupStats(g.id);return '<article class="group-manage-card"><div class="group-manage-head"><i style="background:'+esc(g.color||"#3A8DFF")+'"></i><div><h2>'+esc(g.title)+'</h2><span>'+esc(g.id)+'</span></div></div><div class="group-manage-stats"><div><b>'+s.total+'</b><span>ресурсов</span></div><div><b>'+s.ok+'</b><span>доступно</span></div><div><b>'+s.bad+'</b><span>проблем</span></div></div><div class="group-manage-actions"><button class="btn tiny secondary edit-group" data-group-edit="'+esc(g.id)+'">Изменить</button>'+(g.id!=="CUSTOM"?'<button class="btn tiny danger delete-group" data-group-delete="'+esc(g.id)+'">Удалить</button>':'')+'</div></article>'}).join("");
  qa(".edit-group").forEach(function(b){b.onclick=function(){openGroupForm(S.groups.find(function(g){return g.id===b.dataset.groupEdit}))}});
  qa(".delete-group").forEach(function(b){b.onclick=function(){deleteGroup(b.dataset.groupDelete)}})
}

function openGroupForm(g){
  q("#groupForm").reset();q("#groupKey").value=g?g.id:"";q("#groupDialogTitle").textContent=g?"Изменить группу":"Новая группа";q("#groupTitle").value=g?g.title:"";q("#groupColor").value=g&&g.color?g.color:"#3A8DFF";q("#groupDialog").showModal()
}
async function saveGroup(e){
  e.preventDefault();var key=q("#groupKey").value,title=q("#groupTitle").value.trim(),color=q("#groupColor").value;
  if(!title){toast("Введите название группы");return}
  try{if(key)await api("/api/groups/"+encodeURIComponent(key),{method:"PATCH",body:JSON.stringify({title:title,color:color})},true);else await api("/api/groups",{method:"POST",body:JSON.stringify({title:title,color:color})},true);q("#groupDialog").close();await loadAll(true);toast(key?"Группа обновлена":"Группа создана")}catch(err){toast(err.message)}
}
async function deleteGroup(key){
  var g=S.groups.find(function(x){return x.id===key});if(!g)return;
  if(!confirm("Удалить группу «"+g.title+"»? Ресурсы будут перенесены в «Пользовательские»."))return;
  try{await api("/api/groups/"+encodeURIComponent(key),{method:"DELETE"},true);await loadAll(true);toast("Группа удалена")}catch(err){toast(err.message)}
}

function filteredResources(){
  var rows=(S.dashboard&&S.dashboard.resources||[]).slice(),s=(q("#searchInput").value||"").toLowerCase(),g=q("#groupFilter").value,st=q("#statusFilter").value;
  return rows.filter(function(r){var ok=!s||r.name.toLowerCase().indexOf(s)>=0||r.target.toLowerCase().indexOf(s)>=0||String(r.resolved_ip||"").indexOf(s)>=0;if(g!=="ALL"&&r.group_name!==g)ok=false;if(st==="AVAILABLE"&&r.diagnosis!=="AVAILABLE")ok=false;if(st==="RESTRICTION"&&r.diagnosis!=="LIKELY_RESTRICTION")ok=false;if(st==="OUTAGE"&&r.diagnosis!=="LIKELY_OUTAGE")ok=false;if(st==="UNKNOWN"&&r.diagnosis!=="DOMESTIC_UNKNOWN"&&r.diagnosis!=="INSUFFICIENT_DATA")ok=false;return ok})
}

function renderResources(){
  if(!S.dashboard)return;
  var all=S.dashboard.resources||[],sel=q("#groupFilter"),old=sel.value||"ALL";
  var groups=S.groups.filter(function(g){return g.resource_count||g.id==="CUSTOM"});
  sel.innerHTML='<option value="ALL">Все группы</option>'+groups.map(function(g){return '<option value="'+esc(g.id)+'">'+esc(g.title)+'</option>'}).join("");
  if(Array.from(sel.options).some(function(o){return o.value===old}))sel.value=old;
  q("#groupOptions").innerHTML=S.groups.map(function(g){return '<option value="'+esc(g.id)+'">'+esc(g.title)+'</option>'}).join("");
  var rows=filteredResources(),el=q("#resourcesTable");
  if(!rows.length){el.innerHTML=empty(all.length?"Ничего не найдено":"Список пуст",all.length?"Измените фильтры.":"Добавьте ресурс.");return}
  el.innerHTML='<div class="table-head"><div>Ресурс</div><div>Вывод</div><div>VPS</div><div>РФ</div><div>DNS</div><div>HTTP</div><div>Действия</div></div>'+rows.map(function(r){var ext=r.external||{},dom=r.domestic||{};return '<div class="table-row" data-resource="'+r.id+'"><div class="table-resource"><b>'+esc(r.name)+'</b><span>'+esc(r.target)+' · '+esc(groupTitle(r.group_name))+'</span></div><div><span class="status-chip '+diagClass(r.diagnosis)+'">'+diagText(r.diagnosis)+'</span></div><div>'+stText(ext.status)+'</div><div>'+stText(dom.status)+'</div><div>'+num((dom.dns_ms!=null?dom.dns_ms:ext.dns_ms)," мс")+'</div><div>'+((dom.http_status!=null?dom.http_status:ext.http_status)||"—")+'</div><div><button class="btn tiny secondary row-check" data-check="'+r.id+'">Проверить</button></div></div>'}).join("");
  qa("#resourcesTable .table-row").forEach(function(row){row.onclick=function(e){if(e.target.closest(".row-check"))return;openDetail(Number(row.dataset.resource))}});
  qa(".row-check").forEach(function(b){b.onclick=function(e){e.stopPropagation();manualCheck(Number(b.dataset.check))}})
}

function incidentHtml(i){
  var severity=i.severity==="critical"?"critical":i.closed_at?"info":"";
  var read=!!i.acknowledged_at;
  return '<div class="incident-row '+severity+' '+(read?"read":"unread")+'" data-incident="'+i.id+'"><i></i><div><b>'+esc(i.resource_name||"Событие")+'</b><p>'+esc(i.message||"")+'</p></div><div class="incident-row-actions"><time>'+ago(i.opened_at||i.closed_at)+'</time>'+(read?'<span class="incident-read-mark">✓ Прочитано</span>':'<button class="incident-read-btn" data-ack="'+i.id+'">✓ Прочитать</button>')+'</div></div>'
}
async function acknowledgeIncident(id){
  try{await api("/api/incidents/"+id+"/ack",{method:"POST"},true);await loadAll(true);toast("Инцидент отмечен прочитанным")}catch(e){toast(e.message)}
}
async function acknowledgeAllIncidents(){
  try{var r=await api("/api/incidents/ack-all",{method:"POST"},true);await loadAll(true);toast("Отмечено прочитанными: "+r.acknowledged)}catch(e){toast(e.message)}
}
function bindIncidentActions(){
  qa("[data-ack]").forEach(function(b){b.onclick=function(e){e.stopPropagation();acknowledgeIncident(Number(b.dataset.ack))}})
}
function renderIncidents(){
  var a=S.incidents.filter(function(i){return !i.closed_at}),h=S.incidents.filter(function(i){return i.closed_at});
  q("#activeIncidents").innerHTML=a.length?a.map(incidentHtml).join(""):empty("Активных инцидентов нет","Система не видит открытых тревог.");
  q("#incidentHistory").innerHTML=h.length?h.map(incidentHtml).join(""):empty("История пуста","Закрытые события появятся здесь.");
  bindIncidentActions();
  var unread=S.incidents.filter(function(i){return !i.acknowledged_at}).length,button=q("#ackAllIncidents");
  if(button){button.disabled=!unread;button.textContent=unread?"✓ Отметить все прочитанными ("+unread+")":"✓ Всё прочитано"}
}

function renderProbes(){
  var el=q("#probesGrid");if(!el||!S.dashboard)return;
  var probes=S.dashboard.probes||[];
  el.innerHTML=probes.length?probes.map(function(p){return '<article class="probe-page-card"><h2>'+esc(p.name)+'</h2><p>'+esc(p.scope)+' · '+(p.online?"онлайн":"нет связи")+'</p><div class="probe-page-meta"><div><span>Последняя связь</span><b>'+ago(p.last_seen_at)+'</b></div><div><span>Возраст данных</span><b>'+(p.age_seconds==null?"—":duration(p.age_seconds))+'</b></div></div></article>'}).join(""):empty("Точки наблюдения не подключены","")
  renderProbeLegend()
}

function renderNotifications(){
  var b=q("#browserNotifyState"),w=q("#notifyWebhookState");if(!b||!w||!S.system)return;
  b.textContent=!window.Notification?"Браузер не поддерживает Notification API.":Notification.permission==="granted"?"Разрешение выдано.":Notification.permission==="denied"?"Уведомления заблокированы браузером.":"Разрешение ещё не запрашивалось.";
  w.textContent=S.system.webhook_configured?"Server webhook настроен.":"Webhook не настроен."
}

function renderDiagnostics(){
  if(!S.dashboard)return;var rows=S.dashboard.resources||[],sel=q("#diagResource"),old=String(S.diagId||sel.value||"");
  sel.innerHTML=rows.map(function(r){return '<option value="'+r.id+'">'+esc(r.name)+' · '+esc(r.target)+'</option>'}).join("");
  if(old&&rows.some(function(r){return String(r.id)===old}))sel.value=old;else if(rows.length){sel.value=String(rows[0].id);S.diagId=rows[0].id}
  var r=resourceById(sel.value);if(r)showDiagnostic(r)
}
function showDiagnostic(r){
  S.diagId=r.id;var ext=r.external||{},dom=r.domestic||{},x=r.domestic||r.external||{};
  q("#diagSummary").innerHTML='<div class="diag-summary-card"><div><span>Вывод</span><b>'+diagText(r.diagnosis)+'</b></div><div><span>VPS</span><b>'+stText(ext.status)+' · '+num(ext.response_time_ms," мс")+'</b></div><div><span>РФ</span><b>'+stText(dom.status)+' · '+num(dom.response_time_ms," мс")+'</b></div><div><span>IP</span><b>'+esc(x.resolved_ip||"—")+'</b></div><div><span>HTTP</span><b>'+(x.http_status||"—")+'</b></div></div>';
  setStage("Dns",x.dns_ms,x.status!=="DNS_ERROR");setStage("Tcp",x.tcp_ms,x.tcp_ms!=null);setStage("Tls",x.tls_ms,r.target.indexOf("https://")!==0||x.tls_ms!=null);setStage("Http",x.http_ms,x.status==="OK")
}
function setStage(n,v,good){var e=q("#stage"+n);e.querySelector("b").textContent=v==null?"—":Math.round(v)+" мс";e.className="diag-step "+(v==null?"":good?"good":"bad")}

function renderHistory(){
  if(!q("#historyChart"))return;
  drawSimpleChart(q("#historyChart"),S.historyExt,"availability",true);drawSimpleChart(q("#latencyChart"),S.historyExt,"avg_latency_ms",false);
  q("#historyAvailability").textContent=pct(historyAverage(S.historyExt,"availability"));q("#historyLatency").textContent=num(historyAverage(S.historyExt,"avg_latency_ms")," мс");
  q("#historyEmpty").classList.toggle("hidden",!!S.historyExt.length);q("#latencyEmpty").classList.toggle("hidden",!!S.historyExt.length);
  var rows=S.historyExt.slice(-24).reverse();q("#historyTable").innerHTML=rows.length?'<div class="history-row head"><div>Время</div><div>Доступность</div><div>Задержка</div><div>Проверок</div></div>'+rows.map(function(x){return '<div class="history-row"><div>'+fmt(x.timestamp)+'</div><b>'+pct(x.availability)+'</b><div>'+num(x.avg_latency_ms," мс")+'</div><div>'+x.checks+'</div></div>'}).join(""):empty("Нет истории","")
}

function drawSimpleChart(canvas,data,key,percent){
  if(!canvas)return;var rect=canvas.getBoundingClientRect(),dpr=Math.min(2,devicePixelRatio||1);canvas.width=Math.max(280,Math.floor(rect.width*dpr));canvas.height=Math.max(180,Math.floor(rect.height*dpr));var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);var w=rect.width,h=rect.height,p={l:38,r:10,t:12,b:24};ctx.clearRect(0,0,w,h);if(!data.length)return;var vals=data.map(function(x){return Number(x[key]||0)}),min=percent?0:Math.min.apply(null,vals),max=percent?100:Math.max.apply(null,vals);if(max===min)max=min+1;ctx.font="8px system-ui";ctx.strokeStyle=getCss("--line-soft");ctx.fillStyle=getCss("--muted");for(var i=0;i<=4;i++){var y=p.t+(h-p.t-p.b)*i/4;ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();var v=max-(max-min)*i/4;ctx.fillText(percent?Math.round(v)+"%":Math.round(v)+"",3,y+3)}ctx.strokeStyle=COLORS[1];ctx.lineWidth=1.7;ctx.beginPath();data.forEach(function(x,i){var xx=p.l+(w-p.l-p.r)*(data.length===1?.5:i/(data.length-1)),yy=p.t+(h-p.t-p.b)*(1-(Number(x[key]||0)-min)/(max-min));if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy)});ctx.stroke()
}

function drawSpark(canvas,values,color){
  if(!canvas)return;var r=canvas.getBoundingClientRect(),w=Math.max(45,r.width||70),h=Math.max(20,r.height||30),dpr=Math.min(2,devicePixelRatio||1);canvas.width=w*dpr;canvas.height=h*dpr;var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!values||values.length<2)return;var min=Math.min.apply(null,values),max=Math.max.apply(null,values);if(max===min)max=min+1;ctx.strokeStyle=color;ctx.lineWidth=1.35;ctx.beginPath();values.forEach(function(v,i){var x=i/(values.length-1)*(w-2)+1,y=h-2-(v-min)/(max-min)*(h-5);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke()
}
function drawBars(canvas,values,color){
  if(!canvas)return;var r=canvas.getBoundingClientRect(),w=Math.max(45,r.width||70),h=Math.max(20,r.height||30),dpr=Math.min(2,devicePixelRatio||1);canvas.width=w*dpr;canvas.height=h*dpr;var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!values||!values.length)return;var max=Math.max(1,Math.max.apply(null,values)),bw=w/values.length*.55;ctx.fillStyle=color;values.forEach(function(v,i){var bh=(v/max)*(h-4),x=(i+.2)*w/values.length,y=h-bh-1;ctx.fillRect(x,y,bw,bh)})
}

function renderSettings(){
  if(!S.system||!S.dashboard)return;
  q("#tokenState").textContent=S.authRequired?(S.owner?"Режим владельца активен.":"Сейчас открыт режим просмотра."):"Development mode: все действия доступны без авторизации.";
  q("#alertSystemState").textContent=S.system.webhook_configured?"Server webhook настроен.":"Webhook не настроен; инциденты сохраняются в журнале.";
  q("#securityState").textContent=S.system.private_targets_allowed?"Private targets разрешены.":"Private/loopback/link-local цели заблокированы.";
  var vals=[["Версия",S.system.version],["Uptime",duration(S.system.uptime_seconds)],["Ресурсы",S.system.resources],["Проверки",S.system.checks],["Инциденты",S.system.active_incidents],["Traceroute",S.system.traceroute_available?"готов":"нет"],["База",S.system.database],["Scheduler",S.system.scheduler_enabled?"включён":"выключен"]];
  q("#systemInfo").innerHTML=vals.map(function(v){return '<div class="system-kv"><span>'+esc(v[0])+'</span><b>'+esc(v[1])+'</b></div>'}).join("");
  q("#probeSettings").innerHTML=(S.dashboard.probes||[]).map(function(p){return '<div class="probe-setting"><span>'+esc(p.scope)+'</span><b>'+esc(p.name)+'</b><span>'+(p.online?"онлайн":"нет связи")+' · '+ago(p.last_seen_at)+'</span></div>'}).join("")||empty("Нет probes","");
  renderNotifications()
}

async function manualCheck(id){
  try{toast("Проверяем ресурс…");var r=await api("/api/resources/"+id+"/check",{method:"POST"},true);await loadAll(true);toast(r.scheduled_domestic?"VPS проверен · проверка РФ поставлена в очередь":"Проверка VPS завершена")}catch(e){toast(e.message)}
}
async function trace(id,domestic){
  if(domestic)return traceDomestic(id);
  try{q("#traceOutput").innerHTML=empty("Traceroute","Выполняем маршрут с VPS…");var r=await api("/api/resources/"+id+"/trace",{method:"POST"},true);q("#traceMeta").textContent=r.host+" → "+r.resolved_ip+" · DNS "+r.dns_ms+" мс";q("#traceOutput").innerHTML=r.hops.length?r.hops.map(function(h){return '<div class="trace-hop"><span>'+h.hop+'</span><span>'+esc(h.ip||"*")+'</span><span>'+(h.latency_ms==null?"*":h.latency_ms+" ms")+'</span></div>'}).join(""):'<pre class="trace-raw">'+esc(r.raw)+'</pre>';openView("diagnostics");q("#diagResource").value=String(id);S.diagId=id}catch(e){q("#traceOutput").innerHTML=empty("Traceroute не выполнен",e.message);toast(e.message)}
}
async function traceDomestic(id){
  var probes=S.dashboard.probes||[],p=probes.find(function(x){return x.scope==="DOMESTIC"&&x.online});
  if(!p){toast("Российский probe не подключён");return}
  try{q("#traceOutput").innerHTML=empty("Traceroute РФ","Задание отправлено probe…");var job=await api("/api/resources/"+id+"/trace-domestic?probe_key="+encodeURIComponent(p.probe_key),{method:"POST"},true);openView("diagnostics");for(var i=0;i<30;i++){await new Promise(function(resolve){setTimeout(resolve,1000)});var state=await api("/api/trace-tasks/"+job.task_id);if(state.status==="DONE"){q("#traceMeta").textContent=p.name+" · российский контур";q("#traceOutput").innerHTML='<pre class="trace-raw">'+esc(state.result_text||"Нет вывода")+'</pre>';return}}throw new Error("Probe не вернул traceroute за 30 секунд")}catch(e){q("#traceOutput").innerHTML=empty("Traceroute РФ не выполнен",e.message);toast(e.message)}
}

function catalogItemByKey(key){
  if(!S.catalog)return null;
  for(var gi=0;gi<S.catalog.groups.length;gi++){
    var items=S.catalog.groups[gi].items||[];
    for(var ii=0;ii<items.length;ii++)if(items[ii].key===key)return items[ii]
  }
  return null
}
async function loadResourceCatalog(force){
  if(S.catalog&&!force)return S.catalog;
  S.catalog=await api("/api/resource-catalog");
  return S.catalog
}
function renderCatalog(filter){
  var el=q("#resourceCatalogGroups");if(!el||!S.catalog)return;
  var needle=String(filter||"").trim().toLowerCase();
  var html=S.catalog.groups.map(function(group,groupIndex){
    var items=(group.items||[]).filter(function(item){
      if(!needle)return true;
      return item.name.toLowerCase().indexOf(needle)>=0||item.target.toLowerCase().indexOf(needle)>=0||group.title.toLowerCase().indexOf(needle)>=0
    });
    if(!items.length)return "";
    var available=items.filter(function(item){return !item.already_added}).length;
    var open=needle||groupIndex===0?" open":"";
    return '<details class="catalog-group" data-catalog-group="'+esc(group.key)+'"'+open+'><summary><div class="catalog-group-title"><i style="background:'+esc(group.color||"#55C7FF")+'"></i><div><b>'+esc(group.title)+'</b><span>'+items.length+' ресурсов · '+available+' можно добавить</span></div></div><div class="catalog-group-meta"><span>'+esc(group.source||"")+'</span><small>'+esc(group.as_of||"")+'</small><strong>⌄</strong></div></summary><div class="catalog-group-description">'+esc(group.description||"")+'</div><div class="catalog-resource-list">'+items.map(function(item){
      var checked=!!S.catalogSelected[item.key],disabled=!!item.already_added;
      return '<label class="catalog-resource-row '+(disabled?"already-added":"")+'" data-catalog-row="'+esc(item.key)+'"><input type="checkbox" data-catalog-check="'+esc(item.key)+'" '+(checked?"checked ":"")+(disabled?"disabled ":"")+'><span class="catalog-checkmark"></span>'+resourceIconHtml(item.target,item.name)+'<span class="catalog-resource-main"><b><em>#'+item.rank+'</em>'+esc(item.name)+'</b><small>'+esc(item.target.replace(/^https?:\/\//,""))+'</small></span>'+(disabled?'<span class="catalog-added-badge">Уже добавлен</span>':'<span class="catalog-add-hint">Добавить</span>')+'</label>'
    }).join("")+'</div></details>'
  }).join("");
  el.innerHTML=html||empty("Ничего не найдено","Измените запрос.");
  qa("[data-catalog-check]").forEach(function(box){box.onchange=function(){if(box.checked)S.catalogSelected[box.dataset.catalogCheck]=true;else delete S.catalogSelected[box.dataset.catalogCheck];updateCatalogSelection()}});
  updateCatalogSelection()
}
function updateCatalogSelection(){
  var keys=Object.keys(S.catalogSelected),count=keys.length;
  q("#catalogSelectedCount").textContent=count;
  var custom=String(q("#customResourceTarget").value||"").trim();
  var customPart=custom?(S.customCatalogMatch?" · свой адрес совпал с каталогом":" · + свой ресурс"):"";
  q("#catalogSelectionSummary").textContent=count?(count+" "+(count===1?"ресурс выбран":count<5?"ресурса выбрано":"ресурсов выбрано")+customPart):(custom?"Будет добавлен свой ресурс":"Ничего не выбрано");
  q("#addCatalogResources").disabled=!count&&!custom
}
function fillCustomGroupOptions(){
  var sel=q("#customResourceGroup");if(!sel)return;
  var groups=(S.groups||[]).slice().sort(function(a,b){return Number(a.sort_order||0)-Number(b.sort_order||0)});
  sel.innerHTML=groups.map(function(g){return '<option value="'+esc(g.id)+'" '+(g.id==="CUSTOM"?"selected":"")+'>'+esc(g.title)+'</option>'}).join("")
}
async function openResourceCatalog(){
  S.catalogSelected={};S.customCatalogMatch=null;S.customAutoCatalogKey=null;
  q("#catalogSearch").value="";q("#customResourceTarget").value="";q("#customResourceName").value="";q("#customResourceName").dataset.autoSuggested="1";
  q("#customCatalogMatch").className="custom-match hidden";q("#customCatalogMatch").innerHTML="";
  fillCustomGroupOptions();q("#resourceCatalogGroups").innerHTML='<div class="catalog-loading">Загружаем каталог…</div>';
  q("#resourceDialog").showModal();
  try{await loadResourceCatalog(true);renderCatalog("")}catch(e){q("#resourceCatalogGroups").innerHTML=empty("Каталог не загружен",e.message);toast(e.message)}
  updateCatalogSelection()
}
async function inspectCustomResource(){
  var input=q("#customResourceTarget"),raw=String(input.value||"").trim(),notice=q("#customCatalogMatch"),name=q("#customResourceName");
  if(S.customAutoCatalogKey){delete S.catalogSelected[S.customAutoCatalogKey];S.customAutoCatalogKey=null}
  S.customCatalogMatch=null;
  if(!raw){notice.className="custom-match hidden";notice.innerHTML="";renderCatalog(q("#catalogSearch").value);updateCatalogSelection();return}
  try{
    var match=await api("/api/resource-catalog/match?target="+encodeURIComponent(raw));
    if(input.value.trim()!==raw)return;
    if(match.matched){
      S.customCatalogMatch=match;
      var item=match.resource;
      name.value=item.name;name.dataset.autoSuggested="1";
      notice.className="custom-match catalog-match-found";
      notice.innerHTML='<div>'+resourceIconHtml(item.target,item.name)+'</div><div><b>Этот ресурс уже есть в каталоге</b><span>'+esc(item.name)+' · '+esc(groupTitle(item.group_key))+'</span><small>'+(match.already_added?"Он уже добавлен в мониторинг. Дубликат создан не будет.":"Будет использован каталоговый вариант вместо ручного.")+'</small></div>';
      if(!match.already_added&&!S.catalogSelected[item.key]){S.catalogSelected[item.key]=true;S.customAutoCatalogKey=item.key}
      renderCatalog(q("#catalogSearch").value);updateCatalogSelection();return
    }
    notice.className="custom-match custom-match-new";notice.innerHTML='<div class="custom-match-icon">+</div><div><b>Новый пользовательский ресурс</b><span>Совпадений в каталоге нет.</span><small>Название и логотип определяются автоматически.</small></div>';
    var meta=await getTargetMetadata(raw);
    if(input.value.trim()!==raw)return;
    if((!name.value.trim()||name.dataset.autoSuggested==="1")&&meta.name){name.value=meta.name;name.dataset.autoSuggested="1"}
  }catch(e){
    notice.className="custom-match custom-match-error";notice.innerHTML='<div class="custom-match-icon">!</div><div><b>Не удалось проверить адрес</b><span>'+esc(e.message)+'</span></div>'
  }
  updateCatalogSelection()
}
async function submitResourceCatalog(e){
  e.preventDefault();
  var keys=Object.keys(S.catalogSelected),customTarget=q("#customResourceTarget").value.trim(),messages=[],added=0,existing=0;
  q("#addCatalogResources").disabled=true;
  try{
    if(S.customCatalogMatch&&S.customCatalogMatch.matched&&!S.customCatalogMatch.already_added&&keys.indexOf(S.customCatalogMatch.resource.key)<0)keys.push(S.customCatalogMatch.resource.key);
    if(keys.length){
      var batch=await api("/api/resource-catalog/add",{method:"POST",body:JSON.stringify({resource_keys:keys})},true);
      added+=batch.added.length;existing+=batch.existing.length
    }
    if(customTarget&&!S.customCatalogMatch){
      var customName=q("#customResourceName").value.trim();
      if(!customName){var meta=await getTargetMetadata(customTarget);customName=meta.name||targetMeta(customTarget).name||customTarget}
      var custom=await api("/api/resources",{method:"POST",body:JSON.stringify({
        name:customName,target:customTarget,group_name:q("#customResourceGroup").value||"CUSTOM",
        interval_seconds:60,expected_status_min:200,expected_status_max:399,slow_threshold_ms:1500,failure_threshold:2,enabled:true,alerts_enabled:true
      })},true);
      if(custom.used_catalog){
        var matchedName=custom.catalog_match&&custom.catalog_match.name||customName;
        messages.push("«"+matchedName+"» найден в каталоге — использован каталоговый вариант");
      }
      if(custom.created)added++;else existing++
    }else if(customTarget&&S.customCatalogMatch&&S.customCatalogMatch.already_added){
      existing++;messages.push("«"+S.customCatalogMatch.resource.name+"» уже находится в мониторинге")
    }
    q("#resourceDialog").close();
    S.catalog=null;await loadAll(true);
    var parts=[];if(added)parts.push("добавлено: "+added);if(existing)parts.push("уже было: "+existing);
    toast((parts.length?parts.join(" · "):"Изменений нет")+(messages.length?" · "+messages.join("; "):""))
  }catch(err){toast(err.message);q("#addCatalogResources").disabled=false}
}

function formPayload(){return{name:q("#resourceName").value.trim(),target:q("#resourceTarget").value.trim(),group_name:q("#resourceGroup").value.trim()||"CUSTOM",interval_seconds:Number(q("#resourceInterval").value),expected_status_min:Number(q("#statusMin").value),expected_status_max:Number(q("#statusMax").value),slow_threshold_ms:Number(q("#slowThreshold").value),failure_threshold:Number(q("#failureThreshold").value),enabled:q("#resourceEnabled").checked,alerts_enabled:q("#alertsEnabled").checked}}
function openResourceForm(r){
  if(!r){openResourceCatalog();return}
  q("#resourceForm").reset();q("#resourceId").value=r.id;q("#resourceDialogTitle").textContent="Изменить ресурс";
  q("#resourceName").value=r.name;q("#resourceName").dataset.autoSuggested="0";q("#resourceTarget").value=r.target;q("#resourceGroup").value=r.group_name;
  q("#resourceInterval").value=String(r.interval_seconds||60);q("#statusMin").value=r.expected_status_min||200;q("#statusMax").value=r.expected_status_max||399;
  q("#slowThreshold").value=r.slow_threshold_ms||1500;q("#failureThreshold").value=r.failure_threshold||2;q("#resourceEnabled").checked=!!r.enabled;q("#alertsEnabled").checked=!!r.alerts_enabled;
  syncResourceIdentity(false);q("#resourceEditDialog").showModal()
}
async function saveResource(e){
  e.preventDefault();var id=q("#resourceId").value,p=formPayload();if(!id||!p.name||!p.target){toast("Заполните название и адрес");return}
  try{await api("/api/resources/"+id,{method:"PATCH",body:JSON.stringify(p)},true);q("#resourceEditDialog").close();S.catalog=null;await loadAll(true);toast("Ресурс обновлён")}catch(err){toast(err.message)}
}

async function openDetail(id){
  try{var d=await api("/api/resources/"+id),r=d.resource;S.detailId=id;q("#detailTitle").textContent=r.name;q("#detailBody").innerHTML='<div class="detail-top"><div class="detail-kv"><span>Вывод</span><b>'+diagText(r.diagnosis)+'</b></div><div class="detail-kv"><span>VPS</span><b>'+stText(r.external&&r.external.status)+'</b></div><div class="detail-kv"><span>РФ</span><b>'+stText(r.domestic&&r.domestic.status)+'</b></div><div class="detail-kv"><span>Отклик</span><b>'+num((r.domestic||r.external||{}).response_time_ms," мс")+'</b></div></div><div class="detail-section"><h3>'+esc(r.target)+'</h3><div class="detail-kv"><span>Пояснение</span><b>'+esc(r.diagnosis_text||"—")+'</b></div></div><div class="detail-section"><h3>Последние проверки</h3><div class="check-list">'+(d.checks.length?d.checks.map(function(c){return '<div class="check-row"><div>'+fmt(c.checked_at)+'</div><div>'+esc(c.probe_scope||"")+' · '+stText(c.status)+'</div><div>'+esc(c.message||"")+'</div><div>'+c.response_time_ms+' мс</div></div>'}).join(""):empty("Проверок нет",""))+'</div></div>';q("#detailDialog").showModal()}catch(e){toast(e.message)}
}
async function deleteResource(){var r=resourceById(S.detailId);if(!r)return;if(!confirm("Удалить ресурс «"+r.name+"» и его историю?"))return;try{await api("/api/resources/"+r.id,{method:"DELETE"},true);q("#detailDialog").close();await loadAll(true);toast("Ресурс удалён")}catch(e){toast(e.message)}}

function appIconMarkup(name){
  var icons={
    overview:'<svg viewBox="0 0 24 24"><path d="M3 11.5L12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/><path d="M9.5 20v-6h5v6"/></svg>',
    resources:'<svg viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="11" rx="2"/><path d="M8 20h8M12 17v3"/></svg>',
    alerts:'<svg viewBox="0 0 24 24"><path d="M12 3l9 16H3L12 3z"/><path d="M12 9v4M12 16.5h.01"/></svg>',
    map:'<svg viewBox="0 0 24 24"><path d="M9 18l-5 2V6l5-2 6 2 5-2v14l-5 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>',
    probes:'<svg viewBox="0 0 24 24"><circle cx="12" cy="11" r="3"/><path d="M19 11c0 5-7 10-7 10S5 16 5 11a7 7 0 0114 0z"/></svg>',
    history:'<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
    notifications:'<svg viewBox="0 0 24 24"><path d="M6 9a6 6 0 0112 0c0 7 3 7 3 7H3s3 0 3-7"/><path d="M10 20h4"/></svg>',
    integrations:'<svg viewBox="0 0 24 24"><circle cx="7" cy="7" r="2"/><circle cx="17" cy="7" r="2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/><path d="M9 7h6M7 9v6M17 9v6M9 17h6"/></svg>',
    settings:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19 13.5v-3l-2-.7-.8-1.9.9-1.9-2.1-2.1-1.9.9-1.9-.8L10.5 2h-3l-.7 2-1.9.8-1.9-.9L.9 6l.9 1.9L1 9.8l-2 .7v3l2 .7.8 1.9-.9 1.9L3 20.1l1.9-.9 1.9.8.7 2h3l.7-2 1.9-.8 1.9.9 2.1-2.1-.9-1.9.8-1.9z" transform="translate(2.5 0) scale(.79)"/></svg>',
    bell:'<svg viewBox="0 0 24 24"><path d="M6 9a6 6 0 0112 0c0 7 3 7 3 7H3s3 0 3-7"/><path d="M10 20h4"/></svg>',
    theme:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    world:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 010 18M12 3a15 15 0 000 18"/></svg>',
    expand:'<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"/><path d="M9 9L3 3M15 9l6-6M9 15l-6 6M15 15l6 6"/></svg>',
    cloud:'<svg viewBox="0 0 32 32"><path d="M9 24h14a6 6 0 000-12h-.5A8 8 0 007 14.5 4.8 4.8 0 009 24z" fill="#0b2036"/><path d="M13 17h6l-2.1 3H20l-5 6 1.2-4H13z" fill="#0b2036"/></svg>'
  };
  return icons[name]||""
}
function hydrateChromeIcons(){
  qa(".side-item[data-view]").forEach(function(b){var slot=b.querySelector(":scope > span");if(slot)slot.innerHTML=appIconMarkup(b.dataset.view)});
  var brand=q(".brand-logo");if(brand)brand.innerHTML=appIconMarkup("cloud");
  var alert=q("#openAlerts");if(alert)alert.innerHTML=appIconMarkup("bell")+'<i id="notifyCount" class="notify-count hidden">0</i>';
  var theme=q("#themeToggle");if(theme)theme.innerHTML=appIconMarkup("theme");
  var world=q("#worldButton");if(world)world.innerHTML=appIconMarkup("world");
  var expand=q("#expandChart");if(expand)expand.innerHTML=appIconMarkup("expand")
}

function setup(){
  hydrateChromeIcons();
  updateClock();setInterval(updateClock,1000);
  qa(".side-item[data-view]").forEach(function(b){b.onclick=function(){openView(b.dataset.view)}});
  qa("[data-view-jump]").forEach(function(b){b.onclick=function(){openView(b.dataset.viewJump)}});
  q("#globalSearch").oninput=function(){renderSearch(this.value)};
  var identityTimer=null;
  q("#resourceTarget").addEventListener("input",function(){clearTimeout(identityTimer);identityTimer=setTimeout(function(){syncResourceIdentity(false)},180)});
  q("#resourceName").addEventListener("input",function(){this.dataset.autoSuggested="0"});
  document.addEventListener("keydown",function(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();q("#globalSearch").focus()}});
  document.addEventListener("click",function(e){if(!e.target.closest(".search-wrap"))q("#searchResults").classList.add("hidden")});
  q("#themeToggle").onclick=function(){var light=document.documentElement.dataset.theme==="light";document.documentElement.dataset.theme=light?"dark":"light";localStorage.setItem("netweather_theme",light?"dark":"light");renderAll()};
  document.documentElement.dataset.theme=localStorage.getItem("netweather_theme")||"dark";
  q("#openAlerts").onclick=function(){openView("alerts")};
  q("#ackAllIncidents").onclick=acknowledgeAllIncidents;
  q("#worldButton").onclick=function(){openView("map")};
  q("#manageGroups").onclick=function(){openView("groups")};
  q("#customizeOverview").onclick=openDashboardPreferences;
  q("#dashboardPreferencesForm").onsubmit=submitDashboardPreferences;
  q("#resetDashboardPreferences").onclick=resetDashboardPreferences;
  [q("#sidebarAddResource"),q("#openAddResource"),q("#overviewAddResource")].forEach(function(b){if(b)b.onclick=openResourceCatalog});
  q("#resourceCatalogForm").onsubmit=submitResourceCatalog;
  q("#catalogSearch").oninput=function(){renderCatalog(this.value)};
  var customTimer=null;
  q("#customResourceTarget").oninput=function(){clearTimeout(customTimer);customTimer=setTimeout(inspectCustomResource,260);updateCatalogSelection()};
  q("#customResourceName").oninput=function(){this.dataset.autoSuggested="0"};
  q("#resourceForm").onsubmit=saveResource;q("#groupForm").onsubmit=saveGroup;q("#openAddGroup").onclick=function(){openGroupForm(null)};
  qa(".modal-close").forEach(function(b){b.onclick=function(){b.closest("dialog").close()}});
  q("#openToken2").onclick=function(){toast("Development mode: авторизация отключена")};
  q("#tokenForm").onsubmit=function(e){e.preventDefault();q("#tokenDialog").close()};
  q("#clearToken").onclick=function(){q("#tokenDialog").close()};
  qa(".seg").forEach(function(b){b.onclick=async function(){qa(".seg").forEach(function(x){x.classList.remove("active")});b.classList.add("active");S.streamMinutes=Number(b.dataset.minutes);S.realtime=await api("/api/realtime?minutes="+S.streamMinutes+"&scope=EXTERNAL");renderRealtime();renderResourceCards();renderOverviewTable()}});
  q("#streamChart").addEventListener("mousemove",handleChartMove);q("#streamChart").addEventListener("mouseleave",function(){q("#chartTooltip").classList.add("hidden")});
  q("#expandChart").onclick=function(){q(".streams-panel").classList.toggle("chart-expanded")};
  q("#mapZoomIn").onclick=function(){S.mapScale=Math.min(2,S.mapScale+.15);q("#worldMapSvg").style.transform="scale("+S.mapScale+")"};
  q("#mapZoomOut").onclick=function(){S.mapScale=Math.max(.8,S.mapScale-.15);q("#worldMapSvg").style.transform="scale("+S.mapScale+")"};
  q("#mapRegion").onchange=function(){toast("Фильтр карты: "+this.options[this.selectedIndex].text)};
  q("#faultResourceSelect").onchange=function(){S.faultId=Number(this.value);renderFaultPanel()};
  q("#searchInput").oninput=renderResources;q("#groupFilter").onchange=renderResources;q("#statusFilter").onchange=renderResources;
  q("#diagResource").onchange=function(){S.diagId=Number(this.value);var r=resourceById(this.value);if(r)showDiagnostic(r)};
  q("#diagCheck").onclick=function(){var id=Number(q("#diagResource").value);if(id)manualCheck(id)};q("#diagTrace").onclick=function(){var id=Number(q("#diagResource").value);if(id)trace(id,false)};q("#diagTraceDomestic").onclick=function(){var id=Number(q("#diagResource").value);if(id)trace(id,true)};
  q("#historyRange").onchange=function(){loadAll(true)};
  q("#enableNotifications").onclick=async function(){if(!("Notification" in window)){toast("Браузер не поддерживает уведомления");return}var p=await Notification.requestPermission();renderNotifications();toast(p==="granted"?"Уведомления включены":"Разрешение не выдано")};
  q("#deleteResource").onclick=deleteResource;q("#editResource").onclick=function(){var r=resourceById(S.detailId);q("#detailDialog").close();if(r)openResourceForm(r)};q("#detailCheck").onclick=function(){q("#detailDialog").close();manualCheck(S.detailId)};q("#detailTrace").onclick=function(){q("#detailDialog").close();trace(S.detailId,false)};
  window.addEventListener("resize",function(){renderRealtime();renderHistory();renderResourceCards();renderOverviewTable();applyDashboardPreferences()});
  loadAll(false);S.poll=setInterval(function(){loadAll(true)},15000)
}
document.addEventListener("DOMContentLoaded",setup);
})();