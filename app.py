"""
RAG 知识库管理系统 - 主入口
包含：用户注册/登录、知识问答（需登录）、后台管理（管理员登录）
"""

import os
import uuid
from datetime import datetime
import streamlit as st

# ===== 页面配置（必须是第一个 Streamlit 调用）=====
st.set_page_config(
    page_title="RAG 知识库管理系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Streamlit Cloud 密钥配置（两个 Key）=====
import os as _os
_embedding_key = ""
_chat_key = ""
try:
    _embedding_key = st.secrets.get("DASHSCOPE_API_KEY", "")
    _chat_key = st.secrets.get("DASHSCOPE_CHAT_KEY", "")
    if not _chat_key:
        _chat_key = _embedding_key
    _os.environ["DASHSCOPE_API_KEY"] = _embedding_key
    _os.environ["DASHSCOPE_CHAT_KEY"] = _chat_key
except Exception:
    _embedding_key = _os.environ.get("DASHSCOPE_API_KEY", "")
    _chat_key = _os.environ.get("DASHSCOPE_CHAT_KEY", _embedding_key)

import config
from rag import RagService
from knowledge_base import KnowledgeBaseService
from services.auth import check_login
from services.users import register, login, get_user_history_dir
from services.file_parser import FileParser

# ===== 会话状态初始化 =====
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if "user_logged_in" not in st.session_state:
    st.session_state["user_logged_in"] = False

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "login"

if "rag" not in st.session_state:
    st.session_state["rag"] = RagService()

if "server" not in st.session_state:
    st.session_state["server"] = KnowledgeBaseService()


# ===== 工具函数 =====
def capture(generator, cache_list):
    """流式获取生成器内容并缓存到列表"""
    for chunk in generator:
        cache_list.append(chunk)
        yield chunk


def get_session_config(username: str) -> dict:
    """动态构建会话配置"""
    return {
        "configurable": {
            "session_id": f"user:{username}"
        }
    }


# ===== 侧边栏导航 =====
with st.sidebar:
    st.title("📚 RAG 知识库系统")
    st.caption("基于 RAG 的智能知识管理平台")

    st.divider()

    # 用户登录状态
    if st.session_state["user_logged_in"] and st.session_state["current_user"]:
        st.success(f"👤 {st.session_state['current_user']}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state["user_logged_in"] = False
            st.session_state["current_user"] = None
            st.session_state["current_page"] = "login"
            st.session_state.pop("qa_messages", None)
            st.toast("已退出登录")
            st.rerun()
    else:
        st.info("请先登录")

    st.divider()
    st.subheader("🧭 导航")

    # 智能问答按钮
    qa_label = "💬 智能问答"
    if st.button(qa_label, use_container_width=True, disabled=not st.session_state["user_logged_in"]):
        st.session_state["current_page"] = "qa"
        st.rerun()

    # 后台管理按钮（仅管理员可见）
    if st.session_state["admin_logged_in"]:
        admin_label = "🔒 后台管理"
        if st.button(admin_label, use_container_width=True):
            st.session_state["current_page"] = "admin"
            st.rerun()

    st.divider()
    st.caption(f"Embed: {'OK' if _embedding_key else 'NO'} | Chat: {'OK' if _chat_key else 'NO'}")
    st.caption("v3.0 · 2026")


# ===== 页面路由变量 =====
_current = st.session_state["current_page"]
_admin_logged = st.session_state["admin_logged_in"]
_user_logged = st.session_state["user_logged_in"]
_current_user = st.session_state.get("current_user")

# ===== 页面 0：登录/注册 =====
if _current == "login":
    st.title("🔐 用户登录")
    st.caption("欢迎使用 RAG 知识库问答系统")
    st.divider()

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    success, message = login(username, password)
                    if success:
                        st.session_state["user_logged_in"] = True
                        st.session_state["current_user"] = username
                        st.session_state["current_page"] = "qa"
                        # 初始化用户会话历史
                        if "qa_messages" not in st.session_state:
                            st.session_state["qa_messages"] = [
                                {"role": "assistant", "content": f"欢迎来到智能客服系统，{username}！请输入您的问题。"}
                            ]
                        st.session_state["session_id"] = str(uuid.uuid4())[:8]
                        st.success("登录成功，正在跳转...")
                        st.rerun()
                    else:
                        st.error(message)

    with tab_register:
        with st.form("register_form"):
            st.caption("注册后即可使用智能问答功能")
            new_username = st.text_input("用户名")
            new_password = st.text_input("密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            submitted = st.form_submit_button("注册", use_container_width=True)

            if submitted:
                if not new_username or not new_password:
                    st.error("请输入用户名和密码")
                elif new_password != confirm_password:
                    st.error("两次输入的密码不一致")
                elif len(new_username) < 2:
                    st.error("用户名至少2个字符")
                else:
                    success, message = register(new_username, new_password)
                    if success:
                        st.success(message)
                        st.info("请使用新账号登录")
                    else:
                        st.error(message)


# ===== 页面 1：智能问答（需登录）=====
elif _current == "qa" and _user_logged:
    st.title("💬 智能问答")
    st.caption(f"当前用户: {_current_user} | 基于知识库的 RAG 智能问答系统")
    st.divider()

    # 初始化用户会话历史
    if "qa_messages" not in st.session_state:
        st.session_state["qa_messages"] = [
            {"role": "assistant", "content": f"欢迎来到智能客服系统，{_current_user}！请输入您的问题。"}
        ]
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())[:8]

    # 显示问答侧边栏信息
    with st.sidebar:
        st.subheader("📋 会话信息")
        st.caption(f"会话 ID: `{st.session_state['session_id']}`")
        total_questions = len(
            [m for m in st.session_state["qa_messages"] if m["role"] == "user"]
        )
        total_reply_chars = sum(
            len(m["content"])
            for m in st.session_state["qa_messages"]
            if m["role"] == "assistant"
        )
        st.caption(f"本轮提问: {total_questions} 次")
        st.caption(f"回复总字数: {total_reply_chars}")

        st.subheader("⚙️ 知识库信息")
        st.caption(f"嵌入模型: {config.embedding_model_name}")
        st.caption(f"对话模型: {config.chat_model_name}")

        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state["qa_messages"] = [
                {"role": "assistant", "content": f"对话已清空，{_current_user}！请输入您的问题。"}
            ]
            st.session_state["session_id"] = str(uuid.uuid4())[:8]
            st.toast("对话已清空", icon="🧹")
            st.rerun()

    # 显示聊天历史
    for message in st.session_state["qa_messages"]:
        st.chat_message(message["role"]).write(message["content"])

    # 聊天输入
    prompt = st.chat_input(placeholder="请输入您的问题，按 Enter 发送...")

    if prompt:
        st.chat_message("user").write(prompt)
        st.session_state["qa_messages"].append({"role": "user", "content": prompt})

        ai_res_list = []
        try:
            with st.spinner("AI 思考中..."):
                res_stream = st.session_state["rag"].chain.stream(
                    {"input": prompt},
                    get_session_config(_current_user)
                )
                st.chat_message("assistant").write_stream(
                    capture(res_stream, ai_res_list)
                )
                st.session_state["qa_messages"].append(
                    {"role": "assistant", "content": "".join(ai_res_list)}
                )
        except Exception as e:
            st.error(f"生成回复时出错，请重试。错误详情：{str(e)}")
            st.toast("回复生成失败", icon="❌")
            st.session_state["qa_messages"].pop()


# ===== 页面 2：管理员登录 =====
elif _current == "admin" and not _admin_logged:
    st.title("🔒 后台管理登录")
    st.caption("仅限管理员访问，请输入账号密码")
    st.divider()

    with st.form("admin_login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录", use_container_width=True)

        if submitted:
            if check_login(username, password):
                st.session_state["admin_logged_in"] = True
                st.success("登录成功，正在跳转...")
                st.rerun()
            else:
                st.error("用户名或密码错误，请重试")


# ===== 页面 3：后台管理（需要登录）=====
elif _current == "admin" and _admin_logged:
    st.title("📁 知识库管理")
    st.caption("上传文档到 RAG 向量知识库")
    st.divider()

    # 侧边栏展示知识库配置
    with st.sidebar:
        st.subheader("📋 知识库配置")
        st.caption(f"向量库路径: `{config.persist_directory}`")
        st.caption(f"嵌入模型: {config.embedding_model_name}")
        st.caption(f"分块大小: {config.chunk_size} 字符")
        st.caption(f"分块重叠: {config.chunk_overlap} 字符")

        st.divider()
        st.subheader("👥 用户管理")
        st.caption("用户注册后即可使用问答功能")
        st.caption(f"知识库共享，历史独立")

        st.divider()
        st.subheader("📊 本次会话上传记录")
        if st.session_state.get("upload_history"):
            for record in st.session_state["upload_history"]:
                st.caption(
                    f"{record['time']} · **{record['file']}** ({record['status']})"
                )
        else:
            st.caption("暂无上传记录")

    # ===== Tab 1：上传文件 =====
    tab_upload, tab_manage = st.tabs(["上传文件", "管理文件"])

    with tab_upload:
        ALLOWED_TYPES = ["txt", "md", "pdf", "docx", "csv", "xlsx"]
        upload_file = st.file_uploader(
            "上传知识库文件",
            type=ALLOWED_TYPES,
            accept_multiple_files=False,
            key="file_uploader",
        )

        if upload_file is None:
            st.info("请上传文件到知识库，或将文件拖拽到此区域")
            st.caption(f"支持格式：{' / '.join(ALLOWED_TYPES).upper()} | 最大文件：{config.MAX_FILE_SIZE_MB}MB")
        else:
            file_name = upload_file.name
            file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
            file_size_kb = upload_file.size / 1024

            if upload_file.size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
                st.error(f"文件过大（>{config.MAX_FILE_SIZE_MB}MB），请拆分后上传")
                st.stop()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("文件名称", file_name)
            col2.metric("文件格式", file_ext.upper())
            col3.metric("文件大小", f"{file_size_kb:.1f} KB")
            col4.metric("解析状态", "待解析")

            file_bytes = upload_file.getvalue()
            try:
                with st.spinner("正在解析文件内容..."):
                    text = FileParser.parse(file_bytes, file_name)
                col4.metric("解析状态", "解析成功")
            except Exception as parse_err:
                st.error(f"文件解析失败: {str(parse_err)}")
                st.stop()

            preview_len = min(len(text), 2000)
            with st.expander(f"预览文件内容（前 {preview_len} 字符）"):
                st.text(text[:preview_len] + ("\n..." if len(text) > preview_len else ""))

            with st.status("正在载入知识库...", expanded=True) as status:
                result = st.session_state["server"].upload_by_file(text, file_name)
                status.update(label="载入完成!", state="complete", expanded=False)

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

            if "upload_history" not in st.session_state:
                st.session_state["upload_history"] = []
            st.session_state["upload_history"].append({
                "file": file_name,
                "status": upload_status,
                "time": datetime.now().strftime("%H:%M:%S"),
            })

    with tab_manage:
        st.subheader("📄 知识库文件列表")

        file_list = st.session_state["server"].list_files()

        if not file_list:
            st.info("知识库中暂无文件")
        else:
            # 统计
            total_files = len(file_list)
            total_chunks = sum(f["chunks"] for f in file_list)
            st.caption(f"共 {total_files} 个文件，{total_chunks} 个文本块")

            # 全量删除按钮
            with st.expander("危险操作", expanded=False):
                st.warning("以下操作不可撤销，请谨慎操作")
                col_del_all, _ = st.columns([1, 3])
                with col_del_all:
                    if st.button("清空全部知识库", type="secondary", use_container_width=True):
                        st.session_state["confirm_clear_all"] = True

                if st.session_state.get("confirm_clear_all"):
                    st.error("确认要删除知识库中的全部文件吗？此操作不可撤销！")
                    col_yes, col_no, _ = st.columns([1, 1, 2])
                    with col_yes:
                        if st.button("确认清空", type="primary", use_container_width=True):
                            count = st.session_state["server"].delete_all()
                            st.session_state["confirm_clear_all"] = False
                            st.toast(f"已清空 {count} 个文本块", icon="🗑️")
                            st.rerun()
                    with col_no:
                        if st.button("取消", use_container_width=True):
                            st.session_state["confirm_clear_all"] = False
                            st.rerun()

            st.divider()

            # 逐个文件展示和删除
            for idx, f in enumerate(file_list):
                col_info, col_action = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{f['source']}**")
                    st.caption(f"上传时间: {f['create_time']} | 文本块: {f['chunks']} 个")
                with col_action:
                    if st.button("删除", key=f"del_{idx}", use_container_width=True):
                        count = st.session_state["server"].delete_by_source(f["source"])
                        st.toast(f"已删除 {f['source']}（{count} 个文本块）", icon="🗑️")
                        st.rerun()
                st.divider()
