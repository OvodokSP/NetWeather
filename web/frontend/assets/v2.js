
(function(){
"use strict";
var S={dashboard:null,history:[],incidents:[],system:null,groups:[],view:"overview",detailId:null,diagId:null,poll:null,knownIncidentIds:new Set(),firstIncidentLoad:true};
function q(s){return document.querySelector(s)} function qa(s){return Array.prototype.slice.call(document.querySelectorAll(s))}
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"})[c]})}
function token(){return localStorage.getItem("netweather_token")||""}
function auth(){return token()?{"Authorization":"Bearer "+token()}:{}}
function toast(m){var e=q("#toast");e.textContent=m;e.classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(function(){e.classList.remove("show")},3000)}
function fmt(ts){if(!ts)return "—";return new Date(ts*1000).toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"})}
function ago(ts){if(!ts)return "—";var d=Math.max(0,Math.floor(Date.now()/1000-ts));if(d<60)return d+" сек назад";if(d<3600)return Math.floor(d/60)+" мин назад";if(d<86400)return Math.floor(d/3600)+" ч назад";return Math.floor(d/86400)+" дн назад"}
function duration(sec){sec=Number(sec||0);if(sec<60)return sec+" сек";if(sec<3600)return Math.floor(sec/60)+" мин";if(sec<86400)return Math.floor(sec/3600)+" ч";return Math.floor(sec/86400)+" дн"}
function stClass(s){return s==="OK"?"ok":s==="TIMEOUT"?"warn":s?"bad":"neutral"}
function stText(s){return({OK:"Работает",DNS_ERROR:"DNS ошибка",TCP_ERROR:"TCP ошибка",TLS_ERROR:"TLS ошибка",HTTP_ERROR:"HTTP ошибка",TIMEOUT:"Таймаут",BLOCKED_TARGET:"Заблокировано",UNKNOWN_ERROR:"Ошибка"})[s]||"Нет данных"}
function groupTitle(v){var found=S.groups.find(function(g){return g.id===v});if(found)return found.title;return({"RUSSIAN":"Российские","INTERNATIONAL":"Международные","MESSENGERS":"Мессенджеры и соцсети","INFRASTRUCTURE":"Инфраструктура","CUSTOM":"Пользовательские"})[v]||v}
function mode(mode){return({NORMAL:["Нормальный доступ","Сеть доступна, существенных проблем не обнаружено.","ok"],PARTIAL_DEGRADATION:["Частичная деградация","Часть контролируемых ресурсов недоступна или отвечает нестабильно.","warn"],RESTRICTED_ACCESS:["Вероятны ограничения","Российский сегмент доступен заметно лучше международного.","warn"],NO_INTERNET:["Критическая недоступность","Большинство проверенных ресурсов недоступно.","bad"],INITIALIZING:["Инициализация","Ресурсы добавлены. NetWeather собирает первые измерения.","neutral"],NO_DATA:["Нет целей","Добавьте хотя бы один ресурс для начала мониторинга.","neutral"]})[mode]||["Нет данных","Ожидание данных.","neutral"]}
async function api(path,opt,secure){opt=opt||{};if(secure&&!token()){q("#tokenInput").value="";q("#tokenDialog").showModal();throw new Error("Сначала укажите API-токен")}var headers={"Content-Type":"application/json"};Object.assign(headers,opt.headers||{});if(secure)Object.assign(headers,auth());var res=await fetch(path,Object.assign({},opt,{headers:headers}));if(!res.ok){var m="HTTP "+res.status;try{var j=await res.json();m=j.detail||m}catch(_e){}if(res.status===401)toast("Неверный или отсутствующий API-токен");throw new Error(m)}if(res.status===204)return null;return res.json()}
function empty(title,text){return '<div class="nw-empty"><div><b>'+esc(title)+'</b><span>'+esc(text||"")+'</span></div></div>'}
function resourceById(id){return(S.dashboard&&S.dashboard.resources||[]).find(function(r){return r.id===Number(id)})}
function incidentById(id){return S.incidents.find(function(x){return x.id===Number(id)})}

function openView(name){S.view=name;qa(".view").forEach(function(v){v.classList.toggle("active",v.id==="view-"+name)});qa(".nav-item").forEach(function(b){b.classList.toggle("active",b.dataset.view===name)});q("#pageTitle").textContent=({overview:"Обзор",resources:"Ресурсы",alerts:"Тревоги",diagnostics:"Диагностика",history:"История",settings:"Управление"})[name]||"NetWeather";if(name==="history")drawHistory();if(name==="diagnostics")renderDiagnostics()}
function setApiState(ok){q("#apiStatus").textContent=ok?"онлайн":"нет связи";q(".status-dot").style.background=ok?"var(--nw-good)":"var(--nw-bad)"}

async function loadAll(silent){
  try{
    var hours=Number(q("#historyRange").value||24);
    var a=await Promise.all([api("/api/dashboard"),api("/api/history?hours="+hours),api("/api/incidents?limit=100"),api("/api/system"),api("/api/groups")]);
    S.dashboard=a[0];S.history=a[1];S.incidents=a[2];S.system=a[3];S.groups=a[4];setApiState(true);renderAll();notifyNewIncidents();
  }catch(e){setApiState(false);if(!silent)toast("Ошибка загрузки: "+e.message)}
}
function renderAll(){renderOverview();renderResources();renderIncidents();renderSettings();renderDiagnostics();drawHistory();q("#versionLabel").textContent=S.system?"· "+S.system.version:""}

function renderOverview(){
  if(!S.dashboard)return;var s=S.dashboard.summary||{},rows=S.dashboard.resources||[],mi=mode(s.mode);
  q("#availability").textContent=s.checked?Number(s.availability_index||0):"—";
  var pct=s.checked?Number(s.availability_index||0):0;q("#gauge").style.background="conic-gradient(var(--accent) "+(pct*3.6)+"deg,rgba(128,150,175,.12) 0deg)";
  q("#modePill").textContent=mi[0];q("#modePill").className="mode-pill "+mi[2];q("#modeTitle").textContent=mi[0];q("#modeText").textContent=mi[1];q("#lastUpdated").textContent=fmt(s.last_updated);
  q("#availableCount").textContent=s.available||0;q("#availableHint").textContent="из "+(s.checked||0)+" проверенных · "+(s.total||0)+" целей";
  q("#problemCount").textContent=s.problematic||0;q("#avgLatency").textContent=s.avg_latency_ms==null?"—":s.avg_latency_ms+" мс";
  q("#activeIncidentCount").textContent=s.active_incidents||0;q("#incidentHint").textContent=(s.active_incidents||0)?"требуют внимания":"нет активных";
  renderGroups(s.groups||{});renderOverviewResources(rows);renderOverviewIncidents((S.dashboard.incidents||[]).filter(function(i){return !i.closed_at}).slice(0,6));
  var badge=q("#alertBadge"),n=(S.dashboard.incidents||[]).filter(function(i){return !i.closed_at}).length;badge.textContent=n;badge.classList.toggle("hidden",!n);
  drawChart("availabilityChart",S.history,"availability",true,"availabilityEmpty");
}
function renderGroups(groups){
  var el=q("#groupList"),keys=Object.keys(groups);if(!keys.length){el.innerHTML=empty("Групп пока нет","Они появятся после добавления ресурсов.");return}
  el.innerHTML=keys.map(function(k){var g=groups[k],p=g.availability==null?0:g.availability;return '<div class="nw-group"><div class="nw-group-head"><b>'+esc(groupTitle(k))+'</b><span>'+(g.checked||0)+'/'+g.total+' проверено · '+(g.availability==null?"—":g.availability+"%")+'</span></div><div class="nw-progress"><i style="width:'+p+'%"></i></div></div>'}).join("");
}
function resourceMini(r){
  return '<div class="nw-resource" data-resource="'+r.id+'"><div class="nw-resource-main"><b>'+esc(r.name)+'</b><span>'+esc(r.target)+'</span></div><div><span class="status-pill '+stClass(r.status)+'">'+stText(r.status)+'</span></div><div class="nw-stage"><b>'+(r.dns_ms==null?"—":r.dns_ms+" мс")+'</b>DNS</div><div class="nw-stage"><b>'+(r.tcp_ms==null?"—":r.tcp_ms+" мс")+'</b>TCP</div><div class="nw-stage"><b>'+(r.tls_ms==null?"—":r.tls_ms+" мс")+'</b>TLS</div><div class="latency">'+(r.response_time_ms==null?"—":r.response_time_ms+" мс")+'</div></div>'
}
function renderOverviewResources(rows){var el=q("#overviewResources");if(!rows.length){el.innerHTML=empty("Нет ресурсов","Перейдите в «Ресурсы» и добавьте первую цель.");return}el.innerHTML=rows.slice(0,8).map(resourceMini).join("");bindResourceClicks(el)}
function incidentHtml(i,active){
  var cls=i.severity==="critical"?"critical":i.closed_at?"info":"warning";var kind=({DOWN:"Недоступность",SLOW:"Медленный ответ",TLS_EXPIRY:"Срок TLS"})[i.kind]||i.kind;
  return '<div class="nw-incident '+cls+'"><i class="incident-mark"></i><div><b>'+esc(i.resource_name)+' · '+esc(kind)+'</b><p>'+esc(i.message)+'</p></div><time>'+ago(i.opened_at)+'</time>'+(active&&!i.acknowledged_at?'<div class="incident-actions"><button class="mini-btn ack-btn" data-ack="'+i.id+'" title="Подтвердить">✓</button></div>':"")+'</div>'
}
function renderOverviewIncidents(rows){var el=q("#overviewIncidents");el.innerHTML=rows.length?rows.map(function(i){return incidentHtml(i,false)}).join(""):empty("Всё спокойно","Активных тревог нет.")}

function filteredResources(){
  var rows=(S.dashboard&&S.dashboard.resources||[]).slice(),search=(q("#searchInput").value||"").toLowerCase(),group=q("#groupFilter").value,status=q("#statusFilter").value;
  return rows.filter(function(r){var match=!search||r.name.toLowerCase().indexOf(search)>=0||r.target.toLowerCase().indexOf(search)>=0||String(r.resolved_ip||"").indexOf(search)>=0;if(group!=="ALL"&&r.group_name!==group)match=false;if(status==="OK"&&r.status!=="OK")match=false;if(status==="PROBLEM"&&(!r.status||r.status==="OK"))match=false;if(status==="PENDING"&&r.status)match=false;return match})
}
function renderResources(){
  var all=S.dashboard&&S.dashboard.resources||[],sel=q("#groupFilter"),old=sel.value||"ALL",groups=Array.from(new Set(all.map(function(r){return r.group_name})));
  sel.innerHTML='<option value="ALL">Все группы</option>'+groups.map(function(g){return '<option value="'+esc(g)+'">'+esc(groupTitle(g))+'</option>'}).join("");if(Array.from(sel.options).some(function(o){return o.value===old}))sel.value=old;
  q("#groupOptions").innerHTML=(S.groups||[]).map(function(g){return '<option value="'+esc(g.id)+'">'+esc(g.title)+'</option>'}).join("");
  var el=q("#resourcesTable"),rows=filteredResources();if(!rows.length){el.innerHTML=empty(all.length?"Ничего не найдено":"Список пуст",all.length?"Измените фильтры.":"Добавьте ресурс — проверки начнутся автоматически.");return}
  el.innerHTML='<div class="nw-table-head"><div>Ресурс</div><div>Статус</div><div>DNS</div><div>TCP</div><div>TLS</div><div>HTTP</div><div></div></div>'+rows.map(function(r){
    return '<div class="nw-table-row" data-resource="'+r.id+'"><div class="nw-table-resource"><b>'+esc(r.name)+'</b><span>'+esc(r.target)+' · '+esc(groupTitle(r.group_name))+(r.resolved_ip?" · "+esc(r.resolved_ip):"")+'</span></div><div><span class="status-pill '+stClass(r.status)+'">'+stText(r.status)+'</span></div><div>'+(r.dns_ms==null?"—":r.dns_ms+" мс")+'</div><div>'+(r.tcp_ms==null?"—":r.tcp_ms+" мс")+'</div><div>'+(r.tls_ms==null?"—":r.tls_ms+" мс")+'</div><div>'+(r.http_status==null?"—":r.http_status)+'</div><div class="nw-actions"><button class="mini-btn row-check" data-check="'+r.id+'" title="Проверить">↻</button><button class="mini-btn row-edit" data-edit="'+r.id+'" title="Изменить">✎</button></div></div>'
  }).join("");bindResourceClicks(el);qa(".row-check").forEach(function(b){b.onclick=function(e){e.stopPropagation();manualCheck(Number(b.dataset.check))}});qa(".row-edit").forEach(function(b){b.onclick=function(e){e.stopPropagation();openResourceForm(resourceById(b.dataset.edit))}})
}
function bindResourceClicks(root){Array.prototype.slice.call(root.querySelectorAll("[data-resource]")).forEach(function(e){e.onclick=function(){openDetail(Number(e.dataset.resource))}})}

function renderIncidents(){
  var active=S.incidents.filter(function(i){return !i.closed_at}),history=S.incidents.filter(function(i){return i.closed_at});
  q("#activeIncidents").innerHTML=active.length?active.map(function(i){return incidentHtml(i,true)}).join(""):empty("Нет активных тревог","NetWeather сообщит здесь о недоступности, задержке и истекающих TLS-сертификатах.");
  q("#incidentHistory").innerHTML=history.length?history.map(function(i){return incidentHtml(i,false)}).join(""):empty("История пуста","Закрытые инциденты появятся здесь.");
  qa(".ack-btn").forEach(function(b){b.onclick=function(){ackIncident(Number(b.dataset.ack))}})
}
function renderSettings(){
  q("#tokenState").textContent=token()?"Токен сохранён в этом браузере.":"Токен не указан — изменения и диагностика защищены.";
  if(!S.system)return;var x=S.system;q("#alertSystemState").textContent=x.webhook_configured?"Webhook настроен на сервере.":"Webhook не задан. Тревоги сохраняются в журнале, браузерные уведомления можно включить на странице «Тревоги».";
  q("#securityState").textContent=x.private_targets_allowed?"ВНИМАНИЕ: private targets разрешены.":"Private targets заблокированы; redirect probe не следует во внутреннюю сеть.";
  var values=[["Версия",x.version],["Uptime",duration(x.uptime_seconds)],["Ресурсы",x.resources],["Проверки",x.checks],["Инциденты",x.active_incidents],["Traceroute",x.traceroute_available?"готов":"нет"],["База",x.database],["Scheduler",x.scheduler_enabled?"включён":"выключен"]];
  q("#systemInfo").innerHTML=values.map(function(v){return '<div class="system-kv"><span>'+esc(v[0])+'</span><b>'+esc(v[1])+'</b></div>'}).join("")
}

function renderDiagnostics(){
  var rows=S.dashboard&&S.dashboard.resources||[],sel=q("#diagResource"),old=String(S.diagId||sel.value||"");sel.innerHTML=rows.map(function(r){return '<option value="'+r.id+'">'+esc(r.name)+' · '+esc(r.target)+'</option>'}).join("");
  if(old&&Array.from(sel.options).some(function(o){return o.value===old}))sel.value=old;else if(rows.length){sel.value=String(rows[0].id);S.diagId=rows[0].id}
  if(!rows.length){q("#diagSummary").innerHTML=empty("Нет целей","Добавьте ресурс.");resetStages();return}
  var r=resourceById(sel.value);if(r)showDiagnostic(r)
}
function resetStages(){["Dns","Tcp","Tls","Http"].forEach(function(k){var e=q("#stage"+k);e.className="diag-step";e.querySelector("b").textContent="—"})}
function showDiagnostic(r){
  S.diagId=r.id;q("#diagResource").value=String(r.id);q("#diagSummary").innerHTML='<div class="diag-summary-card"><div><span>Ресурс</span><b>'+esc(r.name)+'</b></div><div><span>IP</span><b>'+esc(r.resolved_ip||"—")+'</b></div><div><span>Полный отклик</span><b>'+(r.response_time_ms==null?"—":r.response_time_ms+" мс")+'</b></div><div><span>HTTP</span><b>'+(r.http_status==null?"—":r.http_status)+'</b></div><div><span>TLS</span><b>'+(r.tls_days_left==null?"—":r.tls_days_left+" дн")+'</b></div></div>';
  setStage("Dns",r.dns_ms,r.status!=="DNS_ERROR"&&r.status!=="BLOCKED_TARGET");setStage("Tcp",r.tcp_ms,r.tcp_ms!=null);setStage("Tls",r.tls_ms,r.target.indexOf("https://")!==0||r.tls_ms!=null);setStage("Http",r.http_ms,r.status==="OK")
}
function setStage(name,val,good){var e=q("#stage"+name);e.querySelector("b").textContent=val==null?"—":val+" мс";e.className="diag-step "+(val==null?"":good?"good":"bad")}

function drawHistory(){
  var h=S.history||[];drawChart("historyChart",h,"availability",true,"historyEmpty");drawChart("latencyChart",h,"avg_latency_ms",false,"latencyEmpty");
  if(h.length){q("#historyAvailability").textContent=Math.round(h.reduce(function(a,b){return a+b.availability},0)/h.length)+"%";q("#historyLatency").textContent=Math.round(h.reduce(function(a,b){return a+b.avg_latency_ms},0)/h.length)+" мс"}else{q("#historyAvailability").textContent="—";q("#historyLatency").textContent="—"}
  var rows=h.slice(-20).reverse();q("#historyTable").innerHTML=rows.length?'<div class="history-row head"><div>Время</div><div>Доступность</div><div>Задержка</div><div>Проверок</div></div>'+rows.map(function(x){return '<div class="history-row"><div>'+fmt(x.timestamp)+'</div><b>'+x.availability+'%</b><div>'+x.avg_latency_ms+' мс</div><div>'+x.checks+'</div></div>'}).join(""):empty("Нет истории","Первые интервалы появятся после запуска мониторинга.")
}
function drawChart(id,data,key,percent,emptyId){
  var c=q("#"+id),emptyEl=q("#"+emptyId);if(!c)return;var rect=c.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1);c.width=Math.max(300,Math.floor(rect.width*dpr));c.height=Math.max(180,Math.floor(rect.height*dpr));var ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);var w=rect.width,h=rect.height,p={l:42,r:12,t:15,b:28};ctx.clearRect(0,0,w,h);if(emptyEl)emptyEl.classList.toggle("hidden",!!data.length);if(!data.length)return;
  var vals=data.map(function(x){return Number(x[key]||0)}),min=percent?0:Math.min.apply(null,vals),max=percent?100:Math.max.apply(null,vals);if(max===min)max=min+1;
  var css=getComputedStyle(document.documentElement),muted=css.getPropertyValue("--nw-muted").trim()||"#8196ad",line=css.getPropertyValue("--accent").trim()||"#5ecbff";ctx.font="10px system-ui";ctx.fillStyle=muted;ctx.strokeStyle="rgba(130,150,175,.13)";ctx.lineWidth=1;
  for(var i=0;i<=4;i++){var y=p.t+(h-p.t-p.b)*i/4;ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();var v=max-(max-min)*i/4;ctx.fillText(percent?Math.round(v)+"%":Math.round(v)+"",4,y+3)}
  ctx.strokeStyle=line;ctx.lineWidth=2;ctx.beginPath();data.forEach(function(x,i){var xx=p.l+(w-p.l-p.r)*(data.length===1?0.5:i/(data.length-1)),yy=p.t+(h-p.t-p.b)*(1-(Number(x[key]||0)-min)/(max-min));if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy)});ctx.stroke();
  var step=Math.max(1,Math.floor(data.length/6));data.forEach(function(x,i){if(i%step&&i!==data.length-1)return;var xx=p.l+(w-p.l-p.r)*(data.length===1?0.5:i/(data.length-1));ctx.fillStyle=muted;ctx.fillText(new Date(x.timestamp*1000).toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"}),Math.min(xx,w-45),h-7)})
}

async function manualCheck(id){
  try{toast("Проверяем ресурс…");await api("/api/resources/"+id+"/check",{method:"POST"},true);await loadAll(true);toast("Проверка завершена");var r=resourceById(id);if(S.view==="diagnostics"&&r)showDiagnostic(r)}catch(e){toast(e.message)}
}
async function checkAll(){
  var b=q("#checkAll"),old=b.textContent;b.disabled=true;b.textContent="Проверяем…";try{var r=await api("/api/check-all",{method:"POST"},true);await loadAll(true);toast("Проверено: "+r.checked+" · OK: "+r.ok+" · ошибок: "+r.failed)}catch(e){toast(e.message)}finally{b.disabled=false;b.textContent=old}
}
async function trace(id){
  try{q("#traceOutput").innerHTML=empty("Traceroute","Выполняем маршрут с VPS…");var r=await api("/api/resources/"+id+"/trace",{method:"POST"},true);q("#traceMeta").textContent=r.host+" → "+r.resolved_ip+" · DNS "+r.dns_ms+" мс";q("#traceOutput").innerHTML=r.hops.length?r.hops.map(function(h){return '<div class="trace-hop"><span>'+h.hop+'</span><span>'+esc(h.ip||"*")+'</span><span>'+(h.latency_ms==null?"*":h.latency_ms+" ms")+'</span></div>'}).join(""):'<pre class="trace-raw">'+esc(r.raw)+'</pre>';openView("diagnostics");q("#diagResource").value=String(id);S.diagId=id}catch(e){q("#traceOutput").innerHTML=empty("Traceroute не выполнен",e.message);toast(e.message)}
}
async function ackIncident(id){try{await api("/api/incidents/"+id+"/ack",{method:"POST"},true);await loadAll(true);toast("Тревога подтверждена")}catch(e){toast(e.message)}}

function formPayload(){
  return{name:q("#resourceName").value.trim(),target:q("#resourceTarget").value.trim(),group_name:q("#resourceGroup").value.trim()||"CUSTOM",interval_seconds:Number(q("#resourceInterval").value),expected_status_min:Number(q("#statusMin").value),expected_status_max:Number(q("#statusMax").value),slow_threshold_ms:Number(q("#slowThreshold").value),failure_threshold:Number(q("#failureThreshold").value),enabled:q("#resourceEnabled").checked,alerts_enabled:q("#alertsEnabled").checked}
}
function openResourceForm(r){
  q("#resourceForm").reset();q("#resourceId").value=r?r.id:"";q("#resourceDialogLabel").textContent=r?"РЕДАКТИРОВАНИЕ":"НОВАЯ ЦЕЛЬ";q("#resourceDialogTitle").textContent=r?"Изменить ресурс":"Добавить ресурс";
  q("#resourceName").value=r?r.name:"";q("#resourceTarget").value=r?r.target:"";q("#resourceGroup").value=r?r.group_name:"CUSTOM";q("#resourceInterval").value=String(r?r.interval_seconds:60);q("#statusMin").value=r?r.expected_status_min:200;q("#statusMax").value=r?r.expected_status_max:399;q("#slowThreshold").value=r?r.slow_threshold_ms:1500;q("#failureThreshold").value=r?r.failure_threshold:2;q("#resourceEnabled").checked=r?!!r.enabled:true;q("#alertsEnabled").checked=r?!!r.alerts_enabled:true;q("#resourceDialog").showModal()
}
async function saveResource(e){
  e.preventDefault();var id=q("#resourceId").value,p=formPayload();if(!p.name||!p.target){toast("Заполните название и адрес");return}if(p.expected_status_min>p.expected_status_max){toast("Минимальный HTTP-код больше максимального");return}
  try{if(id)await api("/api/resources/"+id,{method:"PATCH",body:JSON.stringify(p)},true);else await api("/api/resources",{method:"POST",body:JSON.stringify(p)},true);q("#resourceDialog").close();await loadAll(true);toast(id?"Ресурс обновлён":"Ресурс добавлен")}catch(err){toast(err.message)}
}
async function openDetail(id){
  try{var d=await api("/api/resources/"+id),r=d.resource;S.detailId=id;q("#detailTitle").textContent=r.name;q("#detailBody").innerHTML='<div class="detail-top"><div class="detail-kv"><span>Статус</span><b>'+stText(r.status)+'</b></div><div class="detail-kv"><span>IP</span><b>'+esc(r.resolved_ip||"—")+'</b></div><div class="detail-kv"><span>Отклик</span><b>'+(r.response_time_ms==null?"—":r.response_time_ms+" мс")+'</b></div><div class="detail-kv"><span>TLS</span><b>'+(r.tls_days_left==null?"—":r.tls_days_left+" дн")+'</b></div></div><div class="detail-section"><h4>'+esc(r.target)+'</h4><div class="detail-kv"><span>Последнее сообщение</span><b>'+esc(r.message||"—")+'</b></div></div><div class="detail-section"><h4>Последние проверки</h4><div class="check-list">'+(d.checks.length?d.checks.map(function(c){return '<div class="check-row"><div>'+fmt(c.checked_at)+'</div><div><span class="status-pill '+stClass(c.status)+'">'+stText(c.status)+'</span></div><div>'+esc(c.message||"")+'</div><div>'+c.response_time_ms+' мс</div></div>'}).join(""):empty("Проверок ещё нет",""))+'</div></div>';q("#detailDialog").showModal()}catch(e){toast(e.message)}
}
async function deleteResource(){var r=resourceById(S.detailId);if(!r)return;if(!confirm("Удалить ресурс «"+r.name+"» и его историю?"))return;try{await api("/api/resources/"+r.id,{method:"DELETE"},true);q("#detailDialog").close();await loadAll(true);toast("Ресурс удалён")}catch(e){toast(e.message)}}

function notifyNewIncidents(){
  var active=S.incidents.filter(function(i){return !i.closed_at});if(S.firstIncidentLoad){active.forEach(function(i){S.knownIncidentIds.add(i.id)});S.firstIncidentLoad=false;return}
  active.forEach(function(i){if(!S.knownIncidentIds.has(i.id)){S.knownIncidentIds.add(i.id);if("Notification" in window&&Notification.permission==="granted")new Notification("NetWeather: "+i.resource_name,{body:i.message})}})
}
function setup(){
  qa(".nav-item").forEach(function(b){b.onclick=function(){openView(b.dataset.view)}});qa("[data-go]").forEach(function(b){b.onclick=function(){openView(b.dataset.go)}});
  q("#themeToggle").onclick=function(){var light=document.documentElement.dataset.theme==="light";document.documentElement.dataset.theme=light?"dark":"light";localStorage.setItem("netweather_theme",light?"dark":"light");renderAll()};
  document.documentElement.dataset.theme=localStorage.getItem("netweather_theme")||"dark";if(token()){q("#openToken").textContent="API-токен ✓";q("#openToken").classList.add("token-ok")}
  [q("#openToken"),q("#openToken2")].forEach(function(b){b.onclick=function(){q("#tokenInput").value=token();q("#tokenDialog").showModal()}});
  q("#tokenForm").onsubmit=async function(e){e.preventDefault();var t=q("#tokenInput").value.trim();if(!t){toast("Введите API-токен");return}localStorage.setItem("netweather_token",t);try{await api("/api/auth/verify",{},true);q("#tokenDialog").close();renderSettings();q("#openToken").textContent="API-токен ✓";q("#openToken").classList.add("token-ok");toast("API-токен проверен и сохранён")}catch(err){localStorage.removeItem("netweather_token");toast("Токен не принят: "+err.message)}};
  q("#clearToken").onclick=function(){localStorage.removeItem("netweather_token");q("#tokenInput").value="";q("#openToken").textContent="API-токен";q("#openToken").classList.remove("token-ok");renderSettings();toast("Токен удалён")};
  qa(".modal-close").forEach(function(b){b.onclick=function(){b.closest("dialog").close()}});
  q("#openAddResource").onclick=function(){openResourceForm(null)};q("#resourceForm").onsubmit=saveResource;
  q("#searchInput").oninput=renderResources;q("#groupFilter").onchange=renderResources;q("#statusFilter").onchange=renderResources;
  q("#checkAll").onclick=checkAll;q("#historyRange").onchange=function(){loadAll(true)};
  q("#diagResource").onchange=function(){S.diagId=Number(this.value);var r=resourceById(this.value);if(r)showDiagnostic(r)};
  q("#diagCheck").onclick=function(){var id=Number(q("#diagResource").value);if(id)manualCheck(id)};q("#diagTrace").onclick=function(){var id=Number(q("#diagResource").value);if(id)trace(id)};
  q("#enableNotifications").onclick=async function(){if(!("Notification" in window)){toast("Браузер не поддерживает уведомления");return}var p=await Notification.requestPermission();toast(p==="granted"?"Уведомления включены":"Разрешение не выдано")};
  q("#deleteResource").onclick=deleteResource;q("#editResource").onclick=function(){var r=resourceById(S.detailId);q("#detailDialog").close();if(r)openResourceForm(r)};q("#detailCheck").onclick=function(){q("#detailDialog").close();manualCheck(S.detailId)};q("#detailTrace").onclick=function(){q("#detailDialog").close();trace(S.detailId)};
  window.addEventListener("resize",function(){if(S.history)drawHistory()});
  loadAll(false);S.poll=setInterval(function(){loadAll(true)},15000)
}
document.addEventListener("DOMContentLoaded",setup);
})();