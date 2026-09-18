(function(){
"use strict";

var COLORS=["#ff6174","#58c7ff","#78a5ff","#42df9c","#ffd34f","#9a65ff","#56e1d0","#ff8bc7","#b8e35d","#7bb6ff"];
var S={
  dashboard:null,incidents:[],system:null,groups:[],realtime:null,events:[],
  historyExt:[],historyDom:[],streamMinutes:60,detailId:null,diagId:null,
  faultId:null,view:"overview",poll:null,streamMeta:null,authRequired:false,
  owner:true,mapScale:1,metaCache:{}
};

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
function resourceIconHtml(target,name){
  var m=targetMeta(target),fallback=esc((name||m.name||"?").slice(0,2).toUpperCase());
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

  renderRealtime();renderEvents();renderResourceCards();renderMap();renderOverviewTable();renderFaultPanel()
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

function drawAvailabilityChart(canvas,series){
  if(!canvas)return;
  var rect=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1);
  canvas.width=Math.max(420,Math.floor(rect.width*dpr));canvas.height=Math.max(180,Math.floor(rect.height*dpr));
  var ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);
  var w=rect.width,h=rect.height,p={l:46,r:10,t:12,b:27};ctx.clearRect(0,0,w,h);
  if(!series.length){S.streamMeta=null;return}
  var points=[];series.forEach(function(row){row.points.forEach(function(x){if(x.availability!=null)points.push(Number(x.availability))})});
  if(!points.length){S.streamMeta=null;return}
  var minVal=Math.min.apply(null,points),min=minVal>=90?90:minVal>=75?75:0,max=100;
  var ticks=[];for(var ti=0;ti<=4;ti++)ticks.push(max-(max-min)*ti/4);
  ctx.font="10px system-ui";ctx.fillStyle=getCss("--muted");ctx.strokeStyle=getCss("--line-soft");ctx.lineWidth=1;
  ticks.forEach(function(v){var y=p.t+(h-p.t-p.b)*(1-(v-min)/(max-min));ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();ctx.fillText((Math.round(v*10)/10).toString().replace(".0","")+"%",3,y+3)});
  var allTs=[];series.forEach(function(row){row.points.forEach(function(x){allTs.push(x.timestamp)})});
  var tmin=Math.min.apply(null,allTs),tmax=Math.max.apply(null,allTs);if(tmax===tmin)tmax=tmin+1;
  series.slice(0,7).forEach(function(row,si){ctx.strokeStyle=COLORS[si%COLORS.length];ctx.lineWidth=1.6;ctx.beginPath();var started=false;row.points.forEach(function(pt){if(pt.availability==null)return;var x=p.l+(w-p.l-p.r)*(pt.timestamp-tmin)/(tmax-tmin),y=p.t+(h-p.t-p.b)*(1-(Number(pt.availability)-min)/(max-min));if(!started){ctx.moveTo(x,y);started=true}else ctx.lineTo(x,y)});ctx.stroke()});
  for(var j=0;j<=6;j++){var ts=tmin+(tmax-tmin)*j/6,x=p.l+(w-p.l-p.r)*j/6;ctx.fillStyle=getCss("--muted");ctx.fillText(shortTime(ts),Math.min(x,w-36),h-7)}
  S.streamMeta={series:series,tmin:tmin,tmax:tmax,min:min,max:max,p:p,w:w,h:h,key:"availability"}
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
  var current=S.dashboard.resources||[],cards=rows.slice(0,6);
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
  var visible=rows.slice(0,6);
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

function formPayload(){return{name:q("#resourceName").value.trim(),target:q("#resourceTarget").value.trim(),group_name:q("#resourceGroup").value.trim()||"CUSTOM",interval_seconds:Number(q("#resourceInterval").value),expected_status_min:Number(q("#statusMin").value),expected_status_max:Number(q("#statusMax").value),slow_threshold_ms:Number(q("#slowThreshold").value),failure_threshold:Number(q("#failureThreshold").value),enabled:q("#resourceEnabled").checked,alerts_enabled:q("#alertsEnabled").checked}}
function openResourceForm(r){q("#resourceForm").reset();q("#resourceId").value=r?r.id:"";q("#resourceDialogLabel").textContent=r?"РЕДАКТИРОВАНИЕ":"НОВАЯ ЦЕЛЬ";q("#resourceDialogTitle").textContent=r?"Изменить ресурс":"Добавить ресурс";q("#resourceName").value=r?r.name:"";q("#resourceName").dataset.autoSuggested=r?"0":"1";q("#resourceTarget").value=r?r.target:"";q("#resourceGroup").value=r?r.group_name:"CUSTOM";q("#resourceInterval").value=String(r?r.interval_seconds:60);q("#statusMin").value=r?r.expected_status_min:200;q("#statusMax").value=r?r.expected_status_max:399;q("#slowThreshold").value=r?r.slow_threshold_ms:1500;q("#failureThreshold").value=r?r.failure_threshold:2;q("#resourceEnabled").checked=r?!!r.enabled:true;q("#alertsEnabled").checked=r?!!r.alerts_enabled:true;syncResourceIdentity(false);q("#resourceDialog").showModal()}
async function saveResource(e){e.preventDefault();var id=q("#resourceId").value,p=formPayload();if(!p.name||!p.target){toast("Заполните название и адрес");return}try{if(id)await api("/api/resources/"+id,{method:"PATCH",body:JSON.stringify(p)},true);else await api("/api/resources",{method:"POST",body:JSON.stringify(p)},true);q("#resourceDialog").close();await loadAll(true);toast(id?"Ресурс обновлён":"Ресурс добавлен")}catch(err){toast(err.message)}}

async function openDetail(id){
  try{var d=await api("/api/resources/"+id),r=d.resource;S.detailId=id;q("#detailTitle").textContent=r.name;q("#detailBody").innerHTML='<div class="detail-top"><div class="detail-kv"><span>Вывод</span><b>'+diagText(r.diagnosis)+'</b></div><div class="detail-kv"><span>VPS</span><b>'+stText(r.external&&r.external.status)+'</b></div><div class="detail-kv"><span>РФ</span><b>'+stText(r.domestic&&r.domestic.status)+'</b></div><div class="detail-kv"><span>Отклик</span><b>'+num((r.domestic||r.external||{}).response_time_ms," мс")+'</b></div></div><div class="detail-section"><h3>'+esc(r.target)+'</h3><div class="detail-kv"><span>Пояснение</span><b>'+esc(r.diagnosis_text||"—")+'</b></div></div><div class="detail-section"><h3>Последние проверки</h3><div class="check-list">'+(d.checks.length?d.checks.map(function(c){return '<div class="check-row"><div>'+fmt(c.checked_at)+'</div><div>'+esc(c.probe_scope||"")+' · '+stText(c.status)+'</div><div>'+esc(c.message||"")+'</div><div>'+c.response_time_ms+' мс</div></div>'}).join(""):empty("Проверок нет",""))+'</div></div>';q("#detailDialog").showModal()}catch(e){toast(e.message)}
}
async function deleteResource(){var r=resourceById(S.detailId);if(!r)return;if(!confirm("Удалить ресурс «"+r.name+"» и его историю?"))return;try{await api("/api/resources/"+r.id,{method:"DELETE"},true);q("#detailDialog").close();await loadAll(true);toast("Ресурс удалён")}catch(e){toast(e.message)}}

function setup(){
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
  [q("#sidebarAddResource"),q("#openAddResource"),q("#overviewAddResource")].forEach(function(b){if(b)b.onclick=function(){openResourceForm(null)}});
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
  window.addEventListener("resize",function(){renderRealtime();renderHistory();renderResourceCards();renderOverviewTable()});
  loadAll(false);S.poll=setInterval(function(){loadAll(true)},15000)
}
document.addEventListener("DOMContentLoaded",setup);
})();