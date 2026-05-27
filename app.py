import streamlit as st
import pandas as pd
import requests
import io
import re
import os
import random
from openpyxl.styles import Alignment
from supabase import create_client, Client # Thư viện kết nối database đám mây

# 1. Cấu hình giao diện Dashboard
st.set_page_config(page_title="AI Nhận Xét Học Sinh", page_icon="🎓", layout="wide")

# --- KẾT NỐI DATABASE SUPABASE ---
SUPABASE_URL = "https://nregdydyzpkpuzsaibrs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5yZWdkeWR5enBrcHV6c2FpYnJzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4NDY4MDEsImV4cCI6MjA5NTQyMjgwMX0.qBptrQFiCFgjLOUyaHEqsPS_hVF1c-PoR-E2Kwb0xUM"

loi_ket_noi_db = ""

@st.cache_resource
def init_supabase():
    global loi_ket_noi_db
    try:
        if not SUPABASE_URL or "ĐIỀN_URL" in SUPABASE_URL:
            loi_ket_noi_db = "URL chưa được cấu hình đúng."
            return None
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table("users").select("id").limit(1).execute()
        return client
    except Exception as e:
        loi_ket_noi_db = str(e)
        return None

supabase: Client = init_supabase()

# --- CSS ĐẸP VÀ CHỐNG DỊCH TRÌNH DUYỆT ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; translate: no !important; }
    .notranslate { translate: no !important; }
    [data-testid="stSidebar"] { min-width: 350px !important; max-width: 350px !important; }
    .main-header {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 30px; border-radius: 20px; color: white; text-align: center; margin-bottom: 40px;
        box-shadow: 0 10px 25px rgba(30, 58, 138, 0.2);
    }
    .stButton > button {
        width: 100%; height: 100px !important; border-radius: 18px !important;
        border: 1px solid #E5E7EB !important; background-color: white !important;
        color: #1F2937 !important; font-size: 18px !important; font-weight: 600 !important;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    .stButton > button:hover {
        border-color: #3B82F6 !important; color: #2563EB !important;
        background-color: #EFF6FF !important; transform: translateY(-5px);
        box-shadow: 0 15px 30px -5px rgba(59, 130, 246, 0.2) !important;
    }
    .stFileUploader { background-color: #F9FAFB; padding: 20px; border-radius: 20px; border: 2px dashed #D1D5DB; }
    .login-box { max-width: 450px; margin: 60px auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #F3F4F6; }
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO BIẾN TRẠNG THÁI ---
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "user_email" not in st.session_state: st.session_state["user_email"] = ""
if "is_admin" not in st.session_state: st.session_state["is_admin"] = False

# --- HÀM XỬ LÝ DATABASE ONLINE ---
def kiem_tra_dang_nhap_online(email, password):
    if email == "Hasty_Spider_admin" and password == "Bichthao@0312":
        return True, True
    if not supabase:
        return False, False
    try:
        res = supabase.table("users").select("*").eq("email", email.strip().lower()).eq("password", password).eq("status", "approved").execute()
        if len(res.data) > 0:
            return True, False
    except:
        pass
    return False, False

def gui_yeu_cau_duyet_online(email, password):
    if not supabase: 
        return f"Chưa cấu hình cơ sở dữ liệu. Chi tiết lỗi: {loi_ket_noi_db}"
    try:
        res = supabase.table("users").select("*").eq("email", email.strip().lower()).execute()
        if len(res.data) > 0:
            return "Gmail này đã tồn tại trên hệ thống rồi!"
        supabase.table("users").insert({"email": email.strip().lower(), "password": password, "status": "pending"}).execute()
        return "Gửi yêu cầu thành công! Vui lòng đợi duyệt nha."
    except Exception as e:
        return f"Lỗi gửi yêu cầu: {str(e)}"

# --- GIAO DIỆN MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ ---
if not st.session_state["logged_in"]:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🔐AI NHẬN XÉT HỌC SINH</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Đăng nhập", "📝 Đăng ký cấp quyền"])
    
    with tab1:
        u_email = st.text_input("Gmail của bạn:", key="login_email", placeholder="vi-du@gmail.com...")
        u_pass = st.text_input("Mật khẩu:", type="password", key="login_pass", placeholder="Nhập mật khẩu...")
        if st.button("XÁC NHẬN ĐĂNG NHẬP", key="btn_login", use_container_width=True):
            hop_le, la_admin = kiem_tra_dang_nhap_online(u_email, u_pass)
            if hop_le:
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = u_email
                st.session_state["is_admin"] = la_admin
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("❌ Gmail chưa được duyệt, sai mật khẩu hoặc gmail rồi!")
                if loi_ket_noi_db:
                    st.error(f"Chi tiết kỹ thuật: {loi_ket_noi_db}")
                
    with tab2:
        st.info("💡 Điền Gmail của bạn vào đây nhé.")
        r_email = st.text_input("Nhập Gmail đăng ký:", key="reg_email", placeholder="vi-du@gmail.com...")
        r_pass = st.text_input("Tạo mật khẩu đăng nhập:", type="password", key="reg_pass", placeholder="Nhập mật khẩu tự chọn...")
        if st.button("GỬI YÊU CẦU DUYỆT", key="btn_register", use_container_width=True):
            if "@" not in r_email or len(r_pass) < 4:
                st.warning("Vui lòng nhập đúng định dạng Gmail và mật khẩu từ 4 ký tự trở lên nha!")
            else:
                msg = gui_yeu_cau_duyet_online(r_email, r_pass)
                if "Chưa cấu hình" in msg or "Lỗi" in msg:
                    st.error(msg)
                else:
                    st.success(msg)
                
    st.markdown('</div>', unsafe_allow_html=True)

# --- GIAO DIỆN CHÍNH (ĐÃ ĐĂNG NHẬP THÀNH CÔNG) ---
else:
    st.markdown('<div class="main-header notranslate"><h1>🎓AI NHẬN XÉT HỌC SINH</h1><p>Phiên bản thử nghiệm version T1.0</p></div>', unsafe_allow_html=True)

    DANH_SACH_MON = {
        "📕 Tiếng việt": {"file": "databank_tieng_viet.xlsx", "sheet": "Tiếng việt"},
        "📐 Toán": {"file": "databank_toan.xlsx", "sheet": "Toán"},
        "🕊️ Đạo đức": {"file": "databank_dao_duc.xlsx", "sheet": "Đạo đức"},
        "🔬 Khoa học": {"file": "databank_khoa_hoc.xlsx", "sheet": "Khoa học"},
        "🗺️ Lịch sử - Địa lý": {"file": "databank_lsdl.xlsx", "sheet": "Lịch sử và Địa lý"},
        "💻 Tin Học - Công Nghệ": {"file": "databank_TH_CN.xlsx", "sheet": "TH-CN (Công nghệ)"},
        "⛺ Hoạt ĐỘng Trải nghiệm": {"file": "databank_hdtn.xlsx", "sheet": "Hoạt động trải nghiệm"}
    }

    with st.sidebar:
        st.markdown(f"👤 Tài khoản: **{st.session_state['user_email']}**")
        if st.button("🚪 Đăng xuất", key="btn_logout"):
            st.session_state["logged_in"] = False
            st.rerun()
            
        if st.session_state["is_admin"]:
            st.divider()
            st.markdown("### 👑 MENU QUẢN LÝ GMAIL")
            if not supabase:
                st.warning("Chưa cấu hình khóa kết nối mạng trực tuyến.")
            else:
                try:
                    res_pending = supabase.table("users").select("*").eq("status", "pending").execute()
                    users_list = res_pending.data
                    if len(users_list) == 0:
                        st.write("🎉 Không có ai đang chờ duyệt!")
                    else:
                        st.write(f"⏳ Có {len(users_list)} tài khoản đang chờ được xác nhận:")
                        for user in users_list:
                            with st.expander(f"✉️ {user['email']}"):
                                col_d1, col_d2 = st.columns(2)
                                if col_d1.button("Duyệt ✅", key=f"ok_{user['id']}"):
                                    supabase.table("users").update({"status": "approved"}).eq("id", user['id']).execute()
                                    st.rerun()
                                if col_d2.button("Xóa ❌", key=f"del_{user['id']}"):
                                    supabase.table("users").delete().eq("id", user['id']).execute()
                                    st.rerun()
                except:
                    st.error("Lỗi tải danh sách chờ duyệt trực tuyến.")

        st.divider()
        st.markdown("### ⚙️ Trạng thái câu mẫu")
        for mon, info in DANH_SACH_MON.items():
            if os.path.exists(info["file"]): st.success(f"✅ {mon}")
