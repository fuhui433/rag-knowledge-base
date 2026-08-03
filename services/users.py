"""
用户管理系统 - 注册/登录/用户历史存储
"""

import os
import json
import hashlib
from typing import Optional
from datetime import datetime


# 用户数据文件路径
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")

# 聊天历史存储目录
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "..", "chat_history")


def _hash_password(password: str, salt: str) -> tuple[str, str]:
    """对密码加盐哈希"""
    combined = password + salt
    hashed = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return hashed, salt


def _load_users() -> dict:
    """加载用户数据"""
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_users(users: dict) -> None:
    """保存用户数据"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register(username: str, password: str) -> tuple[bool, str]:
    """
    注册用户
    返回: (成功与否, 消息)
    """
    users = _load_users()

    if username in users:
        return False, "用户名已存在"

    salt = hashlib.md5(f"{username}{datetime.now()}".encode()).hexdigest()[:16]
    hashed_password, stored_salt = _hash_password(password, salt)

    users[username] = {
        "password_hash": hashed_password,
        "salt": stored_salt,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_users(users)
    return True, "注册成功"


def login(username: str, password: str) -> tuple[bool, str]:
    """
    用户登录
    返回: (成功与否, 消息)
    """
    users = _load_users()

    if username not in users:
        return False, "用户不存在"

    user = users[username]
    hashed_password, _ = _hash_password(password, user["salt"])

    if hashed_password != user["password_hash"]:
        return False, "密码错误"

    return True, "登录成功"


def get_user_history_dir(username: str) -> str:
    """获取用户的历史记录目录"""
    user_dir = os.path.join(HISTORY_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir
