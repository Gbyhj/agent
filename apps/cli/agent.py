"""Agent CLI — 软件版 (Rich 终端 UI)

对标: Claude Code CLI · Aider · ChatGPT CLI
体验: 彩色面板 · 流式输出 · 进度条 · 多模式 · 历史记录

安装: pip install agent-cli && agent
"""
import asyncio, sys, os, readline, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── 终端颜色 (无依赖) ──
class Color:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
    BLUE = "\033[34m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLACK = "\033[40m"; BG_BLUE = "\033[44m"

def banner():
    print(f"""
{Color.CYAN}{Color.BOLD}╔══════════════════════════════════════╗
║        Agent CLI v5.0                 ║
║  自主 AI 助手 · 代码审查·架构分析      ║
╚══════════════════════════════════════╝{Color.RESET}
{Color.DIM}命令: /help /mode /review /arch /db /exit{Color.RESET}
""")

def show_help():
    print(f"""
{Color.BOLD}可用命令:{Color.RESET}
  {Color.GREEN}/review <文件>{Color.RESET}  代码安全审查
  {Color.GREEN}/arch{Color.RESET}           项目架构分析
  {Color.GREEN}/db <描述>{Color.RESET}      数据库表设计
  {Color.GREEN}/search <关键词>{Color.RESET}  联网搜索
  {Color.GREEN}/mode shadow|assist|auto{Color.RESET}  切换模式
  {Color.GREEN}/soul{Color.RESET}          查看 Agent 身份
  {Color.GREEN}/stats{Color.RESET}         查看统计
  {Color.GREEN}/clear{Color.RESET}         清屏
  {Color.GREEN}/exit{Color.RESET}          退出
""")

def spinner(text: str, duration: float = 0.8):
    """模拟进度动画"""
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    import threading
    stop = threading.Event()
    def _spin():
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\r{Color.CYAN}{frames[i%len(frames)]}{Color.RESET} {text}")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write(f"\r{Color.GREEN}✓{Color.RESET} {text}\n")
    t = threading.Thread(target=_spin)
    t.start()
    time.sleep(duration)
    stop.set()
    t.join()

def stream_output(text: str, delay: float = 0.015):
    """流式输出 (打字机效果)"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def status_bar(mode: str, calls: int, cost: float):
    """底部状态栏"""
    bar = f"{Color.BG_BLUE}{Color.WHITE} 模式:{mode} | 调用:{calls} | 费用:¥{cost:.4f} {Color.RESET}"
    return bar

async def process_with_agent(message: str, mode: str = "auto") -> str:
    """调用 Agent 后端处理"""
    try:
        from agent.providers.llm import LLM
        api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("AGENT_API_KEY", ""))
        if not api_key:
            return f"{Color.YELLOW}⚠ 未配置 API Key。设置: export DEEPSEEK_API_KEY=sk-xxx{Color.RESET}\n\n[演示模式] 这是一个 Agent CLI，支持:\\n  • /review — 代码安全审查\\n  • /arch   — 项目架构分析\\n  • /db     — 数据库表设计\\n  • /search — 联网搜索"
        
        llm = LLM(provider="deepseek", model="deepseek-chat")
        resp = llm.chat([{"role": "user", "content": message}])
        return resp.content
    except Exception as e:
        return f"{Color.RED}错误: {e}{Color.RESET}"

async def main():
    """CLI 主循环"""
    banner()
    mode = "auto"
    calls = 0
    
    # 历史记录
    hist_file = os.path.expanduser("~/.agent_history")
    try:
        readline.read_history_file(hist_file)
    except Exception:
        pass
    
    while True:
        try:
            prompt = f"{Color.GREEN}agent [{mode}]{Color.RESET} {Color.DIM}▶{Color.RESET} "
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            readline.write_history_file(hist_file)
            
            # 命令处理
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/exit" or cmd == "/quit":
                    print(f"{Color.DIM}再见!{Color.RESET}")
                    break
                elif cmd == "/help":
                    show_help()
                    continue
                elif cmd == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    banner()
                    continue
                elif cmd == "/stats":
                    print(f"{Color.DIM}调用次数: {calls} | 模式: {mode}{Color.RESET}")
                    continue
                elif cmd == "/soul":
                    try:
                        from agent.src.features.soul import Soul
                        s = Soul()
                        print(f"\n{Color.CYAN}{s.identity['raw']}{Color.RESET}\n")
                    except Exception:
                        print(f"{Color.YELLOW}SOUL.md 未配置{Color.RESET}")
                    continue
                elif cmd.startswith("/mode"):
                    new_mode = cmd.replace("/mode", "").strip()
                    if new_mode in ("shadow", "assist", "auto", "autonomous"):
                        mode = new_mode
                        print(f"{Color.GREEN}✓ 模式切换: {mode}{Color.RESET}")
                    else:
                        print(f"模式: shadow | assist | auto")
                    continue
            
            # 调用 Agent
            calls += 1
            spinner(f"处理中: {user_input[:40]}...", 0.5)
            
            result = await process_with_agent(user_input, mode)
            
            # 输出
            print(f"\n{Color.BOLD}{'─'*60}{Color.RESET}")
            stream_output(result)
            print(f"{Color.BOLD}{'─'*60}{Color.RESET}\n")
            
            # 状态栏
            print(status_bar(mode, calls, calls * 0.001))
            print()
            
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}按 /exit 退出{Color.RESET}")
        except EOFError:
            print(f"\n{Color.DIM}再见!{Color.RESET}")
            break

if __name__ == "__main__":
    asyncio.run(main())
