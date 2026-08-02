"""
项目统一配置文件
"""

# ===== 路径配置 =====
import os

# 获取当前文件所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

md5path = os.path.join(BASE_DIR, "md5.text")
collections_name = "rag"
persist_directory = os.path.join(BASE_DIR, "chroma_db")

# ===== 文本分割配置 =====
chunk_size = 1000
chunk_overlap = 100
separators = ["\n\n", "\n", " .", "!", "？", "。", "！", "?", " ", ""]
max_split_char_mumber = 1000

# ===== 检索配置 =====
similarity_threshold = 3

# ===== 模型配置 =====
embedding_model_name = "text-embedding-v4"
chat_model_name = "qwen3-max"

# ===== 会话配置 =====
session_config = {
    "configurable": {
        "session_id": "user001"
    }
}

# ===== 管理员账号配置 =====
# 生产环境请修改为强密码
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ===== 文件上传限制 =====
MAX_FILE_SIZE_MB = 10
