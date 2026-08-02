import os
import config
import hashlib
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime


def check_md5(md5_str: str):
    if not os.path.exists(config.md5path):
        open(config.md5path, "w", encoding="utf-8").close()
        return False
    else :
        for line in open(config.md5path, "r", encoding="utf-8").readlines():
            line = line.strip()
            if line == md5_str:
                return True
        return  False



def save_md5(md5_str: str):
    with open(config.md5path, "a", encoding="utf-8") as f:
        f.write(md5_str + "\n")

def get_string_md5(input_str: str, encoding="utf-8"):
    str_bytes = input_str.encode( encoding= encoding)
    md5_obj= hashlib.md5()
    md5_obj.update(str_bytes)
    return md5_obj.hexdigest()


class KnowledgeBaseService(object):
    def __init__(self):
        os.makedirs(config.persist_directory, exist_ok=True)

        _key = os.environ.get("DASHSCOPE_API_KEY", "")
        self.chroma = Chroma(
            collection_name=config.collections_name,
            embedding_function=DashScopeEmbeddings(
                model="text-embedding-v4",
                dashscope_api_key=_key,
            ),
            persist_directory=config.persist_directory,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,

        )

    def upload_by_file(self, data, filename):
        md5_hex = get_string_md5(data)
        if check_md5(md5_hex):
            return "[跳过]内容已经存在知识库中"

        if len(data) > config.max_split_char_mumber:
            knowledge_chunks: list[str] = self.splitter.split_text(data)
        else:
            knowledge_chunks = [data]

        metadata = {"source": filename,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     "operator": "小"
                    }

        self.chroma.add_texts(
            knowledge_chunks,
            metadatas=[metadata for _ in knowledge_chunks],
        )
        save_md5(md5_hex)
        return f"[成功]上传文件 {filename} 到知识库中"

    # ----- 知识库管理方法 -----
    def _get_all(self) -> dict:
        """获取全部向量数据（绕过 Chroma get() 默认 limit）"""
        collection = self.chroma.get()
        if not collection or not collection.get("ids"):
            return {"ids": [], "metadatas": [], "documents": []}

        # Chroma 默认 limit 可能截断，用 include 分批获取
        total = self.chroma._collection.count()
        if total == 0:
            return {"ids": [], "metadatas": [], "documents": []}

        return self.chroma.get(limit=total)

    def list_files(self) -> list[dict]:
        """列出知识库中所有唯一的文件（去重source），返回文件信息列表"""
        collection = self._get_all()
        if not collection or not collection.get("metadatas"):
            return []

        seen = {}
        for meta in collection["metadatas"]:
            source = meta.get("source", "未知文件")
            if source not in seen:
                chunk_count = sum(
                    1 for m in collection["metadatas"]
                    if m.get("source") == source
                )
                seen[source] = {
                    "source": source,
                    "create_time": meta.get("create_time", "未知"),
                    "chunks": chunk_count,
                }

        return sorted(
            seen.values(),
            key=lambda x: x["create_time"],
            reverse=True,
        )

    def delete_by_source(self, source: str) -> int:
        """删除指定 source 的所有向量数据，返回删除的 chunk 数量"""
        collection = self._get_all()
        if not collection or not collection.get("ids"):
            return 0

        ids_to_delete = []
        for idx, meta in enumerate(collection["metadatas"]):
            if meta.get("source") == source:
                ids_to_delete.append(collection["ids"][idx])

        if ids_to_delete:
            self.chroma.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def delete_all(self) -> int:
        """清空整个知识库，返回删除的 chunk 数量"""
        collection = self._get_all()
        total = len(collection.get("ids", []))
        if total > 0:
            self.chroma.delete(ids=collection["ids"])
            open(config.md5path, "w", encoding="utf-8").close()
        return total

