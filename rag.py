import os
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda
from file_history_store import get_history
from vector_stores import VectorStoreService
from langchain_community.embeddings import DashScopeEmbeddings
import config
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi

# Streamlit Cloud Secrets 支持：尝试读取 secrets，失败则用环境变量
try:
    import streamlit as _st
    _key = _st.secrets.get("DASHSCOPE_API_KEY", "")
    if _key:
        os.environ["DASHSCOPE_API_KEY"] = _key
except Exception:
    pass

class RagService(object):
    def __init__(self):

        self.vector_service = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model_name)
        )

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一个知识库问答助手。请根据以下参考资料回答用户问题。"
                 "参考资料为知识库中检索到的相关文档。{context}"
                 "回答时优先使用参考资料中的信息，参考资料中没有覆盖到的内容，可以结合你自己的知识进行补充，但要向用户说明哪些来自知识库、哪些来自你的知识。"),
                MessagesPlaceholder("history"),
                ("user", "请回答用户提问：{input}")
            ]
        )

        self.chat_model = ChatTongyi(model=config.chat_model_name, streaming=True)

        self.chain = self.__get_chain()

    def __get_chain(self):
        """获取最终的执行链"""
        retriever = self.vector_service.get_retriever()

        def retrieve_with_scores(value: str):
            """检索时放松阈值，尽量匹配知识库中的内容"""
            docs_with_scores = self.vector_service.vector_store.similarity_search_with_relevance_scores(
                value, k=config.similarity_threshold
            )
            return [doc for doc, _ in docs_with_scores]

        def format_document(docs: list[Document]):
            if not docs:
                return "（知识库中未检索到直接相关的参考资料）"

            formatted_str = ""
            for doc in docs:
                formatted_str += f"文档片段：{doc.page_content}\n文档元数据：{doc.metadata}\n\n"

            return formatted_str

        def format_for_retriever(value: dict) -> str:
            return value["input"]

        def format_for_prompt_template(value):
            new_value = {}
            new_value["input"] = value["input"]["input"]
            new_value["context"] = value["context"]
            new_value["history"] = value["input"]["history"]
            return new_value

        chain = (
            {
                "input": RunnablePassthrough(),
                "context": RunnableLambda(format_for_retriever) | RunnableLambda(retrieve_with_scores) | RunnableLambda(format_document)
            } | RunnableLambda(format_for_prompt_template) | self.prompt_template | self.chat_model | StrOutputParser()
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        return conversation_chain