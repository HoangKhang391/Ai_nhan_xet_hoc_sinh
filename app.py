import streamlit as st
import pandas as pd
import requests
import io
import re
import os
import random
from datetime import datetime
from openpyxl.styles import Alignment
from supabase import create_client, Client # Thư viện kết nối database đám mây
from streamlit_autorefresh import st_autorefresh # Tự động làm mới bảng log cho Admin

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
    
    /* Custom css nhỏ riêng cho nút kích tài khoản trong Sidebar để giao diện cân đối hơn */
    .kick-btn button { height: 35px !important; font-size: 14px !important; padding: 0px !important; border-radius: 8px !important; }
    .log-container { background-color: #111827; color: #10B981; padding: 15px; border-radius: 12px; font-family: 'Courier New', Courier, monospace; font-size: 13px; max-height: 250px; overflow-y: auto; box-shadow: inset 0 2px 4px rgba(0,0,0,0.6); }
    .admin-badge { background-color: #FEF3C7; color: #D97706; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; border: 1px solid #FCD34D; display: inline-block; }
    </style>
""", unsafe_allow_html=True)

# --- ⚙️ ĐỒNG BỘ TRẠNG THÁI ĐĂNG NHẬP QUA URL ---
url_email = st.query_params.get("u", "")
url_admin = st.query_params.get("a", "0")

if "logged_in" not in st.session_state:
    if url_email:
        st.session_state["logged_in"] = True
        st.session_state["user_email"] = url_email
        st.session_state["is_admin"] = (url_admin == "1")
    else:
        st.session_state["logged_in"] = False
        st.session_state["user_email"] = ""
        st.session_state["is_admin"] = False

# --- HÀM GHI LỊCH SỬ THAO TÁC LÊN ĐÁM MÂY SUPABASE ---
def ghi_log_he_thong(user, hanh_dong):
    if supabase:
        try:
            # Đẩy trực tiếp log lên database online để tất cả các máy đều đồng bộ dữ liệu chung
            supabase.table("logs").insert({"user_email": user, "action": hanh_dong}).execute()
        except:
            pass

# --- HÀM TẢI LOGS VỀ CHO ADMIN XEM ---
def tai_log_he_thong_online():
    if not supabase:
        return ["❌ Chưa kết nối được database để lấy Nhật ký hoạt động."]
    try:
        res = supabase.table("logs").select("*").order("created_at", desc=True).limit(40).execute()
        danh_sach_log = []
        for item in res.data:
            try:
                tg_goc = item["created_at"].split(".")[0].replace("T", " ")
                tg_format = datetime.strptime(tg_goc, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            except:
                tg_format = datetime.now().strftime("%H:%M:%S")
            danh_sach_log.append(f"[{tg_format}] 👤 {item['user_email']} -> {item['action']}")
        return danh_sach_log if danh_sach_log else ["Chưa có thao tác nào được thực hiện..."]
    except Exception as e:
        return [f"❌ Lỗi tải lịch sử hoạt động: {str(e)}"]

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
                
                ghi_log_he_thong(u_email, "Đăng nhập vào hệ thống thành công.")
                
                st.query_params["u"] = u_email
                st.query_params["a"] = "1" if la_admin else "0"
                
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
            if "@" not in r_email or len
