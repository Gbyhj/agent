"""
User System — 用户注册/登录/鉴权

最小可用版：JWT Token + 文件存储
生产版：替换为 PostgreSQL + 微信 openid
"""
from __future__ import annotations

import os
import json
import hashlib
import time
from datetime import datetime
from dataclasses import dataclass


@dataclass
class User:
    id: str
    name: str = ""
    platform: str = "web"       # web | miniapp | desktop
    openid: str = ""            # 微信 openid
    quota_daily: int = 50       # 每日请求额度
    quota_used: int = 0
    created_at: str = ""
    last_login: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class UserManager:
    """用户管理器"""

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = storage_dir or os.path.expanduser("~/.agent_users")
        os.makedirs(self.storage_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        return os.path.join(self.storage_dir, f"{user_id}.json")

    def create(self, name: str = "", platform: str = "web",
               openid: str = "") -> User:
        """创建用户"""
        import uuid
        user_id = openid or uuid.uuid4().hex[:16]
        user = User(id=user_id, name=name, platform=platform, openid=openid)
        self._save(user)
        return user

    def get(self, user_id: str) -> User | None:
        """获取用户"""
        try:
            data = json.load(open(self._path(user_id), encoding="utf-8"))
            data["last_login"] = datetime.now().isoformat()
            return User(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def login_wechat(self, code: str) -> User:
        """微信登录（小程序）"""
        # code → openid（调用微信 API）
        # 简化版：直接用 code hash 作为 openid
        openid = f"wx_{hashlib.md5(code.encode()).hexdigest()[:12]}"
        user = self.get(openid)
        if not user:
            user = self.create(name=f"用户{openid[-4:]}", platform="miniapp", openid=openid)
        user.last_login = datetime.now().isoformat()
        self._save(user)
        return user

    def check_quota(self, user_id: str) -> tuple[bool, str]:
        """检查用户额度"""
        user = self.get(user_id)
        if not user:
            return False, "用户不存在"

        # 每日重置
        today = datetime.now().strftime("%Y-%m-%d")
        if user.last_login[:10] != today:
            user.quota_used = 0
            self._save(user)

        if user.quota_used >= user.quota_daily:
            return False, f"今日额度已用完 ({user.quota_daily} 次)"

        user.quota_used += 1
        self._save(user)
        return True, f"剩余 {user.quota_daily - user.quota_used} 次"

    def _save(self, user: User):
        data = user.__dict__.copy()
        with open(self._path(user.id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def stats(self) -> dict:
        users = []
        for f in os.listdir(self.storage_dir):
            if f.endswith(".json"):
                try:
                    u = json.load(open(os.path.join(self.storage_dir, f)))
                    users.append({"id": u["id"], "name": u.get("name",""), "platform": u.get("platform","")})
                except Exception:
                    pass
        return {"total_users": len(users), "users": users[-20:]}


class RateLimiter:
    """速率限制器"""

    def __init__(self):
        self._buckets: dict[str, list[float]] = {}

    def check(self, user_id: str, max_requests: int = 10,
              window_seconds: int = 60) -> tuple[bool, str]:
        """检查速率限制"""
        now = time.time()
        window_start = now - window_seconds

        # 清理过期记录
        if user_id in self._buckets:
            self._buckets[user_id] = [t for t in self._buckets[user_id] if t > window_start]
        else:
            self._buckets[user_id] = []

        count = len(self._buckets[user_id])

        if count >= max_requests:
            reset_in = int(window_seconds - (now - (self._buckets[user_id][0] or now)))
            return False, f"请求过于频繁，{reset_in}秒后重试"

        self._buckets[user_id].append(now)
        return True, f"剩余 {max_requests - count - 1} 次"
