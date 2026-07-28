"""
Agent Desktop App — 跨平台桌面应用

基于 PyWebView，Windows/Mac/Linux 一键运行。

启动:
    pip install pywebview
    python desktop_app.py
"""
from __future__ import annotations

import os
import sys
import threading
import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.server import app as flask_app


def start_flask():
    """后台启动 Flask 服务"""
    flask_app.run(host="127.0.0.1", port=51423, debug=False, use_reloader=False)


def main():
    # 启动 Flask 后台
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    # 创建桌面窗口
    window = webview.create_window(
        title="Agent v5",
        url="http://127.0.0.1:51423",
        width=1000,
        height=700,
        min_size=(600, 400),
        resizable=True,
        fullscreen=False,
        confirm_close=True,
    )

    webview.start(debug=False)
    sys.exit(0)


if __name__ == "__main__":
    main()
