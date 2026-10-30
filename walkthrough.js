const canvas=document.getElementById('screen'),ctx=canvas.getContext('2d');
const progress=document.getElementById('progress');
const scenes=[
  {name:'电脑端的小车排查工具',seconds:5,scenario:'restored',action:'给机器人课程使用：先检查，再按步骤排查',detail:'小车沿黑线行驶异常时，分别检查电脑连接和底部巡线传感器的读数。',overview:true},
  {name:'连接正常，读数却没有更新',seconds:7,scenario:'line-stale',action:'选择“巡线数据过期”，查看检查结果',detail:'巡线传感器读取车下路面、辅助识别黑线。本例中它已有4.6秒未更新。',question:'巡线怎么了？'},
  {name:'断开连接时，先恢复连接',seconds:6,scenario:'offline',action:'切换“主控断连”示例，查看检查步骤',detail:'主控就是小车的控制板。连接中断后，先检查供电与电脑连接。',question:'连接怎么了？'},
  {name:'没有数据时，暂不判断',seconds:5,scenario:'unknown',action:'导入一份没有状态数据的记录',detail:'结果显示“未确认”，不能把没有数据当成一切正常。'},
  {name:'回看问题何时出现和恢复',seconds:8,scenario:'restored',action:'点击“载入示例过程”，逐份查看状态记录',detail:'快照就是某一时刻的状态记录。缺少数据的记录不会自动结束原问题。',session:true},
  {name:'接口可用，不等于车辆能动',seconds:6,scenario:'capability',action:'选择“遥控接口不可用”，查看说明',detail:'软件只检查接口支持情况；实际运动许可，需要在小车控制程序中核对。',question:'为什么不能启动？'},
  {name:'保存结果，便于继续排查',seconds:7,scenario:'restored',action:'点击“导出诊断报告”或“导出本机记录”',detail:'报告保存本次判断和检查步骤；状态记录可以交给同伴复查。',ending:true}
];
const duration=scenes.reduce((n,s)=>n+s.seconds,0);
let prepared=[],current=null,recording=false,started=0,elapsed=0,lastVideo=null;
async function api(path,body){const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.error||'接口错误');return d;}
function font(size=24,bold=false){ctx.font=`${bold?'600 ':''}${size}px "Microsoft YaHei", sans-serif`;}
function text(t,x,y,size=24,color='#263a50',bold=false){font(size,bold);ctx.fillStyle=color;ctx.fillText(t,x,y);}
function wrap(t,x,y,width,size=24,line=38,max=5,color='#465a70'){
  font(size);ctx.fillStyle=color;let row='',n=0;
  for(const ch of String(t)){if(ch==='\n'||ctx.measureText(row+ch).width>width){ctx.fillText(row,x,y+n*line);n++;row=ch==='\n'?'':ch;if(n>=max)return y+n*line;}else row+=ch;}
  if(row)ctx.fillText(row,x,y+n*line);return y+(n+1)*line;
}
function box(x,y,w,h,color='#fff'){ctx.fillStyle=color;ctx.beginPath();ctx.roundRect(x,y,w,h,12);ctx.fill();}
function draw(){
  // Native 1080p export with a 1280x720 logical layout.
  ctx.setTransform(1.5,0,0,1.5,0,0);
  ctx.fillStyle='#f3f5f7';ctx.fillRect(0,0,1280,720);
  ctx.fillStyle='#21384d';ctx.fillRect(0,0,1280,64);
  text('小车调试助手',36,42,24,'#fff',true);
  text('运行结果演示 · 示例数据',922,42,21,'#d8e2eb');
  if(!current){text('正在准备示例…',40,130);requestAnimationFrame(draw);return;}
  const {scene,index,report,answer}=current;
  text(`${String(index+1).padStart(2,'0')} / ${scenes.length}`,40,105,18,'#647588');
  text(scene.name,40,153,36,'#20374c',true);text(scene.action,40,195,22,'#53687b');
  box(40,223,736,354);box(796,223,444,354,'#e8eef4');
  const chosen=report.findings.find(f=>f.level==='issue')||report.findings.find(f=>f.level==='unknown')||report.findings.find(f=>f.code==='drive_unavailable')||report.findings[0];
  text('检查结果',64,262,19,'#677989');
  const color={issue:'#a65c17',unknown:'#667786',notice:'#2e608e',checked:'#23765e'}[report.status];
  wrap(scene.overview?'检查连接、传感器和恢复过程':report.title,64,310,680,28,36,2,color);wrap(scene.detail,64,382,670,25,39,3);
  let evidence='连接和巡线读数均在各自更新时间范围内';
  if(chosen.code==='line_stale'){const ms=Number(chosen.evidence[0].match(/= ([0-9.]+)/)[1]);evidence=`巡线读数：${ms/1000}秒未更新；检查阈值：1.5秒`;}
  else if(chosen.code==='link_offline')evidence='电脑与小车的连接状态：已断开';
  else if(report.status==='unknown')evidence='缺少连接状态或传感器读数，无法确认';
  else if(chosen.code==='drive_unavailable')evidence='当前遥控接口：不可用';
  text(scene.overview?'如何体验':'判断依据',64,506,18,'#677989');
  wrap(scene.overview?'打开工具 → 选择示例 → 查看结果和检查步骤':evidence,64,543,665,21,28,1,'#315d88');
  if(scene.overview){
    text('这段演示看什么',820,263,23,'#2c526e',true);
    wrap('1  软件怎样指出问题\n2  怎样给出检查步骤\n3  怎样记录问题恢复\n4  怎样保存排查结果',820,310,395,23,42,5);
  }else if(scene.session){
    text('6帧回放结果',820,263,23,'#2c526e',true);
    wrap('1  数据有效\n2  巡线过期\n3  字段缺失：保留原问题\n4  巡线恢复\n5  主控断连\n6  通信恢复',820,310,395,23,37,6);
  }else if(scene.ending){
    text('你可以怎样体验',820,263,23,'#2c526e',true);
    wrap('打开源码目录的启动助手\n在浏览器里使用工具\n\n示例模式无需连接小车\n运行方法见源码说明',820,310,395,22,37,6);
  }else{
    text(answer?'下一步检查':'导入结果',820,263,23,'#2c526e',true);
    wrap(answer||'数据不足，暂时无法判断。\n补齐状态字段后重新检查。',820,310,391,23,37,6);
  }
  box(40,598,1200,56,'#e4eaf0');text('示例数据；诊断结果由软件接口计算。实车诊断待验证。',62,633,22,'#52677a');
  text('状态检查 → 查看步骤 → 快照回放 → 导出报告',40,693,20,'#647588');text(`${duration}秒 / 1080p`,1080,693,18,'#647588');
  ctx.fillStyle='#326c99';ctx.fillRect(0,715,1280*(recording?Math.min(1,elapsed/duration):(index+1)/scenes.length),5);
  requestAnimationFrame(draw);
}
async function prepare(){
  prepared=await Promise.all(scenes.map(async(scene,index)=>{
    const report=scene.scenario==='unknown'?await api('analyze',{snapshot:{}}):await api('demo',{scenario:scene.scenario});
    let answer='',session=null;
    if(scene.question){const full=(await api('ask',{mode:'demo',scenario:scene.scenario,question:scene.question})).answer;answer=(full.split('下一步：')[1]||full).split('\n\n')[0].trim().replace(/原控制台/g,'小车调试程序').replace(/由本人/g,'').replace(/串口连接/g,'连接线');}
    if(scene.session)session=await api('session',{mode:'demo'});
    return {scene,index,report,answer,session};
  }));loadScene(0);progress.textContent='已准备好：44秒 / 1920×1080，点击开始导出。';
}
function loadScene(index){current=prepared[index];progress.textContent=`${index+1}/${scenes.length} ${current.scene.name}`;}
function saveBlob(blob,name){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000);}
document.getElementById('downloadVideo').onclick=()=>{if(lastVideo)saveBlob(lastVideo,'小车调试助手-功能演示-44秒.webm');};
document.getElementById('save').onclick=()=>canvas.toBlob(b=>saveBlob(b,`第三方演示画面-${current.index+1}.png`));
document.getElementById('stale').onclick=()=>loadScene(1);
document.getElementById('recovery').onclick=()=>loadScene(4);
document.getElementById('record').onclick=async()=>{
  if(recording||!prepared.length)return;
  if(!canvas.captureStream||typeof MediaRecorder==='undefined'){progress.textContent='浏览器不支持视频导出。';return;}
  const buttons=[...document.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
  const chunks=[],stream=canvas.captureStream(30);
  const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(x=>MediaRecorder.isTypeSupported(x));
  const rec=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:10000000});
  rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
  rec.onstop=()=>{lastVideo=new Blob(chunks,{type:mime});stream.getTracks().forEach(t=>t.stop());buttons.forEach(b=>b.disabled=false);progress.textContent='44秒演示录制完成，请点击下载已录制视频。';};
  try{
    loadScene(0);recording=true;started=performance.now();rec.start(1000);
    await new Promise(resolve=>{const tick=()=>{elapsed=(performance.now()-started)/1000;let end=0,index=0;for(let i=0;i<scenes.length;i++){end+=scenes[i].seconds;if(elapsed<end){index=i;break;}}if(elapsed>=duration){resolve();return;}if(current.index!==index)loadScene(index);setTimeout(tick,30);};tick();});
    recording=false;rec.stop();
  }catch(e){recording=false;if(rec.state==='recording')rec.stop();progress.textContent='导出中断：'+e.message;buttons.forEach(b=>b.disabled=false);}
};
prepare().catch(e=>progress.textContent=e.message);draw();
