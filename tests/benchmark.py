<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent v5</title>
<style>
:root{--bg:#f8f9fa;--card:#fff;--text:#1a1a2e;--text2:#888;--accent:#2563eb;--green:#16a34a;--red:#dc2626;--border:#e5e8ec;--radius:8px;--font:system-ui,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;max-width:1000px;margin:0 auto}
.header{background:var(--card);border-bottom:1px solid var(--border);padding:8px 16px;display:flex;align-items:center;gap:8px;flex-shrink:0;font-size:13px}
.header h1{font-size:16px}
.badge{font-size:10px;padding:2px 7px;border-radius:10px;background:#eff6ff;color:var(--accent);font-weight:600}
.sep{flex:1}
.main{flex:1;display:flex;overflow:hidden}
.chat-area{flex:1;display:flex;flex-direction:column}
.chat{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:88%;padding:8px 12px;border-radius:var(--radius);font-size:13px;line-height:1.5;word-break:break-word}
.msg.user{align-self:flex-end;background:var(--accent);color:#fff}
.msg.agent{align-self:flex-start;background:var(--card);border:1px solid var(--border)}
.msg.system{align-self:center;font-size:11px;color:var(--text2);padding:3px 8px;border-radius:12px;background:#f0f4f8}
.input-bar{background:var(--card);border-top:1px solid var(--border);padding:10px;display:flex;gap:6px;flex-shrink:0}
.input-bar input{flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px;outline:none}
.input-bar input:focus{border-color:var(--accent)}
.input-bar button,.input-bar select{padding:8px 14px;border:none;border-radius:var(--radius);font-size:12px;font-weight:600;cursor:pointer;background:var(--accent);color:#fff}
.input-bar button:disabled{opacity:.5}
.dashboard{width:260px;background:var(--card);border-left:1px solid var(--border);padding:12px;overflow-y:auto;flex-shrink:0;display:none}
.dashboard h3{font-size:13px;margin-bottom:8px}
.stat{margin-bottom:8px;font-size:11px}
.stat .label{color:var(--text2)}
.stat .value{font-weight:600}
.progress{height:4px;background:var(--border);border-radius:2px;margin-top:2px}
.progress .fill{height:100%;background:var(--accent);border-radius:2px;transition:width .3s}
.show-dash .dashboard{display:block}
.streaming .agent:last-child::after{content:'▊';animation:blink 1s infinite}
@keyframes blink{50%{opacity:0}}
</style>
</head>
<body class="show-dash">
<div class="header">
  <h1>Agent v5</h1>
  <span class="badge" id="modelBadge">DeepSeek</span>
  <span class="badge" id="toolBadge">6 tools</span>
  <span class="sep"></span>
  <span style="font-size:11px;color:var(--text2)">实时流式 · 智能路由</span>
</div>
<div class="main">
<div class="chat-area">
<div class="chat" id="chat"><div class="msg system">Agent v5 就绪。7 个创新全部集成。</div></div>
<div class="input-bar">
  <select id="mode"><option value="act">Act</option><option value="plan">Plan</option></select>
  <input id="msgInput" placeholder="输入任务..." autofocus>
  <button onclick="send()" id="sendBtn">→</button>
</div>
</div>
<div class="dashboard" id="dashboard">
  <h3>📊 仪表盘</h3>
  <div class="stat"><div class="label">模型</div><div class="value" id="dModel">-</div></div>
  <div class="stat"><div class="label">Turns</div><div class="value" id="dTurns">0</div></div>
  <div class="stat"><div class="label">Tokens</div><div class="value" id="dTokens">0</div></div>
  <div class="stat"><div class="label">费用</div><div class="value" id="dCost">¥0</div></div>
  <div class="stat"><div class="label">延迟</div><div class="value" id="dLatency">-</div></div>
  <div class="stat"><div class="label">记忆</div><div class="value" id="dMemory">0 条</div></div>
  <div class="stat"><div class="label">反射命中</div><div class="value" id="dReflex">0%</div><div class="progress"><div class="fill" id="dReflexBar" style="width:0%"></div></div></div>
  <hr style="margin:8px 0;border:none;border-top:1px solid var(--border)">
  <div style="font-size:10px;color:var(--text2)">7 创新 · 58 文件 · MIT</div>
</div>
</div>
<script>
let activeStream = null;

function addMsg(role,content){
  const d=document.getElementById('chat');
  const div=document.createElement('div');
  div.className='msg '+role;
  div.textContent=content;
  d.appendChild(div);d.scrollTop=d.scrollHeight;
  return div;
}

function updateDash(data){
  if(data.model) document.getElementById('dModel').textContent=data.model;
  if(data.turns!=null) document.getElementById('dTurns').textContent=data.turns;
  if(data.tokens) document.getElementById('dTokens').textContent=(data.tokens/1000).toFixed(1)+'K';
  if(data.cost!=null) document.getElementById('dCost').textContent='¥'+data.cost.toFixed(4);
  if(data.latency) document.getElementById('dLatency').textContent=data.latency+'s';
  if(data.memories!=null) document.getElementById('dMemory').textContent=data.memories+' 条';
}

async function send(){
  const inp=document.getElementById('msgInput');
  const btn=document.getElementById('sendBtn');
  const msg=inp.value.trim();
  if(!msg)return;
  inp.value='';inp.disabled=true;btn.disabled=true;

  addMsg('user',msg);
  const agentDiv=addMsg('agent','');
  document.querySelector('.chat-area').classList.add('streaming');

  try{
    const resp=await fetch('/api/chat/stream',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg,mode:document.getElementById('mode').value})
    });

    const reader=resp.body.getReader();
    const decoder=new TextDecoder();
    let buffer='',done=false;

    while(!done){
      const{value,done:d}=await reader.read();
      if(d){done=true;break}
      buffer+=decoder.decode(value,{stream:true});

      const lines=buffer.split('\n');
      buffer=lines.pop()||'';

      for(const line of lines){
        if(line.startsWith('data: ')){
          try{
            const d=JSON.parse(line.slice(6));
            if(d.done){
              updateDash(d);
              done=true;
            }else if(d.text){
              agentDiv.textContent+=d.text;
              document.getElementById('chat').scrollTop=document.getElementById('chat').scrollHeight;
            }else if(d.meta){
              updateDash(d.meta);
            }
          }catch(e){}
        }
      }
    }
    document.querySelector('.chat-area').classList.remove('streaming');
  }catch(e){
    agentDiv.textContent='错误: '+e.message;
  }
  inp.disabled=false;btn.disabled=false;inp.focus();
}

document.getElementById('msgInput').addEventListener('keydown',e=>{if(e.key==='Enter')send()});
</script>
</body>
</html>
