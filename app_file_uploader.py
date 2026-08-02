import streamlit as st
from datetime import datetime
from knowledge_base import KnowledgeBaseService
import config_data as config

# 页面配置（必须是第一个 Streamlit 调用）
st.set_page_config(
    page_title="知识库管理",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

MAX_FILE_SIZE_MB = 10

# ===== 会话状态初始化 =====
if "server" not in st.session_state:
    st.session_state["server"] = KnowledgeBaseService()

if "upload_history" not in st.session_state:
    st.session_state["upload_history"] = []

# ===== 侧边栏 =====
with st.sidebar:
    st.title("📚 知识库管理")
    st.caption("上传文档到 RAG 向量知识库")

    st.divider()
    st.subheader("📋 知识库配置")
    st.caption(f"向量库路径: `{config.persist_directory}`")
    st.caption(f"嵌入模型: {config.embedding_model_name}")
    st.caption(f"分块大小: {config.chunk_size} 字符")
    st.caption(f"分块重叠: {config.chunk_overlap} 字符")

    st.divider()
    st.subheader("📊 本次会话上传记录")
    if st.session_state.upload_history:
        for record in st.session_state.upload_history:
            st.caption(
                f"{record['time']}  ·  **{record['file']}**  ({record['status']})"
            )
    else:
        st.caption("暂无上传记录")

    st.divider()
    st.caption("v1.0  ·  2026")

# ===== 主内容区 =====
st.title("知识库更新服务")
st.divider()

upload_file = st.file_uploader(
    "上传知识库文件",
    type=["txt"],
    accept_multiple_files=False,
)

if upload_file is None:
    st.info("👆 请上传一个 .txt 文件到知识库，或将文件拖拽到此区域")
    st.caption(f"支持格式：TXT  |  最大文件：{MAX_FILE_SIZE_MB}MB  |  编码：UTF-8")
else:
    file_name = upload_file.name
    file_size_kb = upload_file.size / 1024

    # 文件大小校验
    if upload_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"文件过大（>{MAX_FILE_SIZE_MB}MB），请拆分后上传")
        st.stop()

    # 文件信息展示
    col1, col2, col3 = st.columns(3)
    col1.metric("文件名称", file_name)
    col2.metric("文件格式", upload_file.type)
    col3.metric("文件大小", f"{file_size_kb:.1f} KB")

    # 内容预览（折叠）
    text = upload_file.getvalue().decode("utf-8")
    with st.expander("预览文件内容（前 2000 字符）"):
        st.text(text[:2000] + ("\n..." if len(text) > 2000 else ""))

    # 上传处理
    with st.status("正在载入知识库...", expanded=True) as status:
        result = st.session_state["server"].upload_by_file(text, file_name)
        status.update(label="载入完成!", state="complete", expanded=False)

    # 结果反馈
    if "跳过" in result:
        st.warning(result)
        st.toast("内容已存在，已跳过", icon="⏭️")
        upload_status = "跳过"
    elif "成功" in result:
        st.success(result)
        st.toast("知识库更新成功", icon="✅")
        upload_status = "成功"
    else:
        st.info(result)
        upload_status = "未知"

    # 记录上传历史
    st.session_state.upload_history.append({
        "file": file_name,
        "status": upload_status,
        "time": datetime.now().strftime("%H:%M:%S"),
    })
