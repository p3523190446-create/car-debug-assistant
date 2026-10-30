const $=id=>document.getElementById(id);
const names={demo:'示例演示',live:'本机真实接口',import:'导入快照'};
var replayActive=false;
let mode='demo',scenario='line-stale',snapshot=null,report=null,lastRead=0,busy=false;
let history=[];try{const saved=JSON.parse(localStorage.getItem('car-debug-v1')||'[]');if(Array.isArray(saved))history=saved.filter(x=>x&&typeof x.text==='string'&&Object.hasOwn(names,x.source)&&Number.isFinite(x.time)).slice(-200)}catch{}
const previous={};
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n}
async function api(path,body){const res=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'读取失败');return data}
function event(text,source=mode){history.push({time:Date.now(),source,text});history=history.slice(-200);try{localStorage.setItem('car-debug-v1',JSON.stringify(history))}catch{$('error').textContent='浏览器本机记录未保存，请导出记录。';$('error').hidden=false}paintHistory()}
function paintHistory(){const list=$('timeline');list.replaceChildren();for(const x of history.slice(-12).reverse()){const row=el('li');row.append(el('time',new Date(x.time).toLocaleTimeString('zh-CN',{hour12:false})),el('span',names[x.source]),el('strong',x.text));list.append(row)}}
function readableEvidence(text){
  return text.replace(/line.age_ms = ([0-9.]+) ms/g,(_,n)=>`巡线读数距上次更新：${Number(n)/1000}秒`)
    .replace(/link_age_ms = ([0-9.]+) ms/g,(_,n)=>`连接距上次更新：${Number(n)/1000}秒`)
    .replace(/有效条件：小于1500 ms/g,'检查阈值：小于1.5秒')
    .replace(/有效条件：小于3000 ms/g,'检查阈值：小于3秒')
    .replace(/capabilities.drive_control/g,'遥控接口可用').replace(/line.valid/g,'巡线数据有效')
    .replace(/line.age_ms/g,'巡线更新时间').replace(/link_age_ms/g,'连接更新时间')
    .replace(/connected/g,'小车连接状态').replace(/digital_mask/g,'数字状态标记').replace(/raw =/g,'八路读数：')
    .replace(/None/g,'未提供').replace(/true/g,'是').replace(/false/g,'否')
    .replace(/由本人/g,'').replace(/原控制台/g,'小车调试程序').replace(/串口连接/g,'连接线');
}
function paint(r,recordEvents=true){report=r;lastRead=Date.now();$('headline').textContent=r.title;$('statusLabel').textContent={issue:'发现待排查状态',unknown:'存在未确认状态',checked:'当前快照检查完成',notice:'需要核对接口能力'}[r.status];$('statusIcon').textContent={issue:'!',unknown:'?',checked:'✓',notice:'i'}[r.status];$('statusIcon').className='result-icon '+r.status;$('scope').textContent='根据本次数据给出检查建议，实际车辆状态需要结合设备核对。';$('sourceTitle').textContent=names[r.source];$('sourceNote').textContent={demo:'无需连接小车的模拟设备数据，用于体验检查与恢复流程。',live:'仅读取本机现有控制台的状态接口，本次结果对应刚取得的快照。',import:'以下结论仅对应导入快照，不代表车辆当前在线。'}[r.source];const checks=$('checks');checks.replaceChildren();for(const f of r.findings){const d=el('details',undefined,'check');d.open=f.level==='issue';const s=el('summary');s.append(el('span',f.title,'check-title'),el('span',{ok:'有效',issue:'待排查',notice:'能力说明',unknown:'未确认'}[f.level],'badge '+f.level));d.append(s,el('div',f.evidence.map(readableEvidence).join('\n'),'evidence'),el('p',readableEvidence(f.explanation)));const technical=el('details');technical.append(el('summary','查看原始字段（技术信息）'),el('div',f.evidence.join('\n'),'evidence'));d.append(technical);const steps=el('ol');f.steps.forEach(t=>steps.append(el('li',readableEvidence(t))));d.append(steps);checks.append(d)}if(recordEvents){const before=previous[r.source]||[];let pending=[...new Set([...before,...r.issue_codes])];if(before.length){for(const domain of ['link','line']){const had=before.some(x=>x.startsWith(domain+'_'));const recovered=r.findings.some(f=>f.code===domain+'_ok');if(had&&recovered){event((domain==='link'?'主控通信':'巡线数据')+'恢复：新快照已通过对应检查',r.source);pending=pending.filter(x=>!x.startsWith(domain+'_'))}}}previous[r.source]=pending;event(r.title,r.source);}document.querySelectorAll('[data-scenario]').forEach(n=>n.setAttribute('aria-pressed',String(r.source==='demo'&&n.dataset.scenario===scenario)));$('answer').textContent='已更新快照。选择问题查看对应证据。';updateAge()}
function updateAge(){if(!lastRead)return;const seconds=Math.floor((Date.now()-lastRead)/1000);$('age').textContent=seconds<10?seconds+' 秒前取得快照':seconds+' 秒前的旧快照';}
async function run(action){if(busy)return;busy=true;$('error').hidden=true;document.querySelectorAll('button').forEach(n=>n.disabled=true);try{await action()}catch(e){report=null;lastRead=0;$('sourceTitle').textContent=names[mode];$('sourceNote').textContent='本次没有取得可用状态，等待重新读取。';$('scope').textContent='数据缺失时暂不判断。';$('error').textContent=e.message;$('error').hidden=false;$('headline').textContent='本次未取得有效快照';$('statusLabel').textContent='等待重新读取';$('statusIcon').textContent='?';$('statusIcon').className='result-icon unknown';$('age').textContent='尚无新快照';$('checks').replaceChildren();$('answer').textContent='本次读取失败，不能沿用旧状态回答。';event('本次读取失败；没有新结论')}finally{busy=false;document.querySelectorAll('button').forEach(n=>n.disabled=false)}}
async function showDemo(name){replayActive=false;mode='demo';scenario=name;paint(await api('demo',{scenario}))}
document.querySelectorAll('[data-scenario]').forEach(n=>n.addEventListener('click',()=>run(()=>showDemo(n.dataset.scenario))));
$('example').onclick=()=>run(()=>showDemo('line-stale'));
$('live').onclick=()=>run(async()=>{replayActive=false;mode='live';$('sourceTitle').textContent=names[mode];$('sourceNote').textContent='正在尝试读取本机原调试服务…';paint(await api('live',{}))});
$('analyze').onclick=()=>run(async()=>{replayActive=false;mode='import';snapshot=JSON.parse($('json').value);paint(await api('analyze',{snapshot}))});
async function ask(q){await run(async()=>{if(!report)throw Error('请先取得有效快照');const result=await api('ask',{mode,scenario,snapshot:mode==='import'?snapshot:undefined,question:q});paint(result.report,!replayActive);$('answer').textContent=readableEvidence(result.answer);event((replayActive?'回放询问：':'询问：')+q)})}
$('askForm').onsubmit=e=>{e.preventDefault();ask($('question').value)};
document.querySelectorAll('[data-question]').forEach(n=>n.onclick=()=>{$('question').value=n.dataset.question;ask(n.dataset.question)});
$('export').onclick=()=>{const data={version:'0.2',exported_at:new Date().toISOString(),notice:'示例、导入与真实接口来源均显式标注；无实车验收声明。',history,latest:report};const link=el('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}));link.download='小车诊断记录-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)};
paintHistory();setInterval(updateAge,1000);run(()=>showDemo('line-stale'));

