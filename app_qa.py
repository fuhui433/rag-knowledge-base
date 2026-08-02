import streamlit as st
import uuid
from rag import RagService
import config_data as config

# 页面配置（必须是第一个 Streamlit 调用）
st.set_page_config(
    page_title="智能客服",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def capture(generator, cache_list):
    """流式获取生成器内容并缓存到列表"""
    for chunk in generator:
        cache_list.append(chunk)
        yield chunk


def get_session_config():
    """动态构建会话配置，使用当前 session_id"""
    return {
        "configurable": {
            "session_id": st.session_state["session_id"]
        }
    }


# ===== 会话状态初始化 =====
if "message" not in st.session_state:
    st.session_state["message"] = [
        {"role": "assistant", "content": "欢迎来到智能客服系统，请输入您的问题。"}
    ]

if "rag" not in st.session_state:
    st.session_state["rag"] = RagService()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

# ===== 侧边栏 =====
with st.sidebar:
    st.title("🤖 智能客服")
    st.caption("基于 RAG 的知识问答系统")

    st.divider()
    st.subheader("📋 会话信息")
    st.caption(f"会话 ID: `{st.session_state['session_id']}`")
    total_messages = len(
        [m for m in st.session_state.message if m["role"] == "user"]
    )
    total_chars = sum(
        len(m["content"])
        for m in st.session_state.message
        if m["role"] == "assistant"
    )
    st.caption(f"本轮提问: {total_messages} 次")
    st.caption(f"回复总字数: {total_chars}")

    st.divider()
    st.subheader("📚 知识库")
    st.caption(f"嵌入模型: {config.embedding_model_name}")
    st.caption(f"对话模型: {config.chat_model_name}")

    st.divider()
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state["message"] = [
            {"role": "assistant", "content": "欢迎来到智能客服系统，请输入您的问题。"}
        ]
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
        st.toast("对话已清空", icon="🧹")
        st.rerun()

    st.divider()
    st.caption("v1.0  ·  2026")

# ===== 主内容区 =====
st.title("智能客服")
st.divider()

# 显示聊天历史
for message in st.session_state.message:
    st.chat_message(message["role"]).write(message["content"])

# 聊天输入
prompt = st.chat_input(placeholder="请输入您的问题，按 Enter 发送...")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.message.append({"role": "user", "content": prompt})

    ai_res_list = []
    try:
        with st.spinner("AI 思考中..."):
            res_stream = st.session_state["rag"].chain.stream(
                {"input": prompt}, get_session_config()
            )
            st.chat_message("assistant").write_stream(
                capture(res_stream, ai_res_list)
            )
            st.session_state["message"].append(
                {"role": "assistant", "content": "".join(ai_res_list)}
            )
    except Exception as e:
        st.error(f"生成回复时出错，请重试。错误详情：{str(e)}")
        st.toast("回复生成失败", icon="❌")
        # 移除未能得到回复的用户消息
        st.session_state.message.pop()
