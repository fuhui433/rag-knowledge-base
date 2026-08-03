"""
用户历史消息存储 - 支持多用户
"""

import json
import os
from typing import Sequence
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from services.users import get_user_history_dir


def get_history(session_id: str, username: str = "default") -> BaseChatMessageHistory:
    """
    获取用户的历史消息存储
    session_id 可以是 "user:username" 或普通 session ID
    """
    # 解析 session_id，提取用户名
    if session_id.startswith("user:"):
        user = session_id[5:]
    else:
        user = username

    return FileChatMessageHistory(user, get_user_history_dir(user))


class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, username: str, storage_path: str):
        self.username = username
        self.storage_path = storage_path
        self.file_path = os.path.join(self.storage_path, username + "_chat_history.json")
        os.makedirs(self.storage_path, exist_ok=True)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        all_messages = list(self.messages)
        all_messages.extend(messages)
        new_messages = [message_to_dict(message) for message in all_messages]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(new_messages, f, ensure_ascii=False)

    @property
    def messages(self) -> list[BaseMessage]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)
                return messages_from_dict(messages_data)
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        if os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f)
