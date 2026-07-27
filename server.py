"""
Agent Web API — Flask HTTP Server

启动:
    source agent/.venv/Scripts/activate
    python agent/server.py

端点:
    GET  /               Web UI
    POST /api/chat       发送消息 (SSE 流式)
    GET  /api/tools       列出工具
    GET  /api/health      健康检查
"""
from __future__ import annotations

import os
import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, Response, send_from_directory
from agent.core.agent import Agent, AgentConfig
from agent.tools.builtin import (
    ReadFileTool, WriteFileTool, ListDirTool, GrepTool, BashTool, WebFetchTool,
)
from agent.memory.memory import MemorySystem

app = Flask(__name__, static_folder=None)
agent: Agent | None = None
memory: MemorySystem | None = None


def get_agent() -> Agent:
    global agent
    if agent is None:
        config = AgentConfig(
            provider=os.environ.get("AGENT_PROVIDER", "deepseek"),
            model=os.environ.get("AGENT_MODEL", "deepseek-v4-flash"),
            api_key=os.environ.get("AGENT_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            max_turns=20,
        )
        agent = Agent(config)
        agent.register_tools([
            ReadFileTool(), WriteFileTool(), ListDirTool(),
            GrepTool(), BashTool(), WebFetchTool(),
        ])
    return agent


def get_memory() -> MemorySystem:
    global memory
    if memory is None:
        memory = MemorySystem()
    return memory


# ── API 端点 ───────────────────────────────
@app.route("/api/health")
def health():
    ag = get_agent()
    return jsonify({
        "status": "ok",
        "provider": ag.config.provider,
        "model": ag.config.model,
        "tools": len(ag.registry),
    })


@app.route("/api/tools")
def list_tools():
    ag = get_agent()
    tools = []
    for name in ag.registry.list_names():
        t = ag.registry.get(name)
        tools.append({
            "name": name,
            "description": t.description,
            "destructive": getattr(t, "is_destructive", False),
        })
    return jsonify({"tools": tools})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    mode = data.get("mode", "act")

    if not message:
        return jsonify({"error": "空消息"}), 400

    ag = get_agent()
    ag.config.mode = mode

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(ag.run(message))
    loop.close()

    # 记录记忆
    get_memory().log_daily(f"Task: {message[:80]}\n→ {result.final_answer[:200]}")

    return jsonify({
        "answer": result.final_answer,
        "turns": result.turns,
        "tool_calls": len(result.tool_calls),
        "mode": mode,
    })


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """SSE 流式响应"""
    data = request.get_json()
    message = data.get("message", "")
    mode = data.get("mode", "act")

    def generate():
        ag = get_agent()
        ag.config.mode = mode

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(ag.run(message))
        loop.close()

        chunks = (result.final_answer or "").split("\n")
        for chunk in chunks:
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True, 'turns': result.turns, 'tool_calls': len(result.tool_calls)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ── Web UI ──────────────────────────────────
@app.route("/")
def index():
    return WEB_UI


WEB_UI = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent v4</title>
<style>
:root {
  --bg:#f8f9fa; --card:#fff; --text:#1a1a2e; --text2:#555;
  --accent:#2563eb; --accent-light:#eff6ff; --border:#e5e8ec;
  --danger:#dc2626; --radius:8px; --font:system-ui,sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column}
.header{background:var(--card);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;align-items:center;gap:12px}
.header h1{font-size:18px;font-weight:700}
.header .badge{font-size:11px;padding:2px 8px;border-radius:10px;background:var(--accent-light);color:var(--accent)}
.chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:80%;padding:10px 14px;border-radius:var(--radius);font-size:14px;line-height:1.5}
.msg.user{align-self:flex-end;background:var(--accent);color:#fff}
.msg.agent{align-self:flex-start;background:var(--card);border:1px solid var(--border)}
.msg .meta{font-size:11px;opacity:.6;margin-bottom:4px}
.input-bar{background:var(--card);border-top:1px solid var(--border);padding:12px;display:flex;gap:8px}
.input-bar input{flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:var(--radius);font-size:14px;outline:none}
.input-bar input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(37,99,235,.1)}
.input-bar button{padding:10px 20px;border:none;border-radius:var(--radius);font-size:14px;font-weight:600;cursor:pointer;background:var(--accent);color:#fff}
.input-bar button:hover{opacity:.9}
.input-bar select{padding:8px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px}
.status{font-size:11px;color:var(--text2);text-align:center;padding:4px}
.loading{opacity:.5}
</style>
</head>
<body>
<div class="header">
  <h1>Agent v4</h1>
  <span class="badge" id="providerBadge">loading...</span>
  <span style="font-size:12px;color:var(--text2)" id="toolBadge"></span>
</div>
<div class="chat" id="chat"></div>
<div class="status" id="status">输入任务，按 Enter 发送</div>
<div class="input-bar">
  <select id="modeSelect">
    <option value="act">Act</option>
    <option value="plan">Plan</option>
    <option value="auto">Auto</option>
  </select>
  <input id="msgInput" placeholder="输入任务..." autofocus>
  <button onclick="send()">发送</button>
</div>
<script>
let health={};

async function init(){
  try{
    const r=await fetch('/api/health');
    health=await r.json();
    document.getElementById('providerBadge').textContent=health.provider+'/'+health.model;
    const tr=await fetch('/api/tools');
    const td=await tr.json();
    document.getElementById('toolBadge').textContent=td.tools.length+' tools';
  }catch(e){document.getElementById('status').textContent='连接失败: '+e.message}
}

function addMsg(role,text,meta=''){
  const d=document.getElementById('chat');
  const div=document.createElement('div');
  div.className='msg '+role;
  div.innerHTML=(meta?'<div class="meta">'+meta+'</div>':'')+text.replace(/\n/g,'<br>');
  d.appendChild(div);
  d.scrollTop=d.scrollHeight;
}

async function send(){
  const inp=document.getElementById('msgInput');
  const msg=inp.value.trim();
  if(!msg)return;
  inp.value='';
  inp.disabled=true;
  addMsg('user',msg);
  document.getElementById('status').textContent='执行中...';

  try{
    const r=await fetch('/api/chat',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg,mode:document.getElementById('modeSelect').value})
    });
    const d=await r.json();
    addMsg('agent',d.answer,'turns: '+d.turns+' · tools: '+d.tool_calls+' · '+d.mode);
    document.getElementById('status').textContent='完成 · '+d.turns+' 轮';
  }catch(e){
    addMsg('agent','错误: '+e.message);
    document.getElementById('status').textContent='出错';
  }
  inp.disabled=false;
  inp.focus();
}

document.getElementById('msgInput').addEventListener('keydown',e=>{if(e.key==='Enter')send()});
init();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("=" * 50)
    print("  Agent Web Server")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
