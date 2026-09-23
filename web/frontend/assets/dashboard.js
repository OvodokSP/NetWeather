(function(){
"use strict";

var COLORS=["#ff6174","#58c7ff","#78a5ff","#42df9c","#ffd34f","#9a65ff","#56e1d0","#ff8bc7","#b8e35d","#7bb6ff"];
var S={
  dashboard:null,incidents:[],system:null,groups:[],realtime:null,realtimeDom:null,events:[],incidentNoticesInitialized:false,
  streamMinutes:60,detailId:null,diagId:null,
  faultId:null,view:"overview",poll:null,authRequired:false,
  owner:true,mapScale:1,metaCache:{},catalog:null,catalogSelected:{},customCatalogMatch:null,customAutoCatalogKey:null,
  dashboardPrefs:null,searchIndex:-1,searchAddTarget:null,pendingSearchTarget:null,coreOnline:false,lastSuccessAt:null,
  overviewResourceMode:"ALL"
};

var DASHBOARD_PREFS_KEY="netweather_dashboard_v1";
var DASHBOARD_PANEL_LABELS={
  global_kpi:"Глобальная доступность",
  resources_kpi:"Доступные ресурсы",
  latency_kpi:"Типичный отклик",
  domestic_kpi:"Российский контур",
  personal_kpi:"Моя сеть",
  incidents_kpi:"Активные инциденты",
  events:"Последние события",
  map:"Карта сбоев",
  resources_table:"Таблица ресурсов",
  fault_domain:"Трассировка / fault domain"
};
var DASHBOARD_PANEL_ORDER=["resources_kpi","latency_kpi","personal_kpi","incidents_kpi","events","map","resources_table","fault_domain"];

function defaultDashboardPreferences(){
  return{
    panels:{
      resources_kpi:true,latency_kpi:true,personal_kpi:true,incidents_kpi:true,
      events:true,map:true,resources_table:true,fault_domain:true
    }
  }
}
function loadDashboardPreferences(){
  if(S.dashboardPrefs)return S.dashboardPrefs;
  var base=defaultDashboardPreferences();
  try{
    var raw=JSON.parse(localStorage.getItem(DASHBOARD_PREFS_KEY)||"null");
    if(raw&&typeof raw==="object"){
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
  var hasPersonal=probes.some(function(p){return ["PERSONAL","BROWSER","DEVICE","LOCAL"].indexOf(String(p.scope||"").toUpperCase())>=0&&p.online});
  var hasMap=probes.some(function(p){return Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))});
  return{
    resources_kpi:true,
    latency_kpi:true,
    personal_kpi:hasPersonal,
    incidents_kpi:true,
    events:true,
    map:hasMap,
    resources_table:resources.length>0,
    fault_domain:resources.length>0,
  }
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
  q(".kpi-grid").style.removeProperty("grid-template-columns");
  [[".overview-row-chart"],[".overview-row-middle"],[".overview-row-bottom"]].forEach(function(entry){
    var row=q(entry[0]);if(!row)return;
    var visible=Array.from(row.children).filter(function(n){return !n.classList.contains("dashboard-hidden")});
    row.classList.toggle("dashboard-row-hidden",visible.length===0);
    row.classList.toggle("single-panel",visible.length===1)
  });
  q(".overview-grid").style.removeProperty("grid-template-rows");
}
function renderDashboardPreferencesModal(){
  if(!S.dashboard)return;
  var prefs=loadDashboardPreferences(),caps=dashboardCapabilities();
  q("#dashboardPanelChoices").innerHTML=DASHBOARD_PANEL_ORDER.filter(function(key){return caps[key]}).map(function(key){
    var checked=prefs.panels[key]!==false;
    return '<label class="dashboard-panel-choice"><input type="checkbox" data-dashboard-choice="'+key+'" '+(checked?"checked":"")+'><span class="preferences-checkbox"></span><b>'+esc(DASHBOARD_PANEL_LABELS[key])+'</b></label>'
  }).join("");
  hydrateResourceIcons()
}
function openDashboardPreferences(){
  renderDashboardPreferencesModal();
  openDialog(q("#dashboardPreferencesDialog"),"#dashboardPanelChoices")
}
function submitDashboardPreferences(e){
  e.preventDefault();
  var prefs=loadDashboardPreferences();
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

function focusableIn(root){
  if(!root)return[];
  return Array.prototype.slice.call(root.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])'))
}
function openDialog(dialog,focusSelector){
  if(!dialog)return;
  dialog._returnFocus=document.activeElement&&document.activeElement!==document.body?document.activeElement:null;
  if(!dialog.open)dialog.showModal();
  requestAnimationFrame(function(){
    var target=focusSelector?dialog.querySelector(focusSelector):null;
    if(!target)target=focusableIn(dialog)[0];
    if(target&&typeof target.focus==="function")target.focus({preventScroll:true})
  })
}
function closeDialog(dialog){
  if(dialog&&dialog.open&&!dialog.dataset.locked)dialog.close()
}
function setupDialogs(){
  qa("dialog.modal").forEach(function(dialog){
    dialog.addEventListener("click",function(e){
      if(e.target===dialog&&!dialog.dataset.locked)dialog.close()
    });
    dialog.addEventListener("close",function(){
      dialog.removeAttribute("aria-busy");
      var back=dialog._returnFocus;dialog._returnFocus=null;
      if(back&&document.contains(back)&&typeof back.focus==="function")requestAnimationFrame(function(){back.focus({preventScroll:true})})
    });
    dialog.addEventListener("cancel",function(e){
      if(dialog.dataset.locked){e.preventDefault()}
    })
  })
}
function setBusy(button,busy,label){
  if(!button)return;
  if(busy){
    if(button.dataset.busy==="1")return;
    button.dataset.busy="1";button._busyHtml=button.innerHTML;button._busyDisabled=button.disabled;
    button.disabled=true;button.setAttribute("aria-busy","true");button.classList.add("is-busy");
    var dialog=button.closest&&button.closest("dialog");if(dialog){dialog.dataset.locked="1";dialog.setAttribute("aria-busy","true")}
    if(label)button.textContent=label
  }else{
    if(button.dataset.busy!=="1")return;
    if(button._busyHtml!=null)button.innerHTML=button._busyHtml;
    button.disabled=!!button._busyDisabled;button.removeAttribute("aria-busy");button.classList.remove("is-busy");
    var dialog=button.closest&&button.closest("dialog");if(dialog){delete dialog.dataset.locked;dialog.removeAttribute("aria-busy")}
    delete button.dataset.busy;delete button._busyHtml;delete button._busyDisabled
  }
}
async function withBusy(button,label,fn){
  if(button&&button.dataset.busy==="1")return;
  setBusy(button,true,label);
  try{return await fn()}finally{setBusy(button,false)}
}
function confirmAction(options){
  options=options||{};
  var dialog=q("#confirmDialog"),accept=q("#confirmAccept"),cancel=q("#confirmCancel");
  if(!dialog||!accept||!cancel)return Promise.resolve(false);
  q("#confirmEyebrow").textContent=options.eyebrow||"ПОДТВЕРЖДЕНИЕ";
  q("#confirmTitle").textContent=options.title||"Подтвердите действие";
  q("#confirmMessage").textContent=options.message||"Продолжить?";
  q("#confirmHint").textContent=options.hint||"";
  accept.textContent=options.accept||"Продолжить";
  accept.className="btn "+(options.danger===false?"primary":"danger");
  return new Promise(function(resolve){
    var settled=false;
    function finish(value){
      if(settled)return;settled=true;
      accept.onclick=null;cancel.onclick=null;
      if(dialog.open)dialog.close();
      resolve(value)
    }
    accept.onclick=function(){finish(true)};
    cancel.onclick=function(){finish(false)};
    dialog.addEventListener("close",function(){finish(false)},{once:true});
    openDialog(dialog,"#confirmAccept")
  })
}
function hideSearch(){
  var el=q("#searchResults"),input=q("#globalSearch");if(!el||!input)return;
  el.classList.add("hidden");input.setAttribute("aria-expanded","false");S.searchIndex=-1;S.searchOpen=false
}
function showSearch(){
  var el=q("#searchResults"),input=q("#globalSearch");if(!el||!input)return;
  el.classList.remove("hidden");input.setAttribute("aria-expanded","true");S.searchOpen=true
}
function handleSearchKeydown(e){
  var results=qa("#searchResults [data-search-option]");
  if(e.key==="Escape"){hideSearch();return}
  if(!results.length)return;
  if(e.key==="ArrowDown"){
    e.preventDefault();S.searchIndex=Math.min(results.length-1,S.searchIndex+1);results[S.searchIndex].focus();return
  }
  if(e.key==="ArrowUp"){
    e.preventDefault();if(S.searchIndex<=0){S.searchIndex=-1;q("#globalSearch").focus()}else{S.searchIndex--;results[S.searchIndex].focus()}
  }
}
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"})[c]})}
function legacyToken(){return localStorage.getItem("netweather_token")||""}
function token(){return legacyToken()}
function auth(){return token()?{"Authorization":"Bearer "+token()}:{}}
function toast(m){var e=q("#toast");if(!e)return;e.textContent=m;e.classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(function(){e.classList.remove("show")},3000)}
function fmt(ts){if(!ts)return "—";return new Date(ts*1000).toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"})}
function shortTime(ts){if(!ts)return "—";return new Date(ts*1000).toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"})}
function ago(ts){if(!ts)return "—";var d=Math.max(0,Math.floor(Date.now()/1000-ts));if(d<60)return d+" сек назад";if(d<3600)return Math.floor(d/60)+" мин назад";if(d<86400)return Math.floor(d/3600)+" ч назад";return Math.floor(d/86400)+" дн назад"}
function duration(sec){sec=Number(sec||0);if(sec<60)return sec+" сек";if(sec<3600)return Math.floor(sec/60)+" мин";if(sec<86400)return Math.floor(sec/3600)+" ч";return Math.floor(sec/86400)+" дн"}
function num(v,suffix){return v==null||!Number.isFinite(Number(v))?"—":Math.round(Number(v))+(suffix||"")}
function stText(s){return({OK:"Доступен",HTTP_REJECTED:"Доступен · probe отклонён",DNS_ERROR:"DNS ошибка",TCP_ERROR:"TCP ошибка",TLS_ERROR:"TLS ошибка",HTTP_ERROR:"HTTP ошибка",TIMEOUT:"Таймаут",BLOCKED_TARGET:"Заблокировано",UNKNOWN:"Нет данных",UNKNOWN_ERROR:"Нет данных"})[s]||"Нет данных"}
function stClass(s){return s==="OK"||s==="HTTP_REJECTED"?"ok":s==="TIMEOUT"?"warn":isConfirmedUnavailable(s)?"bad":"neutral"}
function isReachable(s){return s==="OK"||s==="HTTP_REJECTED"}
function isConfirmedUnavailable(s){return ["DNS_ERROR","TCP_ERROR","TLS_ERROR","HTTP_ERROR","TIMEOUT","BLOCKED_TARGET"].indexOf(s)>=0}
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
  return{name:name,host:host,favicon:"",known:isKnown}
}
function getTargetMetadata(value){
  var local=targetMeta(value),u=targetUrl(value);
  if(!u||!local.host)return Promise.resolve({name:local.name,host:local.host,favicon_url:""});
  var key=u.href;
  if(!S.metaCache[key]){
    S.metaCache[key]=api("/api/target-meta?target="+encodeURIComponent(value)).then(function(remote){
      return{name:local.known?local.name:(remote.name||local.name),host:remote.host||local.host,favicon_url:""}
    }).catch(function(){return{name:local.name,host:local.host,favicon_url:""}})
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
  return '<i class="resource-glyph" data-icon-target="'+esc(target)+'" data-icon-name="'+esc(name||m.name||"")+'"><span class="resource-logo-fallback">'+fallback+'</span></i>'
}

function paintResourceIcon(node,meta){
  if(!node||!meta)return;
  var fallback=esc((node.dataset.iconName||meta.name||"?").slice(0,2).toUpperCase());
  node.innerHTML='<span class="resource-logo-fallback">'+fallback+'</span>'
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
  if(!m.host){preview.innerHTML="<span>NW</span>";if(hint)hint.textContent="После ввода ссылки NetWeather предложит название ресурса.";return}
  var canFill=force||!name.value.trim()||name.dataset.autoSuggested==="1";
  if(canFill&&m.name){name.value=m.name;name.dataset.autoSuggested="1"}
  preview.innerHTML='<span>'+esc((m.name||"?").slice(0,2).toUpperCase())+'</span>';
  if(hint)hint.textContent=m.host+" · определяем название…";
  var remote=await getTargetMetadata(raw);
  if(target.value!==raw)return;
  if((force||!name.value.trim()||name.dataset.autoSuggested==="1")&&remote.name){name.value=remote.name;name.dataset.autoSuggested="1"}
  var fallback=esc((remote.name||m.name||"?").slice(0,2).toUpperCase());
  preview.innerHTML='<span>'+fallback+'</span>';
  if(hint)hint.textContent=(remote.host||m.host)+(remote.name?" · «"+remote.name+"»":"")
}

function realtimeById(id){return(S.realtime&&S.realtime.resources||[]).find(function(r){return r.id===Number(id)})}
function empty(title,text){return '<div class="empty-state"><div><b>'+esc(title)+'</b><div style="margin-top:5px">'+esc(text||"")+'</div></div></div>'}
function getCss(name){return getComputedStyle(document.documentElement).getPropertyValue(name).trim()||"#92a8c2"}

async function api(path,opt,secure){
  opt=opt||{};
  if(secure&&S.authRequired&&!S.owner){
    openOwnerLogin();
    throw new Error("Управление требует авторизации")
  }
  var headers={"Content-Type":"application/json"};
  Object.assign(headers,opt.headers||{});
  var oldToken=legacyToken();if(secure&&oldToken)headers.Authorization="Bearer "+oldToken;
  var res=await fetch(path,Object.assign({},opt,{headers:headers}));
  if(!res.ok){
    var msg="HTTP "+res.status;
    try{var j=await res.json();msg=j.detail||msg}catch(_e){}
    throw new Error(msg)
  }
  if(res.status===204)return null;
  return res.json()
}

function applyOwnerMode(){
  var viewer=S.authRequired&&!S.owner;
  document.body.classList.toggle("viewer-mode",viewer);
  var title=q("#ownerModeTitle"),hint=q("#ownerModeHint"),button=q("#ownerAuthAction");
  if(title)title.textContent=S.owner?"Режим владельца":"Режим просмотра";
  if(hint)hint.textContent=S.owner?"управление доступно":"просмотр и добавление";
  if(button){button.textContent=!S.authRequired?"Авторизация отключена":S.owner?"Выйти из режима владельца":"Войти как владелец";button.disabled=!S.authRequired;button.className="btn "+(S.owner&&S.authRequired?"secondary":"primary")}
}
function openOwnerLogin(){
  if(!S.authRequired){toast("Авторизация владельца не требуется");return}
  q("#ownerPassword").value="";
  openDialog(q("#ownerLoginDialog"),"#ownerPassword")
}
async function submitOwnerLogin(e){
  e.preventDefault();var password=q("#ownerPassword").value,button=e.submitter||q("#ownerLoginForm [type=submit]");
  try{await withBusy(button,"Входим…",async function(){
    await api("/api/session/login",{method:"POST",body:JSON.stringify({password:password})});
    localStorage.removeItem("netweather_token");q("#ownerLoginDialog").close();await loadAll(true);toast("Режим владельца включён");
    var pending=S.pendingSearchTarget;S.pendingSearchTarget=null;if(pending)await openResourceCatalog(pending)
  })}catch(err){toast(err.message);q("#ownerPassword").focus()}
}
async function ownerAuthAction(){
  if(!S.owner){openOwnerLogin();return}
  try{await api("/api/session/logout",{method:"POST"});await loadAll(true);toast("Открыт режим просмотра")}catch(err){toast(err.message)}
}

function openView(name){
  S.view=name;
  qa(".view").forEach(function(v){v.classList.toggle("active",v.id==="view-"+name)});
  qa(".side-item[data-view]").forEach(function(b){b.classList.toggle("active",b.dataset.view===name)});
  if(name==="overview"){renderRealtime();renderDomesticRealtime()}
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

function mergeRealtimeWindow(previous,current,totalMinutes){
  if(!previous||totalMinutes<=60)return current;
  var floor=Number(current.to||Date.now()/1000)-totalMinutes*60,refreshFrom=Number(current.from||0),oldRows=new Map((previous.resources||[]).map(function(row){return [Number(row.id),row]}));
  var resources=(current.resources||[]).map(function(row){
    var old=oldRows.get(Number(row.id)),points=new Map();
    (old&&old.points||[]).forEach(function(point){var ts=Number(point.timestamp);if(ts>=floor&&ts<refreshFrom)points.set(ts+"|"+point.status+"|"+point.latency_ms,point)});
    (row.points||[]).forEach(function(point){var ts=Number(point.timestamp);if(ts>=floor)points.set(ts+"|"+point.status+"|"+point.latency_ms,point)});
    return Object.assign({},row,{points:Array.from(points.values()).sort(function(a,b){return Number(a.timestamp)-Number(b.timestamp)})})
  });
  return Object.assign({},current,{minutes:totalMinutes,from:floor,resources:resources})
}

async function loadAll(silent,realtimeWindow){
  if(S.loading)return;
  S.loading=true;
  try{
    var requestMinutes=Number(realtimeWindow||S.streamMinutes);
    var a=await Promise.all([
      api("/api/dashboard"),
      api("/api/incidents?limit=100"),
      api("/api/system"),
      api("/api/groups"),
      api("/api/realtime/combined?minutes="+requestMinutes),
      api("/api/events?limit=30"),
      api("/api/session")
    ]);
    S.dashboard=a[0];if(S.dashboard&&Array.isArray(S.dashboard.resources))S.dashboard.resources=S.dashboard.resources.map(normalizeResourceShape);S.incidents=a[1];notifyIncidentTransitions(S.incidents);S.system=a[2];S.groups=a[3];S.realtime=mergeRealtimeWindow(S.realtime,a[4].global,S.streamMinutes);S.realtimeDom=mergeRealtimeWindow(S.realtimeDom,a[4].russia,S.streamMinutes);S.events=a[5];
    S.authRequired=!!a[6].auth_required;S.owner=!S.authRequired||!!a[6].authenticated;
    S.lastSuccessAt=Date.now();renderAll();setCoreOnline(true)
  }catch(e){
    setCoreOnline(false);
    if(!silent)toast("Ошибка загрузки: "+e.message)
  }finally{S.loading=false
  }
}

function setCoreOnline(ok){
  S.coreOnline=!!ok;
  document.body.classList.toggle("core-offline",!ok);
  q("#apiStatus").textContent=ok?"онлайн":"нет связи";
  var p=q(".pulse-dot");if(p)p.style.background=ok?"var(--green)":"var(--red)";
  if(!ok){
    var health=q("#topSystemStatus");
    if(health){
      health.className="health-pill bad";
      health.querySelector("b").textContent="Нет связи с Core";
      health.querySelector("span").textContent="показаны последние данные"
    }
    if(q("#welcomeTitle"))q("#welcomeTitle").textContent="Данные временно не обновляются";
    if(q("#welcomeSubtitle")){
      var last=S.lastSuccessAt?new Date(S.lastSuccessAt).toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit",second:"2-digit"}):"неизвестно";
      q("#welcomeSubtitle").textContent="Последний успешный снимок: "+last+". Статусы ниже могут быть устаревшими."
    }
  }
}

function applyCapabilityNavigation(){
  if(!S.dashboard)return;
  var probes=S.dashboard.probes||[];
  var hasMap=probes.some(function(p){return Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))});
  var hasDomestic=probes.some(function(p){return isDomesticProbe(p)&&p.online});
  var mapNav=q('.side-item[data-view="map"]'),world=q("#worldButton"),domTrace=q("#diagTraceDomestic");
  if(mapNav)mapNav.classList.toggle("capability-hidden",!hasMap);
  if(world)world.classList.toggle("capability-hidden",!hasMap);
  if(domTrace)domTrace.classList.toggle("capability-hidden",!hasDomestic);
  if(!hasMap&&S.view==="map")openView("overview")
}

function normalizeResourceShape(r){if(r&&typeof r==="object"){if(!r.external&&r.global)r.external=r.global;if(!r.domestic&&r.russia)r.domestic=r.russia}return r}

function isDomesticProbe(p){
  var scope=String(p&&p.scope||"").toUpperCase();
  return scope==="DOMESTIC"||scope==="RUSSIA"||scope==="GLOBALPING_RU"||String(p&&p.probe_key||"").toUpperCase()==="GLOBALPING_RU"
}

function renderAll(){
  applyOwnerMode();
  renderOverview();
  renderGroups();
  renderResources();
  renderIncidents();
  renderDiagnostics();
  renderProbes();
  renderNotifications();
  renderSettings();
  applyCapabilityNavigation();
  if(S.searchOpen)renderSearch(q("#globalSearch").value);
  if(S.system)q("#versionLabel").textContent=S.system.version
}

function renderOverview(){
  if(!S.dashboard)return;
  var summary=S.dashboard.summary||{},legacy=S.dashboard.legacy_summary||{};
  var resources=(S.dashboard.resources||[]).filter(function(r){return r.enabled!==false&&r.enabled!==0});
  var active=S.incidents.filter(function(i){return !i.closed_at});
  var unread=active.filter(function(i){return !i.acknowledged_at});
  var available=resources.filter(function(r){return isReachable((r.external||{}).status)});
  var latencies=available.map(function(r){return Number((r.external||{}).response_time_ms)}).filter(Number.isFinite).sort(function(a,b){return a-b});
  var medianLatency=latencies.length?latencies.length%2?latencies[(latencies.length-1)/2]:Math.round((latencies[latencies.length/2-1]+latencies[latencies.length/2])/2):null;
  var latestCheck=resources.reduce(function(last,r){return Math.max(last,Number(r.checked_at||0))},0);

  q("#kpiResources").textContent=available.length;
  q("#kpiResourcesDelta").textContent="из "+resources.length;
  q("#kpiResourcesDelta").style.color=available.length===resources.length?"var(--green)":available.length?"var(--orange)":"var(--red)";
  q("#kpiResourcesHint").textContent=!resources.length?"добавьте первый ресурс":available.length===resources.length?"все отвечают сейчас":(resources.length-available.length)+" требуют внимания";
  q("#kpiLatency").textContent=medianLatency==null?"—":Math.round(medianLatency);
  q("#kpiLatencyHint").textContent=medianLatency==null?"нет свежих измерений":medianLatency<500?"быстрый отклик":medianLatency<1500?"умеренная задержка":"высокая задержка";

  q("#kpiPersonal").textContent="—";
  q("#kpiPersonalHint").textContent="device-probe ещё не подключён";
  q("#kpiIncidents").textContent=active.length;
  q("#kpiIncidentDelta").textContent=unread.length?unread.length+" новых":active.length?"прочитано":"спокойно";
  q("#kpiIncidentDelta").style.color=unread.length?"var(--red)":"var(--muted)";
  q("#kpiIncidentHint").textContent=active.length?(unread.length?unread.length+" непрочитанных из "+active.length:"прочитано, но не закрыто: "+active.length):"открытых инцидентов нет";

  drawBars(q("#kpiResourcesSpark"),resources.map(function(r){return isReachable((r.external||{}).status)?1:0}),available.length===resources.length?COLORS[3]:COLORS[4]);
  drawSpark(q("#kpiLatencySpark"),latencies,COLORS[5]);
  drawSpark(q("#kpiPersonalSpark"),[],COLORS[3]);
  drawBars(q("#kpiIncidentSpark"),incidentSpark(),COLORS[0]);

  var state=overviewState(summary,legacy,active.length);
  q("#welcomeTitle").textContent=state.title;q("#welcomeSubtitle").textContent=state.text;
  var freshness=q("#overviewFreshness"),freshnessWrap=freshness.closest(".overview-freshness");
  freshness.textContent=latestCheck?ago(latestCheck):"ожидаются";
  freshnessWrap.classList.toggle("stale",!latestCheck||Date.now()/1000-latestCheck>90);
  var health=q("#topSystemStatus");health.className="health-pill "+state.cls;health.querySelector("b").textContent=state.short;health.querySelector("span").textContent=state.healthText;

  q("#alertBadge").textContent=unread.length;q("#alertBadge").classList.toggle("hidden",!unread.length);
  q("#notifyCount").textContent=unread.length;q("#notifyCount").classList.toggle("hidden",!unread.length);

  renderRealtime();renderDomesticRealtime();renderEvents();renderMap();renderOverviewTable();renderFaultPanel();applyDashboardPreferences()
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

function scopeRows(source){return source&&source.resources||[]}
function latestPoint(row){var pts=(row.points||[]).slice().sort(function(a,b){return Number(b.timestamp)-Number(a.timestamp)});return pts[0]||null}
function timelineState(point){if(!point)return"unknown";return point.state==="UP"?"up":point.state==="DOWN"?"down":"unknown"}
function formatTimelineTime(ts){return ts?new Date(ts*1000).toLocaleString("ru-RU",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",second:"2-digit"}):"—"}
function drawResourceTimeline(containerId,statusId,source,scope){
  var el=q("#"+containerId),status=q("#"+statusId);if(!el)return;
  var rows=scopeRows(source),start=Number(source&&source.from||Date.now()/1000-S.streamMinutes*60),end=Number(source&&source.to||Date.now()/1000),span=Math.max(1,end-start),resources=S.dashboard&&S.dashboard.resources||[];
  if(status){var any=rows.some(function(r){return (r.points||[]).length});status.textContent=any?"наблюдений: "+rows.reduce(function(n,r){return n+(r.points||[]).length},0):"нет данных";status.className="stream-scope-badge "+(any?"ok":"neutral")}
  if(!rows.length){el.innerHTML=empty("Нет ресурсов","Добавьте ресурсы в мониторинг.");return}
  var staleAfter=scope==="RUSSIA"?1800:120;
  el.innerHTML=rows.map(function(row){
    var pts=(row.points||[]).slice().sort(function(a,b){return Number(a.timestamp)-Number(b.timestamp)}),resource=resources.find(function(r){return Number(r.id)===Number(row.id)})||{},latest=latestPoint(row),now=Date.now()/1000,state=latest&&now-Number(latest.timestamp)<=staleAfter?timelineState(latest):"unknown";
    var segments=[],cursor=start;
    pts.forEach(function(point,index){
      var t=Math.max(start,Number(point.timestamp)),scheduled=index+1<pts.length?Math.min(end,Number(pts[index+1].timestamp)):end,next=Math.min(scheduled,t+staleAfter);
      if(t>cursor)segments.push({left:(cursor-start)/span*100,width:(t-cursor)/span*100,state:"unknown",title:"Нет измерений · "+formatTimelineTime(cursor)});
      if(next>t){var st=timelineState(point),restricted=scope==="RUSSIA"&&st==="down"&&isReachable((resource.external||{}).status);segments.push({left:(t-start)/span*100,width:(next-t)/span*100,state:st,title:formatTimelineTime(t)+" · "+(st==="up"?"доступен":restricted?"вероятное ограничение в РФ":st==="down"?"недоступен":"нет данных")+(point.latency_ms!=null?" · "+point.latency_ms+" мс":"")})}
      cursor=Math.max(cursor,next)
    });
    if(cursor<end)segments.push({left:(cursor-start)/span*100,width:(end-cursor)/span*100,state:"unknown",title:"Нет свежего измерения"});
    if(!segments.length)segments=[{left:0,width:100,state:"unknown",title:"Нет измерений за период"}];
    var currentState=state==="up"?"Доступен":state==="down"?(scope==="RUSSIA"&&isReachable((resource.external||{}).status)?"Вероятное ограничение в РФ":"Недоступен"):"Нет данных";
    var latency=latest&&latest.latency_ms!=null?latest.latency_ms:(scope==="RUSSIA"?(resource.domestic||{}).response_time_ms:(resource.external||{}).response_time_ms);
    var checked=latest?latest.timestamp:null,alert=!!resource.alerts_enabled;
    var marker=segments.map(function(seg){return '<i class="timeline-segment '+seg.state+'" style="left:'+Math.max(0,seg.left).toFixed(4)+'%;width:'+Math.max(0,seg.width).toFixed(4)+'%" title="'+esc(seg.title)+'"></i>'}).join("");
    var tickPx=Math.max(3.5,el.clientWidth/(S.streamMinutes*6));
    return '<article class="resource-timeline-row" data-resource="'+row.id+'"><div class="timeline-row-head"><button class="timeline-resource-open" data-open-resource="'+row.id+'" title="Открыть ресурс"><b>'+esc(row.name||row.target||"Ресурс")+'</b><span>'+esc(row.target||"")+'</span></button><span class="timeline-notification '+(alert?"enabled":"disabled")+'" title="'+(alert?"Уведомления включены":"Уведомления выключены")+'" aria-label="'+(alert?"Уведомления включены":"Уведомления выключены")+'">'+(alert?"✓":"○")+'</span></div><div class="timeline-track" role="img" aria-label="'+esc(row.name)+': '+esc(currentState)+'; шкала с делениями 10 секунд" style="--timeline-tick:'+tickPx+'px">'+marker+'</div><div class="timeline-axis"><span>'+formatTimelineTime(start)+'</span><span>10 секунд на деление</span><span>'+formatTimelineTime(end)+'</span></div><div class="timeline-details"><span class="timeline-state '+state+'"><i></i>'+esc(currentState)+'</span><span>Отклик: <b>'+esc(num(latency," мс"))+'</b></span><span>Последняя проверка: <b>'+esc(checked?ago(checked):"нет")+'</b></span>'+(latest&&latest.http_status?'<span>HTTP '+esc(latest.http_status)+'</span>':"")+'</div></article>'
  }).join("");
  qa("#"+containerId+" [data-open-resource]").forEach(function(b){b.onclick=function(){openDetail(Number(b.dataset.openResource))}})
}
function renderRealtime(){drawResourceTimeline("globalTimeline","globalTimelineStatus",S.realtime,"GLOBAL")}
function renderDomesticRealtime(){drawResourceTimeline("russiaTimeline","russiaTimelineStatus",S.realtimeDom,"RUSSIA")}
function renderEvents(){
  var el=q("#eventFeed"),rows=S.events||[];
  var important=rows.filter(function(ev){return ev.severity==="critical"||ev.severity==="warning"}).length;
  q("#eventSummary").textContent=important?important+" важных за период":"Критичных изменений нет";
  if(!rows.length){el.innerHTML=empty("Событий пока нет","Изменения состояния появятся здесь.");return}
  el.innerHTML=rows.slice(0,7).map(function(ev){
    var sev=ev.severity==="critical"?"critical":ev.severity==="warning"?"warning":"",label=sev==="critical"?"Критический":sev==="warning"?"Предупреждение":"Информация";
    var unread=ev.incident_id&&!ev.acknowledged_at;
    return '<div class="event-item '+(unread?"unread":"")+'" data-event-resource="'+(ev.resource_id||"")+'"><time class="event-time">'+shortTime(ev.time)+'</time><i class="event-dot '+sev+'"></i><div class="event-main"><b>'+esc(ev.title)+'</b><span>'+esc(ev.message||"")+'</span>'+(unread?'<button class="event-ack" data-ack="'+ev.incident_id+'">✓ Отметить прочитанным</button>':'')+'</div><span class="event-tag '+sev+'">'+label+'</span></div>'
  }).join("");
  qa("[data-event-resource]").forEach(function(row){row.onclick=function(e){if(e.target.closest("[data-ack]"))return;if(row.dataset.eventResource)openDetail(Number(row.dataset.eventResource))}});
  bindIncidentActions()
}

function resourceScopeGap(r){
  var ext=r&&r.external||{},dom=r&&r.domestic||{};
  var globalOk=isReachable(ext.status),ruUnavailable=isConfirmedUnavailable(dom.status);
  return (globalOk&&ruUnavailable)||r&&r.diagnosis==="LIKELY_RESTRICTION"?"Вероятное ограничение в РФ":"";
}
function russianResourceState(r){
  var ext=r&&r.external||{},dom=r&&r.domestic||{};
  var series=((S.realtimeDom&&S.realtimeDom.resources)||[]).find(function(item){return Number(item.id)===Number(r&&r.id)});
  var points=(series&&series.points||[]).filter(function(point){return point.state==="UP"||point.state==="DOWN"}).sort(function(a,b){return b.timestamp-a.timestamp});
  var chartFailure=!!(points.length&&Date.now()/1000-Number(points[0].timestamp)<1800&&points[0].state==="DOWN");
  var ruFailure=isConfirmedUnavailable(dom.status)||chartFailure;
  if(r&&r.diagnosis==="LIKELY_RESTRICTION")return {text:"Вероятное ограничение в РФ",className:"warn",status:dom.status||"UNKNOWN"};
  if(isReachable(dom.status))return {text:"Доступен из РФ",className:"ok",status:dom.status};
  if(ruFailure&&isReachable(ext.status))return {text:"Вероятное ограничение в РФ",className:"warn",status:dom.status||"HTTP_ERROR"};
  if(ruFailure&&!isReachable(ext.status))return {text:"Сбой ресурса · РФ отдельно не подтверждена",className:"bad",status:dom.status||"HTTP_ERROR"};
  if(isConfirmedUnavailable(ext.status))return {text:"Глобальная проверка: сбой · РФ неизвестна",className:"warn",status:dom.status||"UNKNOWN"};
  return {text:"Нет данных по РФ",className:"neutral",status:dom.status||"UNKNOWN"};
}
function resourceDisplayClass(r){
  var ext=(r.external||{}).status,cls=diagClass(r.diagnosis);
  if(cls==="bad"||cls==="warn")return cls;
  return ext?stClass(ext):"neutral"
}
function resourceDisplayText(r){
  var cls=diagClass(r.diagnosis),ext=(r.external||{}).status;
  if(cls==="bad"||cls==="warn")return diagText(r.diagnosis);
  return ext?stText(ext):diagText(r.diagnosis)
}
function resourceAttentionRank(r){
  var cls=resourceDisplayClass(r),latency=Number((r.external||{}).response_time_ms),slow=Number(r.slow_threshold_ms||1500);
  if(cls==="bad"||isConfirmedUnavailable((r.domestic||{}).status))return 0;
  if(cls==="warn"||(Number.isFinite(latency)&&latency>=slow))return 1;
  if(cls==="neutral")return 2;
  return 3
}

function probeInRegion(p,region){
  var lat=Number(p.lat),lon=Number(p.lon);
  if(region==="RU")return lat>=41&&lat<=82&&((lon>=19&&lon<=180)||(lon>=-180&&lon<=-169));
  if(region==="EU")return lat>=34&&lat<=72&&lon>=-25&&lon<=45;
  return true
}
function appendProbePoint(map,p){
  if(!map||!p)return;
  var x=(Number(p.lon)+180)/360*760,y=(90-Number(p.lat))/180*320;
  var circle=document.createElementNS("http://www.w3.org/2000/svg","circle");
  circle.setAttribute("cx",x);circle.setAttribute("cy",y);circle.setAttribute("r",p.online?"5":"4");
  circle.setAttribute("fill",p.online?"#42df9c":"#ff6174");circle.setAttribute("class","map-point");
  circle.setAttribute("tabindex","0");circle.setAttribute("role","img");circle.setAttribute("aria-label",p.name+" · "+(p.online?"онлайн":"нет связи"));
  var title=document.createElementNS("http://www.w3.org/2000/svg","title");title.textContent=p.name+" · "+(p.online?"онлайн":"нет связи");circle.appendChild(title);
  map.appendChild(circle)
}
function renderMap(){
  var probes=S.dashboard&&S.dashboard.probes||[],region=q("#mapRegion")?q("#mapRegion").value:"WORLD";
  var map=q("#mapPoints"),emptyEl=q("#mapEmpty");
  if(map)map.innerHTML="";
  var located=probes.filter(function(p){return Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))&&probeInRegion(p,region)});
  if(emptyEl)emptyEl.classList.toggle("hidden",!!located.length);
  var status=q("#mapStatus");
  if(status){
    var offline=located.filter(function(p){return !p.online}).length;
    status.className="map-status "+(!located.length?"neutral":offline?"bad":"ok");
    status.querySelector("span").textContent=!located.length?"Нет данных о состоянии точек":offline?("Проблемные точки: "+offline+" из "+located.length):"Все отображаемые точки онлайн"
  }
  if(!map||!located.length)return;
  located.forEach(function(p){appendProbePoint(map,p)})
}

function renderMapPage(){
  var probes=S.dashboard&&S.dashboard.probes||[],map=q("#mapPagePoints"),emptyEl=q("#mapPageEmpty");
  if(map)map.innerHTML="";
  var located=probes.filter(function(p){return Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))});
  if(emptyEl)emptyEl.classList.toggle("hidden",!!located.length);
  located.forEach(function(p){appendProbePoint(map,p)});
  renderProbeLegend()
}

function renderProbeLegend(){
  var el=q("#probeMapLegend");if(!el||!S.dashboard)return;
  var probes=S.dashboard.probes||[];
  el.innerHTML=probes.length?probes.map(function(p){return '<div class="probe-map-item '+(p.online?"":"offline")+'"><i></i><div><b>'+esc(p.name)+'</b><span>'+esc(p.scope)+(p.agent_version?' · агент '+esc(p.agent_version):'')+' · '+(p.online?"онлайн":"нет связи")+' · '+ago(p.last_seen_at)+'</span></div></div>'}).join(""):empty("Нет точек наблюдения","")
}

function renderOverviewTable(){
  var rows=S.dashboard.resources||[],el=q("#overviewResourceTable");
  if(!rows.length){el.innerHTML=empty("Нет ресурсов","Добавьте первую цель.");return}
  var ordered=rows.slice().sort(function(a,b){var rank=resourceAttentionRank(a)-resourceAttentionRank(b);return rank||String(a.name).localeCompare(String(b.name),"ru")});
  var matching=S.overviewResourceMode==="ISSUES"?ordered.filter(function(r){return resourceAttentionRank(r)<3}):ordered;
  var visible=matching.slice(0,8),issues=ordered.filter(function(r){return resourceAttentionRank(r)<3}).length;
  q("#overviewResourceSummary").textContent=S.overviewResourceMode==="ISSUES"?(issues?issues+" требуют внимания":"Проблем не обнаружено"):(issues?issues+" требуют внимания · проблемные показаны первыми":rows.length+" ресурсов · всё спокойно");
  if(!visible.length){el.innerHTML=empty("Всё спокойно","Сейчас нет ресурсов, требующих внимания.");return}
  el.innerHTML='<div class="table-head"><div>Ресурс</div><div>Статус</div><div>Отклик</div><div>Уведомления</div><div>DNS</div><div>TCP</div><div>TLS</div><div>HTTP</div><div></div></div>'+visible.map(function(r){
    var x=r.domestic||r.external||{},ruState=russianResourceState(r);
    return '<div class="table-row" data-resource="'+r.id+'" tabindex="0" aria-label="Открыть ресурс «'+esc(r.name)+'». '+esc(ruState.text)+'"><div class="table-resource with-logo">'+resourceIconHtml(r.target,r.name)+'<div><b>'+esc(r.name)+'</b><span>'+esc(r.target)+'</span><small class="table-resource-ru '+ruState.className+'"><i></i>'+esc(ruState.text)+'</small></div></div><div><span class="status-chip '+resourceDisplayClass(r)+'">'+esc(resourceDisplayText(r))+'</span></div><div>'+num(x.response_time_ms," мс")+'</div><div>'+(r.alerts_enabled?"✓ Включены":"○ Выключены")+'</div><div><i class="stage-dot '+stageState("DNS",r,x)+'"></i></div><div><i class="stage-dot '+stageState("TCP",r,x)+'"></i></div><div><i class="stage-dot '+stageState("TLS",r,x)+'"></i></div><div><i class="stage-dot '+stageState("HTTP",r,x)+'"></i></div><button type="button" class="row-more" data-row-more="'+r.id+'" aria-label="Открыть «'+esc(r.name)+'»">⋮</button></div>'
  }).join("");
  qa("#overviewResourceTable .table-row").forEach(function(row){
    row.onclick=function(e){if(e.target.closest("[data-row-more]"))return;openDetail(Number(row.dataset.resource))};
    row.onkeydown=function(e){if((e.key==="Enter"||e.key===" ")&&!e.target.closest("[data-row-more]")){e.preventDefault();openDetail(Number(row.dataset.resource))}}
  });
  qa("#overviewResourceTable [data-row-more]").forEach(function(button){button.onclick=function(e){e.stopPropagation();openDetail(Number(button.dataset.rowMore))}});
  hydrateResourceIcons()
}

function stageState(stage,r,x){
  if(stage==="DNS")return x.dns_ms!=null?"ok":x.status==="DNS_ERROR"?"bad":"neutral";
  if(stage==="TCP")return x.tcp_ms!=null?"ok":x.status==="TCP_ERROR"?"bad":"neutral";
  if(stage==="TLS")return r.target.indexOf("https://")!==0?"ok":x.tls_ms!=null?"ok":x.status==="TLS_ERROR"?"bad":"neutral";
  if(stage==="HTTP")return isReachable(x.status)?"ok":x.http_status!=null?"warn":x.status?"bad":"neutral";
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
    {name:"Транзит (RTT)",value:ext.tcp_ms!=null?num(ext.tcp_ms," мс"):"—",icon:"△",state:r.diagnosis==="LIKELY_RESTRICTION"?"bad":r.diagnosis==="EXTERNAL_PATH_ISSUE"?"warn":isReachable(ext.status)?"ok":"neutral"},
    {name:"Сервер "+r.name,value:ext.response_time_ms!=null?num(ext.response_time_ms," мс"):"—",icon:"▦",state:ext.status?stClass(ext.status):"neutral"},
    {name:"Приложение",value:isReachable(ext.status)?"OK":stText(ext.status),icon:"▣",state:ext.status?stClass(ext.status):"neutral"}
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
  var el=q("#searchResults"),input=q("#globalSearch");if(!el||!input)return;var raw=(value||"").trim(),v=raw.toLowerCase();
  S.searchIndex=-1;
  S.searchAddTarget=null;
  if(!v){hideSearch();el.innerHTML="";return}
  if(!S.dashboard){el.innerHTML=empty("Загружаем ресурсы","Поиск станет доступен через несколько секунд.");showSearch();return}
  var candidate=searchTargetCandidate(raw),candidateHost=candidate?targetMeta(candidate).host:"";
  var rows=(S.dashboard&&S.dashboard.resources||[]).filter(function(r){
    return r.name.toLowerCase().indexOf(v)>=0||r.target.toLowerCase().indexOf(v)>=0||String(r.resolved_ip||"").indexOf(v)>=0||(candidateHost&&targetMeta(r.target).host===candidateHost)
  }).slice(0,8);
  var html=rows.map(function(r,i){return '<button class="search-result" role="option" id="search-result-'+i+'" data-search-option data-search-id="'+r.id+'"><div><b>'+esc(r.name)+'</b><span>'+esc(r.target)+'</span></div><em>'+diagText(r.diagnosis)+'</em></button>'}).join("");
  if(candidate&&!rows.some(function(r){return targetMeta(r.target).host===candidateHost})){
    S.searchAddTarget=candidate;
    html+='<button class="search-result search-add-result" role="option" data-search-option data-search-add="1"><div><b>Добавить ресурс</b><span>'+esc(candidate)+'</span></div><em>Добавить</em></button>'
  }
  el.innerHTML=html||empty("Ничего не найдено","Введите название или адрес сайта.");
  showSearch();
  qa("#searchResults [data-search-option]").forEach(function(b,index){
    b.onclick=function(){
      if(b.dataset.searchAdd){
        var target=S.searchAddTarget;hideSearch();input.value="";
        openResourceCatalog(target);
        return
      }
      hideSearch();input.value="";openDetail(Number(b.dataset.searchId))
    };
    b.onkeydown=function(e){
      if(e.key==="ArrowDown"){e.preventDefault();var next=qa("#searchResults [data-search-option]")[index+1];if(next)next.focus()}
      if(e.key==="ArrowUp"){e.preventDefault();var prev=qa("#searchResults [data-search-option]")[index-1];if(prev)prev.focus();else input.focus()}
      if(e.key==="Escape"){e.preventDefault();hideSearch();input.focus()}
    }
  })
}

function searchTargetCandidate(value){
  var raw=String(value||"").trim();if(!raw||/\s/.test(raw))return null;
  var u=targetUrl(raw);if(!u)return null;
  var host=(u.hostname||"").toLowerCase();
  if(!host||(!host.includes(".")&&!/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)))return null;
  return raw
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
  q("#groupForm").reset();q("#groupKey").value=g?g.id:"";q("#groupDialogTitle").textContent=g?"Изменить группу":"Новая группа";q("#groupTitle").value=g?g.title:"";q("#groupColor").value=g&&g.color?g.color:"#3A8DFF";openDialog(q("#groupDialog"),"#groupTitle")
}
async function saveGroup(e){
  e.preventDefault();var key=q("#groupKey").value,title=q("#groupTitle").value.trim(),color=q("#groupColor").value,button=e.submitter||q("#groupForm [type=submit]");
  if(!title){toast("Введите название группы");q("#groupTitle").focus();return}
  try{await withBusy(button,"Сохраняем…",async function(){
    if(key)await api("/api/groups/"+encodeURIComponent(key),{method:"PATCH",body:JSON.stringify({title:title,color:color})},true);
    else await api("/api/groups",{method:"POST",body:JSON.stringify({title:title,color:color})},true);
    q("#groupDialog").close();await loadAll(true);toast(key?"Группа обновлена":"Группа создана")
  })}catch(err){toast(err.message)}
}
async function deleteGroup(key){
  var g=S.groups.find(function(x){return x.id===key});if(!g)return;
  var ok=await confirmAction({title:"Удалить группу?",message:"«"+g.title+"» будет удалена.",hint:"Ресурсы группы будут перенесены в «Пользовательские».",accept:"Удалить группу"});
  if(!ok)return;
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
  el.innerHTML='<div class="table-head"><div>Ресурс</div><div>Вывод</div><div>VPS</div><div>РФ</div><div>DNS</div><div>HTTP</div><div>Действия</div></div>'+rows.map(function(r){
    var ext=r.external||{},dom=r.domestic||{},gap=resourceScopeGap(r);
    return '<div class="table-row" data-resource="'+r.id+'" tabindex="0" aria-label="Открыть ресурс «'+esc(r.name)+'»"><div class="table-resource"><b>'+esc(r.name)+'</b><span>'+esc(r.target)+' · '+esc(groupTitle(r.group_name))+'</span>'+(gap?'<small class="resource-scope-gap">'+esc(gap)+'</small>':'')+'</div><div><span class="status-chip '+diagClass(r.diagnosis)+'">'+diagText(r.diagnosis)+'</span></div><div>'+stText(ext.status)+'</div><div class="'+russianResourceState(r).className+'">'+esc(russianResourceState(r).text)+'</div><div>'+num((dom.dns_ms!=null?dom.dns_ms:ext.dns_ms)," мс")+'</div><div>'+((dom.http_status!=null?dom.http_status:ext.http_status)||"—")+'</div><div><button class="btn tiny secondary row-check" data-check="'+r.id+'">Проверить</button></div></div>'
  }).join("");
  qa("#resourcesTable .table-row").forEach(function(row){
    row.onclick=function(e){if(e.target.closest(".row-check"))return;openDetail(Number(row.dataset.resource))};
    row.onkeydown=function(e){if((e.key==="Enter"||e.key===" ")&&!e.target.closest(".row-check")){e.preventDefault();openDetail(Number(row.dataset.resource))}}
  });
  qa(".row-check").forEach(function(b){b.onclick=function(e){e.stopPropagation();manualCheck(Number(b.dataset.check),b)}})
}

function incidentHtml(i){
  var severity=i.severity==="critical"?"critical":i.closed_at?"info":"";
  var read=!!i.acknowledged_at;
  return '<div class="incident-row '+severity+' '+(read?"read":"unread")+'" data-incident="'+i.id+'"><i></i><div><b>'+esc(i.resource_name||"Событие")+'</b><p>'+esc(i.message||"")+'</p></div><div class="incident-row-actions"><time>'+ago(i.opened_at||i.closed_at)+'</time>'+(read?'<span class="incident-read-mark">✓ Прочитано · инцидент открыт</span>':'<button class="incident-read-btn" data-ack="'+i.id+'">✓ Прочитать</button>')+'</div></div>'
}
async function acknowledgeIncident(id){
  try{await api("/api/incidents/"+id+"/ack",{method:"POST"},true);await loadAll(true);toast("Инцидент отмечен прочитанным")}catch(e){toast(e.message)}
}
async function acknowledgeAllIncidents(){
  var button=q("#ackAllIncidents");
  try{await withBusy(button,"Отмечаем…",async function(){var r=await api("/api/incidents/ack-all",{method:"POST"},true);await loadAll(true);toast("Отмечено прочитанными: "+r.acknowledged)})}catch(e){toast(e.message)}
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
  el.innerHTML=probes.length?probes.map(function(p){return '<article class="probe-page-card"><h2>'+esc(p.name)+'</h2><p>'+esc(p.scope)+(p.agent_version?' · агент '+esc(p.agent_version):'')+' · '+(p.online?"онлайн":"нет связи")+'</p><div class="probe-page-meta"><div><span>Последняя связь</span><b>'+ago(p.last_seen_at)+'</b></div><div><span>Возраст данных</span><b>'+(p.age_seconds==null?"—":duration(p.age_seconds))+'</b></div></div></article>'}).join(""):empty("Точки наблюдения не подключены","")
  renderProbeLegend()
}

function notifyIncidentTransitions(incidents){
  var storageKey="netweather_notified_incident_transitions",seen=[];
  try{seen=JSON.parse(localStorage.getItem(storageKey)||"[]");if(!Array.isArray(seen))seen=[]}catch(_){seen=[]}
  var known=new Set(seen),transitions=[];
  (incidents||[]).forEach(function(i){
    if(i.opened_at)transitions.push({key:String(i.id)+":open",time:Number(i.opened_at),incident:i,closed:false});
    if(i.closed_at)transitions.push({key:String(i.id)+":closed",time:Number(i.closed_at),incident:i,closed:true});
  });
  transitions.sort(function(a,b){return a.time-b.time});
  var bootstrap=!S.incidentNoticesInitialized&&seen.length===0;
  transitions.forEach(function(t){
    if(known.has(t.key))return;
    known.add(t.key);
    if(["DOWN","RUSSIA_DOWN"].indexOf(String(t.incident.kind||""))<0)return;
    if(!bootstrap&&"Notification" in window&&Notification.permission==="granted"){
      var russian=t.incident.kind==="RUSSIA_DOWN";
      var title=t.closed?(russian?"Ограничение в РФ снято":"Ресурс снова доступен"):(russian?"Вероятное ограничение в РФ":"Ресурс недоступен");
      try{new Notification(title,{body:t.incident.resource_name+" · "+(t.closed?(t.incident.message||"Проверка снова успешна"):t.incident.message),tag:"netweather-"+t.key,renotify:false})}catch(_){ }
    }
  });
  S.incidentNoticesInitialized=true;
  try{localStorage.setItem(storageKey,JSON.stringify(Array.from(known).slice(-300)))}catch(_){ }
}

function renderNotifications(){
  var b=q("#browserNotifyState"),w=q("#notifyWebhookState"),button=q("#enableNotifications");if(!b||!w||!S.system)return;
  var supported="Notification" in window,permission=supported?Notification.permission:"unsupported";
  b.textContent=!supported?"Браузер не поддерживает Notification API.":permission==="granted"?"Разрешение выдано.":permission==="denied"?"Уведомления заблокированы браузером.":"Разрешение ещё не запрашивалось.";
  if(button){
    button.disabled=!supported||permission==="denied"||permission==="granted";
    button.textContent=permission==="granted"?"Уведомления включены":permission==="denied"?"Заблокировано браузером":!supported?"Не поддерживается":"Включить уведомления браузера";
    button.title=permission==="denied"?"Разрешение можно изменить в настройках браузера":""
  }
  w.textContent=S.system.webhook_configured?"Server webhook настроен.":"Webhook не настроен."
}

function renderDiagnostics(){
  if(!S.dashboard)return;var rows=S.dashboard.resources||[],sel=q("#diagResource"),old=String(S.diagId||sel.value||"");
  sel.innerHTML=rows.map(function(r){return '<option value="'+r.id+'">'+esc(r.name)+' · '+esc(r.target)+'</option>'}).join("");
  if(old&&rows.some(function(r){return String(r.id)===old}))sel.value=old;else if(rows.length){sel.value=String(rows[0].id);S.diagId=rows[0].id}
  var r=resourceById(sel.value);if(r)showDiagnostic(r)
}
function showDiagnostic(r){
  S.diagId=r.id;var ext=r.external||{},dom=r.domestic||{},x=r.domestic||r.external||{},fallback=r.external||{};
  var diagnosis=r.diagnosis||r.diagnosis_code||((isReachable(ext.status)||isReachable(dom.status))?"AVAILABLE":"UNKNOWN");
  q("#diagSummary").innerHTML='<div class="diag-summary-card"><div><span>Вывод</span><b>'+diagText(diagnosis)+'</b></div><div><span>VPS</span><b>'+stText(ext.status)+' · '+num(ext.response_time_ms," мс")+'</b></div><div><span>РФ</span><b>'+stText(dom.status)+' · '+num(dom.response_time_ms," мс")+'</b></div><div><span>IP</span><b>'+esc((x.resolved_ip||fallback.resolved_ip)||"—")+'</b></div><div><span>HTTP</span><b>'+((x.http_status||fallback.http_status)||"—")+'</b></div></div>';
  setStage("Dns",x.dns_ms!=null?x.dns_ms:fallback.dns_ms,x.status!=="DNS_ERROR");
  setStage("Tcp",x.tcp_ms!=null?x.tcp_ms:fallback.tcp_ms,x.tcp_ms!=null||fallback.tcp_ms!=null);
  setStage("Tls",x.tls_ms!=null?x.tls_ms:fallback.tls_ms,r.target.indexOf("https://")!==0||x.tls_ms!=null||fallback.tls_ms!=null);
  setStage("Http",x.http_ms!=null?x.http_ms:(fallback.http_ms!=null?fallback.http_ms:fallback.response_time_ms),isReachable(x.status||fallback.status))
}

function setStage(n,v,good){var e=q("#stage"+n);e.querySelector("b").textContent=v==null?"—":Math.round(v)+" мс";e.className="diag-step "+(v==null?"":good?"good":"bad")}

function drawSpark(canvas,values,color){
  if(!canvas)return;var r=canvas.getBoundingClientRect(),w=Math.max(45,r.width||70),h=Math.max(20,r.height||30),dpr=Math.min(2,devicePixelRatio||1);canvas.width=w*dpr;canvas.height=h*dpr;var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!values||values.length<2)return;var min=Math.min.apply(null,values),max=Math.max.apply(null,values);if(max===min)max=min+1;ctx.strokeStyle=color;ctx.lineWidth=1.35;ctx.beginPath();values.forEach(function(v,i){var x=i/(values.length-1)*(w-2)+1,y=h-2-(v-min)/(max-min)*(h-5);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke()
}
function drawBars(canvas,values,color){
  if(!canvas)return;var r=canvas.getBoundingClientRect(),w=Math.max(45,r.width||70),h=Math.max(20,r.height||30),dpr=Math.min(2,devicePixelRatio||1);canvas.width=w*dpr;canvas.height=h*dpr;var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!values||!values.length)return;var max=Math.max(1,Math.max.apply(null,values)),bw=w/values.length*.55;ctx.fillStyle=color;values.forEach(function(v,i){var bh=(v/max)*(h-4),x=(i+.2)*w/values.length,y=h-bh-1;ctx.fillRect(x,y,bw,bh)})
}

function renderSettings(){
  if(!S.system||!S.dashboard)return;
  q("#tokenState").textContent=S.authRequired?(S.owner?"Режим владельца активен. Управляющие действия разрешены.":"Публичный режим: просмотр и базовое добавление ресурсов доступны без входа."):"Локальная разработка: авторизация отключена.";
  q("#alertSystemState").textContent=S.system.webhook_configured?"Server webhook настроен.":"Webhook не настроен; инциденты сохраняются в журнале.";
  q("#securityState").textContent=S.system.private_targets_allowed?"Private targets разрешены.":"Private/loopback/link-local цели заблокированы.";
  var vals=[["Версия",S.system.version],["Uptime",duration(S.system.uptime_seconds)],["Ресурсы",S.system.resources],["Проверки",S.system.checks],["Инциденты",S.system.active_incidents],["Traceroute",S.system.traceroute_available?"готов":"нет"],["База",S.system.database],["Scheduler",S.system.scheduler_enabled?"включён":"выключен"]];
  q("#systemInfo").innerHTML=vals.map(function(v){return '<div class="system-kv"><span>'+esc(v[0])+'</span><b>'+esc(v[1])+'</b></div>'}).join("");
  q("#probeSettings").innerHTML=(S.dashboard.probes||[]).map(function(p){return '<div class="probe-setting"><span>'+esc(p.scope)+'</span><b>'+esc(p.name)+'</b><span>'+(p.online?"онлайн":"нет связи")+' · '+ago(p.last_seen_at)+'</span></div>'}).join("")||empty("Нет probes","");
  renderNotifications()
}

async function manualCheck(id,button){
  try{await withBusy(button,"Проверяем…",async function(){
    toast("Проверяем ресурс…");
    var r=await api("/api/resources/"+id+"/check",{method:"POST"},true);
    await loadAll(true);
    toast(r.scheduled_domestic?"VPS проверен · проверка РФ поставлена в очередь":"Проверка VPS завершена")
  })}catch(e){toast(e.message)}
}
async function trace(id,domestic,button){
  if(domestic)return traceDomestic(id,button);
  try{await withBusy(button,"Traceroute…",async function(){
    q("#traceOutput").innerHTML=empty("Traceroute","Выполняем маршрут с VPS…");
    var r=await api("/api/resources/"+id+"/trace",{method:"POST"},true);
    q("#traceMeta").textContent=r.host+" → "+r.resolved_ip+" · DNS "+r.dns_ms+" мс";
    q("#traceOutput").innerHTML=r.hops.length?r.hops.map(function(h){return '<div class="trace-hop"><span>'+h.hop+'</span><span>'+esc(h.ip||"*")+'</span><span>'+(h.latency_ms==null?"*":h.latency_ms+" ms")+'</span></div>'}).join(""):'<pre class="trace-raw">'+esc(r.raw)+'</pre>';
    openView("diagnostics");q("#diagResource").value=String(id);S.diagId=id
  })}catch(e){q("#traceOutput").innerHTML=empty("Traceroute не выполнен",e.message);toast(e.message)}
}
async function browserTraceProbe(target){
  var url=targetUrl(target);if(!url)throw new Error("Некорректный адрес ресурса");
  if(url.protocol!=="https:")throw new Error("Браузерная проверка доступна только для HTTPS-ресурсов");
  var samples=[],errors=[];
  for(var i=0;i<2;i++){
    var started=performance.now();
    try{
      await window.fetch(url.href,{method:"GET",mode:"no-cors",cache:"no-store",redirect:"follow",credentials:"omit"});
      samples.push(Math.round(performance.now()-started));
    }catch(e){errors.push(String(e&&e.message||e||"network error"))}
  }
  if(!samples.length)throw new Error(errors[0]||"Браузер не получил ответ");
  samples.sort(function(a,b){return a-b});
  return {url:url.href,ok:true,samples:samples,median_ms:samples[Math.floor(samples.length/2)],online:navigator.onLine!==false};
}
async function traceDomestic(id,button){
  var resource=resourceById(id);if(!resource)return;
  try{await withBusy(button,"Проверяем из браузера…",async function(){
    openView("diagnostics");
    q("#traceMeta").textContent="Браузер пользователя · его сеть";
    q("#traceOutput").innerHTML=empty("Проверка из браузера","Запрашиваем ресурс напрямую из текущего браузера…");
    var result=await browserTraceProbe(resource.target);
    q("#traceOutput").innerHTML='<div class="browser-trace-result"><b>Ресурс доступен из браузера</b><span>'+esc(resource.target)+'</span><span>Измерения: '+result.samples.join(" / ")+' мс · медиана '+result.median_ms+' мс</span><small>Это проверка из вашей сети. Браузеры не раскрывают hop-by-hop маршрут, поэтому IP-узлы трассировки здесь недоступны.</small></div>';
  })}catch(e){q("#traceOutput").innerHTML=empty("Проверка из браузера не выполнена",e.message);toast(e.message)}
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
async function openResourceCatalog(initialTarget){
  initialTarget=typeof initialTarget==="string"?initialTarget:"";
  S.catalogSelected={};S.customCatalogMatch=null;S.customAutoCatalogKey=null;
  q("#catalogSearch").value="";q("#customResourceTarget").value=initialTarget;q("#customResourceName").value="";q("#customResourceName").dataset.autoSuggested="1";
  q("#customCatalogMatch").className="custom-match hidden";q("#customCatalogMatch").innerHTML="";
  fillCustomGroupOptions();q("#resourceCatalogGroups").innerHTML='<div class="catalog-loading">Загружаем каталог…</div>';
  openDialog(q("#resourceDialog"),initialTarget?"#customResourceTarget":"#catalogSearch");
  try{await loadResourceCatalog(true);renderCatalog("")}catch(e){q("#resourceCatalogGroups").innerHTML=empty("Каталог не загружен",e.message);toast(e.message)}
  updateCatalogSelection();if(initialTarget)await inspectCustomResource()
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
  var button=e.submitter||q("#addCatalogResources");
  if(button&&button.dataset.busy==="1")return;
  var keys=Object.keys(S.catalogSelected),customTarget=q("#customResourceTarget").value.trim(),messages=[],added=0,existing=0;
  try{
    await withBusy(button,"Добавляем…",async function(){
      if(S.customCatalogMatch&&S.customCatalogMatch.matched&&!S.customCatalogMatch.already_added&&keys.indexOf(S.customCatalogMatch.resource.key)<0)keys.push(S.customCatalogMatch.resource.key);
      if(keys.length){
        var batch=await api("/api/resource-catalog/add",{method:"POST",body:JSON.stringify({resource_keys:keys})});
        added+=batch.added.length;existing+=batch.existing.length
      }
      if(customTarget&&!S.customCatalogMatch){
        var customName=q("#customResourceName").value.trim();
        if(!customName){var meta=await getTargetMetadata(customTarget);customName=meta.name||targetMeta(customTarget).name||customTarget}
        var custom=await api("/api/resources",{method:"POST",body:JSON.stringify({
          name:customName,target:customTarget,group_name:q("#customResourceGroup").value||"CUSTOM",
          interval_seconds:60,expected_status_min:200,expected_status_max:399,slow_threshold_ms:1500,failure_threshold:2,enabled:true,alerts_enabled:true
        })});
        if(custom.used_catalog){
          var matchedName=custom.catalog_match&&custom.catalog_match.name||customName;
          messages.push("«"+matchedName+"» найден в каталоге — использован каталоговый вариант")
        }
        if(custom.created)added++;else existing++
      }else if(customTarget&&S.customCatalogMatch&&S.customCatalogMatch.already_added){
        existing++;messages.push("«"+S.customCatalogMatch.resource.name+"» уже находится в мониторинге")
      }
      q("#resourceDialog").close();
      S.catalog=null;await loadAll(true);
      var parts=[];if(added)parts.push("добавлено: "+added);if(existing)parts.push("уже было: "+existing);
      toast((parts.length?parts.join(" · "):"Изменений нет")+(messages.length?" · "+messages.join("; "):""))
    })
  }catch(err){toast(err.message)}
}

function formPayload(){return{name:q("#resourceName").value.trim(),target:q("#resourceTarget").value.trim(),group_name:q("#resourceGroup").value.trim()||"CUSTOM",interval_seconds:Number(q("#resourceInterval").value),expected_status_min:Number(q("#statusMin").value),expected_status_max:Number(q("#statusMax").value),slow_threshold_ms:Number(q("#slowThreshold").value),failure_threshold:Number(q("#failureThreshold").value),enabled:q("#resourceEnabled").checked,alerts_enabled:q("#alertsEnabled").checked}}
function openResourceForm(r){
  if(!r){openResourceCatalog();return}
  q("#resourceForm").reset();q("#resourceId").value=r.id;q("#resourceDialogTitle").textContent="Изменить ресурс";
  q("#resourceName").value=r.name;q("#resourceName").dataset.autoSuggested="0";q("#resourceTarget").value=r.target;q("#resourceGroup").value=r.group_name;
  q("#resourceInterval").value=String(r.interval_seconds||60);q("#statusMin").value=r.expected_status_min||200;q("#statusMax").value=r.expected_status_max||399;
  q("#slowThreshold").value=r.slow_threshold_ms||1500;q("#failureThreshold").value=r.failure_threshold||2;q("#resourceEnabled").checked=!!r.enabled;q("#alertsEnabled").checked=!!r.alerts_enabled;
  syncResourceIdentity(false);openDialog(q("#resourceEditDialog"),"#resourceName")
}
async function saveResource(e){
  e.preventDefault();var id=q("#resourceId").value,p=formPayload(),button=e.submitter||q("#resourceForm [type=submit]");
  if(!id||!p.name||!p.target){toast("Заполните название и адрес");return}
  try{await withBusy(button,"Сохраняем…",async function(){
    await api("/api/resources/"+id,{method:"PATCH",body:JSON.stringify(p)},true);
    q("#resourceEditDialog").close();S.catalog=null;await loadAll(true);toast("Ресурс обновлён")
  })}catch(err){toast(err.message)}
}

function renderResourceCheckReport(checks){
  var scopes=[{key:"GLOBAL",name:"Глобальный"},{key:"RUSSIA",name:"Россия"},{key:"USER",name:"Устройство"}],rows=(checks||[]).slice();
  return '<div class="resource-report">'+scopes.map(function(scope){
    var items=rows.filter(function(c){var key=String(c.probe_scope||"").toUpperCase();return key===scope.key||(scope.key==="RUSSIA"&&key==="DOMESTIC")||(scope.key==="GLOBAL"&&key==="EXTERNAL")}),up=items.filter(function(c){return isReachable(c.status)}).length,unknown=items.filter(function(c){return !c.status||["UNKNOWN","NO_DATA"].indexOf(String(c.status).toUpperCase())>=0}).length,down=items.length-up-unknown,lat=items.map(function(c){return Number(c.response_time_ms)}).filter(Number.isFinite),avg=lat.length?Math.round(lat.reduce(function(a,b){return a+b},0)/lat.length):null;
    return '<div class="resource-report-row"><b>'+scope.name+'</b><span>'+items.length+' проверок</span><span class="up">Доступно: '+up+'</span><span class="down">Недоступно: '+down+'</span>'+(unknown?'<span>Без данных: '+unknown+'</span>':"")+'<span>Отклик: '+esc(num(avg," мс"))+'</span></div>'
  }).join("")+'</div>'
}
async function openDetail(id){
  try{
    var d=await api("/api/resources/"+id),r=normalizeResourceShape(d.resource),checks=d.checks||[];S.detailId=id;q("#detailTitle").textContent=r.name;
    q("#detailBody").innerHTML='<div class="detail-notify-state">'+(r.alerts_enabled?"✓ Уведомления о падении включены":"○ Уведомления о падении выключены")+'</div><div class="detail-top"><div class="detail-kv"><span>Вывод</span><b>'+diagText(r.diagnosis)+'</b></div><div class="detail-kv"><span>Глобальный контур</span><b>'+stText(r.external&&r.external.status)+'</b></div><div class="detail-kv"><span>РФ</span><b>'+esc(russianResourceState(r).text)+'</b></div><div class="detail-kv"><span>Отклик</span><b>'+num((r.domestic||r.external||{}).response_time_ms," мс")+'</b></div></div><div class="detail-section"><h3>'+esc(r.target)+'</h3><div class="detail-kv"><span>Пояснение</span><b>'+esc(r.diagnosis_text||"—")+'</b></div></div><div class="detail-section"><h3>Отчёт ресурса · последние проверки</h3>'+renderResourceCheckReport(checks)+'<div class="check-list">'+(checks.length?checks.map(function(c){return '<div class="check-row"><div>'+fmt(c.checked_at)+'</div><div>'+esc(c.probe_scope||"")+' · '+stText(c.status)+'</div><div>'+esc(c.message||"")+'</div><div>'+num(c.response_time_ms," мс")+'</div></div>'}).join(""):empty("Проверок нет",""))+'</div></div>';
    openDialog(q("#detailDialog"),"#detailCheck")
  }catch(e){toast(e.message)}
}
async function deleteResource(){var r=resourceById(S.detailId);if(!r)return;var ok=await confirmAction({title:"Удалить ресурс?",message:"«"+r.name+"» будет удалён из мониторинга.",hint:"История проверок этого ресурса также будет удалена.",accept:"Удалить ресурс"});if(!ok)return;try{await withBusy(q("#deleteResource"),"Удаляем…",async function(){await api("/api/resources/"+r.id,{method:"DELETE"},true);q("#detailDialog").close();await loadAll(true);toast("Ресурс удалён")})}catch(e){toast(e.message)}}

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
}

function setup(){
  hydrateChromeIcons();
  setupDialogs();
  localStorage.removeItem("netweather_token");
  var shortcut=q(".search-wrap kbd");if(shortcut)shortcut.textContent=/Mac|iPhone|iPad/.test(navigator.platform)?"⌘ K":"Ctrl K";
  updateClock();setInterval(updateClock,1000);
  qa(".side-item[data-view]").forEach(function(b){b.onclick=function(){openView(b.dataset.view)}});
  qa("[data-view-jump]").forEach(function(b){b.onclick=function(){openView(b.dataset.viewJump)}});
  q("#globalSearch").oninput=function(){renderSearch(this.value)};
  q("#globalSearch").addEventListener("keydown",handleSearchKeydown);
  var identityTimer=null;
  q("#resourceTarget").addEventListener("input",function(){clearTimeout(identityTimer);identityTimer=setTimeout(function(){syncResourceIdentity(false)},180)});
  q("#resourceName").addEventListener("input",function(){this.dataset.autoSuggested="0"});
  document.addEventListener("keydown",function(e){
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();var input=q("#globalSearch");input.focus();input.select();return}
    if(e.key==="Escape"){
      var search=q("#searchResults");if(search&&!search.classList.contains("hidden")){hideSearch();return}
    }
  });
  document.addEventListener("click",function(e){if(!e.target.closest(".search-wrap"))hideSearch()});
  q("#themeToggle").onclick=function(){var light=document.documentElement.dataset.theme==="light";document.documentElement.dataset.theme=light?"dark":"light";localStorage.setItem("netweather_theme",light?"dark":"light");renderAll()};
  document.documentElement.dataset.theme=localStorage.getItem("netweather_theme")||"dark";
  q("#openAlerts").onclick=function(){openView("alerts")};
  q("#ackAllIncidents").onclick=acknowledgeAllIncidents;
  q("#worldButton").onclick=function(){openView("map")};
  q("#manageGroups").onclick=function(){openView("groups")};
  q("#customizeOverview").onclick=openDashboardPreferences;
  q("#dashboardPreferencesForm").onsubmit=submitDashboardPreferences;
  q("#ownerLoginForm").onsubmit=submitOwnerLogin;
  q("#ownerAuthAction").onclick=ownerAuthAction;
  q("#resetDashboardPreferences").onclick=resetDashboardPreferences;
  [q("#sidebarAddResource"),q("#openAddResource"),q("#overviewAddResource")].forEach(function(b){if(b)b.onclick=function(){openResourceCatalog()}});
  q("#resourceCatalogForm").onsubmit=submitResourceCatalog;
  q("#catalogSearch").oninput=function(){renderCatalog(this.value)};
  var customTimer=null;
  q("#customResourceTarget").oninput=function(){clearTimeout(customTimer);customTimer=setTimeout(inspectCustomResource,260);updateCatalogSelection()};
  q("#customResourceName").oninput=function(){this.dataset.autoSuggested="0"};
  q("#resourceForm").onsubmit=saveResource;q("#groupForm").onsubmit=saveGroup;q("#openAddGroup").onclick=function(){openGroupForm(null)};
  qa(".modal-close").forEach(function(b){b.onclick=function(){closeDialog(b.closest("dialog"))}});
  qa('.seg[data-minutes]').forEach(function(b){b.onclick=function(){qa('.seg[data-minutes]').forEach(function(x){x.classList.toggle("active",Number(x.dataset.minutes)===Number(b.dataset.minutes))});S.streamMinutes=Number(b.dataset.minutes);loadAll(true)}});
  qa("[data-overview-resource-mode]").forEach(function(b){b.onclick=function(){S.overviewResourceMode=b.dataset.overviewResourceMode;qa("[data-overview-resource-mode]").forEach(function(x){x.classList.toggle("active",x===b)});renderOverviewTable()}});
  q("#checkAllResources").onclick=async function(){var button=this;try{await withBusy(button,"Проверяем…",async function(){var result=await api("/api/check-all",{method:"POST"},true);await loadAll(true);toast("Проверка завершена: "+result.checked+" ресурсов · доступно "+result.ok+" · проблемы "+result.failed)})}catch(e){toast(e.message)}};
  q("#mapZoomIn").onclick=function(){S.mapScale=Math.min(2,S.mapScale+.15);q("#worldMapSvg").style.transform="scale("+S.mapScale+")"};
  q("#mapZoomOut").onclick=function(){S.mapScale=Math.max(.8,S.mapScale-.15);q("#worldMapSvg").style.transform="scale("+S.mapScale+")"};
  q("#mapRegion").onchange=function(){renderMap()};
  q("#faultResourceSelect").onchange=function(){S.faultId=Number(this.value);renderFaultPanel()};
  q("#searchInput").oninput=renderResources;q("#groupFilter").onchange=renderResources;q("#statusFilter").onchange=renderResources;
  q("#diagResource").onchange=function(){S.diagId=Number(this.value);var r=resourceById(this.value);if(r)showDiagnostic(r)};
  q("#diagCheck").onclick=function(){var id=Number(q("#diagResource").value);if(id)manualCheck(id,this)};q("#diagTrace").onclick=function(){var id=Number(q("#diagResource").value);if(id)trace(id,false,this)};q("#diagTraceDomestic").onclick=function(){var id=Number(q("#diagResource").value);if(id)trace(id,true,this)};
  q("#enableNotifications").onclick=async function(){var button=this;if(!("Notification" in window)){toast("Браузер не поддерживает уведомления");return}await withBusy(button,"Запрашиваем…",async function(){var p=await Notification.requestPermission();renderNotifications();toast(p==="granted"?"Уведомления включены":"Разрешение не выдано")})};
  q("#deleteResource").onclick=deleteResource;q("#editResource").onclick=function(){var r=resourceById(S.detailId);q("#detailDialog").close();if(r)openResourceForm(r)};q("#detailCheck").onclick=function(){var b=this,id=S.detailId;q("#detailDialog").close();manualCheck(id,b)};q("#detailTrace").onclick=function(){var b=this,id=S.detailId;q("#detailDialog").close();trace(id,false,b)};
  window.addEventListener("resize",function(){renderRealtime();renderDomesticRealtime();renderOverviewTable();applyDashboardPreferences()});
  loadAll(false);S.poll=setInterval(function(){if(!S.loading)loadAll(true,Math.min(60,S.streamMinutes))},10000)
}
document.addEventListener("DOMContentLoaded",setup);
})();