// Playback uses the same reports and explicitly retains each data source.
let playbackData=null,playbackIndex=0,playbackSnapshots=[];
function downloadAsset(name,text,type='application/json;charset=utf-8') {
  const link=el('a');
  link.href=URL.createObjectURL(new Blob([text],{type}));link.download=name;link.click();
  setTimeout(()=>URL.revokeObjectURL(link.href),1000);
}
$('reportExport').onclick=()=>{
  if(!report){$('error').textContent='请先取得有效快照。';$('error').hidden=false;return;}
  const lines=['# 小车诊断报告','',`来源：${names[report.source]}`,`时间：${report.at}`,'',`结论：${report.title}`,''];
  for(const f of report.findings) lines.push('## '+f.title,'',readableEvidence(f.explanation),'','依据：',...f.evidence.map(x=>'- '+readableEvidence(x)),'','下一步：',...f.steps.map((x,i)=>(i+1)+'. '+readableEvidence(x)),'');
  lines.push(report.limits);downloadAsset('小车诊断报告.md',lines.join('\n'),'text/markdown;charset=utf-8');
};
function showPlayback() {
  replayActive=true;
  const r=playbackData.frames[playbackIndex];mode=r.source;
  if(mode==='demo')scenario=['restored','line-stale','unknown','restored','offline','restored'][playbackIndex];
  else snapshot=playbackSnapshots[playbackIndex];
  paint(r,false);event('回放第'+(playbackIndex+1)+'帧：'+r.title,r.source);$('replayPosition').textContent=`第 ${playbackIndex+1} / ${playbackData.frames.length} 帧`;
  const s=playbackData.summary;
  $('replaySummary').textContent=`${names[mode]} · ${s.frame_count} 份快照 · ${s.opened} 次问题出现 · ${s.recovered} 次对应恢复。`+playbackData.note;
}
$('demoReplay').onclick=()=>run(async()=>{
  playbackData=await api('session',{mode:'demo'});playbackSnapshots=[];playbackIndex=0;showPlayback();
});
$('sequenceFile').onchange=()=>run(async()=>{
  const file=$('sequenceFile').files[0];if(!file)return;
  if(file.size>900000)throw Error('回放文件请小于900KB。');
  playbackSnapshots=JSON.parse(await file.text());
  playbackData=await api('session',{mode:'import',snapshots:playbackSnapshots});playbackIndex=0;showPlayback();
});
$('previousFrame').onclick=()=>{if(playbackData&&playbackIndex>0){playbackIndex--;showPlayback();}};
$('nextFrame').onclick=()=>{if(playbackData&&playbackIndex<playbackData.frames.length-1){playbackIndex++;showPlayback();}};
