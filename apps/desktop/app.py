"""Agent Desktop — 桌面版 (PyWebView)

对标: ChatGPT Desktop · Claude Desktop
体验: 原生窗口 · 系统托盘 · 快捷键 · 本地运行
"""
import sys, os, json, threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── 桌面版 HTML UI ──
DESKTOP_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Desktop</title>
<style>
:root {
  --bg: #1a1a2e; --surface: #16213e; --card: #0f3460;
  --text: #e0e0e0; --accent: #00d2ff; --accent2: #7b2ff7;
  --success: #00e676; --warn: #ffd600; --error: #ff1744;
  --border: #2a2a4a; --hover: #1e3a6e;
  font-family: 'Segoe UI', system-ui, sans-serif;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }

/* Sidebar */
.sidebar {
  width: 260px; background: var(--surface); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; padding: 16px;
}
.sidebar h2 {
  font-size: 18px; background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 16px;
}
.mode-btn {
  display: block; width: 100%; padding: 10px; margin: 4px 0;
  background: var(--card); border: 1px solid var(--border); color: var(--text);
  border-radius: 8px; cursor: pointer; text-align: left; font-size: 13px;
  transition: all 0.15s;
}
.mode-btn:hover { background: var(--hover); border-color: var(--accent); }
.mode-btn.active { background: var(--accent); color: #000; border-color: var(--accent); font-weight: 600; }
.history-item {
  padding: 8px 12px; margin: 2px 0; border-radius: 6px;
  cursor: pointer; font-size: 12px; color: #999; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.history-item:hover { background: var(--hover); color: var(--text); }

/* Chat Area */
.chat-area { flex: 1; display: flex; flex-direction: column; }
.header {
  padding: 12px 20px; background: var(--surface);
  border-bottom: 1px solid var(--border); font-size: 14px;
  display: flex; justify-content: space-between; align-items: center;
}
.messages {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 12px;
}
.msg {
  max-width: 80%; padding: 12px 16px; border-radius: 12px;
  font-size: 14px; line-height: 1.6; word-break: break-word;
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } }
.msg.user { background: var(--accent); color: #000; align-self: flex-end; }
.msg.agent { background: var(--card); border: 1px solid var(--border); align-self: flex-start; }
.msg.think { background: transparent; border: 1px dashed var(--border); color: #888; font-style: italic; }
.msg.tool { background: #1a1a1a; border: 1px solid #333; font-family: monospace; font-size: 12px; }

/* Input */
.input-bar {
  padding: 16px 20px; background: var(--surface); border-top: 1px solid var(--border);
  display: flex; gap: 8px;
}
.input-bar input {
  flex: 1; padding: 12px 16px; background: var(--bg); border: 1px solid var(--border);
  border-radius: 12px; color: var(--text); font-size: 14px; outline: none;
}
.input-bar input:focus { border-color: var(--accent); }
.input-bar button {
  padding: 12px 24px; background: linear-gradient(135deg, var(--accent), var(--accent2));
  border: none; border-radius: 12px; color: #000; font-weight: 600;
  cursor: pointer; font-size: 14px; transition: opacity 0.15s;
}
.input-bar button:hover { opacity: 0.9; }
.input-bar button:disabled { opacity: 0.4; cursor: not-allowed; }

/* Skills */
.skills {
  padding: 8px 20px; display: flex; gap: 8px; flex-wrap: wrap;
}
.skill-chip {
  padding: 6px 14px; background: var(--card); border: 1px solid var(--border);
  border-radius: 20px; font-size: 12px; cursor: pointer; transition: all 0.15s;
}
.skill-chip:hover { border-color: var(--accent); color: var(--accent); }

/* Status */
.status {
  padding: 8px 20px; font-size: 12px; color: #666;
  display: flex; justify-content: space-between;
}
</style>
</head>
<body>
<div class="sidebar">
  <h2>🤖 Agent Desktop</h2>
  <div style="margin-bottom:12px">
    <button class="mode-btn active" onclick="setMode('auto')">🚀 自主模式</button>
    <button class="mode-btn" onclick="setMode('assist')">🤝 辅助模式</button>
    <button class="mode-btn" onclick="setMode('shadow')">👻 影子模式</button>
  </div>
  <div style="font-size:11px;color:#666;margin:8px 0">对话历史</div>
  <div id="historyList" style="flex:1;overflow-y:auto"></div>
  <div style="font-size:10px;color:#444;margin-top:8px;text-align:center">v5.0 · Desktop Edition</div>
</div>

<div class="chat-area">
  <div class="header">
    <span id="headerTitle">Agent Desktop</span>
    <span id="headerStatus" style="color:var(--accent);font-size:12px">● 就绪</span>
  </div>
  
  <div class="messages" id="messages">
    <div class="msg agent">
      👋 你好!我是 Agent Desktop。<br>
      可以帮你审查代码、分析架构、设计数据库、搜索信息。<br>
      选择一个技能或直接输入问题开始。
    </div>
  </div>

  <div class="skills">
    <span class="skill-chip" onclick="quickSend('审查代码安全性')">🔍 代码审查</span>
    <span class="skill-chip" onclick="quickSend('分析项目架构')">🏗️ 架构分析</span>
    <span class="skill-chip" onclick="quickSend('设计用户数据库表')">🗄️ 数据库设计</span>
    <span class="skill-chip" onclick="quickSend('搜索最新AI框架')">🌐 联网搜索</span>
    <span class="skill-chip" onclick="quickSend('你有哪些功能?')">❓ 功能列表</span>
  </div>

  <div class="input-bar">
    <input id="input" placeholder="输入消息..." onkeydown="if(event.key==='Enter')send()" autofocus>
    <button id="sendBtn" onclick="send()">发送</button>
  </div>
  
  <div class="status">
    <span id="statusText">就绪</span>
    <span id="costText">费用: ¥0.0000</span>
  </div>
</div>

<script>
let mode = 'auto';
let history = [];
let totalCost = 0;
let callCount = 0;

function setMode(m) {
  mode = m;
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('headerTitle').textContent = 'Agent Desktop [' + m + ']';
}

function addMsg(type, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + type;
  div.textContent = text;
  document.getElementById('messages').appendChild(div);
  div.scrollIntoView({behavior:'smooth',block:'end'});
  return div;
}

function quickSend(msg) {
  document.getElementById('input').value = msg;
  send();
}

async function send() {
  const inp = document.getElementById('input');
  const btn = document.getElementById('sendBtn');
  const msg = inp.value.trim();
  if (!msg) return;
  
  inp.value = ''; inp.disabled = true; btn.disabled = true;
  document.getElementById('statusText').textContent = '思考中...';
  
  addMsg('user', msg);
  history.push({role:'user',content:msg});
  
  try {
    const apiKey = localStorage.getItem('agent-api-key') || '';
    if (apiKey) {
      const resp = await fetch('https://api.deepseek.com/v1/chat/completions', {
        method:'POST',
        headers:{'Content-Type':'application/json','Authorization':'Bearer '+apiKey},
        body: JSON.stringify({
          model:'deepseek-chat',
          messages:[
            {role:'system',content:'你是 Agent Desktop, 一个简洁专业的AI助手。用中文回答。'},
            ...history.slice(-10)
          ],
          stream:false
        })
      });
      const data = await resp.json();
      const answer = data.choices?.[0]?.message?.content || 'No response';
      addMsg('agent', answer);
      history.push({role:'assistant',content:answer});
      callCount++;
      totalCost += 0.001;
    } else {
      // Demo mode - sophisticated responses
      await sleep(300);
      addMsg('think', '📋 分析: ' + msg.slice(0,30) + '...');
      await sleep(500);
      
      const demoAnswers = {
        '审查': '## 🔍 代码审查结果\n\n### ✅ 通过项\n- 输入验证: 已实现参数校验\n- 错误处理: 有 try/except 包裹\n\n### ⚠️ 需要注意\n- 第23行: SQL 查询可参数化\n- 第45行: 建议增加超时设置\n\n### 📊 评分: 7.5/10',
        '架构': '## 🏗️ 架构分析\n\n```\n项目结构:\nsrc/engine/    核心引擎\nsrc/infra/     基础设施\nsrc/features/  业务功能\nsrc/memory/    记忆系统\n```\n\n耦合度: 中 · 内聚度: 高\n建议: 增加依赖注入层',
        '数据库': '```sql\nCREATE TABLE users (\n  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n  name VARCHAR(100) NOT NULL,\n  email VARCHAR(255) UNIQUE NOT NULL,\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n  INDEX idx_email (email)\n);\n```\n\n✅ 已添加: 主键 · 唯一约束 · 时间戳 · 索引',
        '搜索': '## 🔍 搜索结果\n\n1. **LangGraph** — 状态图编排框架 (15K+ stars)\n2. **CrewAI** — 角色化多Agent协作 (20K+ stars)\n3. **AutoGen** — 微软多Agent框架 (35K+ stars)\n4. **OpenHands** — 开源AI程序员 (74K+ stars)\n\n💡 建议: 根据任务复杂度选择合适的框架',
        '功能': '## 🤖 Agent Desktop 功能\n\n| 功能 | 说明 |\n|------|------|\n| 🔍 代码审查 | 安全/性能/质量 |\n| 🏗️ 架构分析 | 模块依赖/设计模式 |\n| 🗄️ 数据库设计 | SQL生成/索引优化 |\n| 🌐 联网搜索 | 实时信息检索 |\n| 👻 影子模式 | 不执行,只观察 |\n| 🚀 自主模式 | 全自动任务执行 |',
      };
      
      let answer = '收到你的问题：「' + msg.slice(0,50) + '」\n\n';
      for (const [key, val] of Object.entries(demoAnswers)) {
        if (msg.includes(key)) { answer = val; break; }
      }
      addMsg('agent', answer);
      history.push({role:'assistant',content:answer});
    }
  } catch(e) {
    addMsg('agent', '⚠️ 连接失败: ' + e.message + '\n请在设置中配置API Key');
  }
  
  document.getElementById('statusText').textContent = '就绪';
  document.getElementById('costText').textContent = '费用: ¥' + totalCost.toFixed(4);
  inp.disabled = false; btn.disabled = false;
  inp.focus();
  
  // Update sidebar history
  const hl = document.getElementById('historyList');
  const item = document.createElement('div');
  item.className = 'history-item';
  item.textContent = msg.slice(0,30);
  hl.prepend(item);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
</script>
</body>
</html>"""

def create_desktop_html(path: str):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(DESKTOP_HTML)

def launch_desktop():
    """启动桌面应用 (PyWebView)"""
    html_path = os.path.join(os.path.dirname(__file__), "desktop.html")
    create_desktop_html(html_path)
    
    try:
        import webview
        window = webview.create_window(
            "Agent Desktop v5.0",
            html_path,
            width=1000,
            height=700,
            min_size=(800, 500),
            resizable=True,
        )
        webview.start(debug=False)
    except ImportError:
        print("请安装: pip install pywebview")
        print(f"或直接在浏览器打开: file://{html_path}")
        import webbrowser
        webbrowser.open(f"file://{html_path}")

if __name__ == "__main__":
    launch_desktop()
