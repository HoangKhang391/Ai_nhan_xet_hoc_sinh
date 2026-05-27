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

# --- HÀM TẢI LOGS VỀ CHO ADMIN XEM (ĐÃ SỬA LỖI CÚ PHÁP) ---
def tai_log_he_thong_online():
    if not supabase:
        return ["❌ Chưa kết nối được database để lấy Nhật ký hoạt động."]
    try:
        # Đã sửa lỗi: Dùng desc=True thay thế cho ascending=False để hợp quy chuẩn thư viện mới
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
            if "@" not in r_email or len(r_pass) < 4:
                st.warning("Vui lòng nhập đúng định dạng Gmail và mật khẩu từ 4 ký tự trở lên nha!")
            else:
                msg = gui_yeu_cau_duyet_online(r_email, r_pass)
                if "Chưa cấu hình" in msg or "Lỗi" in msg:
                    st.error(msg)
                else:
                    ghi_log_he_thong(r_email, "Gửi một yêu cầu đăng ký tài khoản mới.")
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
            ghi_log_he_thong(st.session_state['user_email'], "Đã đăng xuất khỏi hệ thống.")
            st.session_state["logged_in"] = False
            st.session_state["is_admin"] = False
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
            
        if st.session_state["is_admin"]:
            st.divider()
            st.markdown("### 👑 MENU QUẢN LÝ GMAIL")
            if not supabase:
                st.warning("Chưa cấu hình khóa kết nối mạng trực tuyến.")
            else:
                try:
                    res_all = supabase.table("users").select("*").execute()
                    all_users = res_all.data
                    
                    users_pending = [u for u in all_users if u.get("status") == "pending"]
                    users_approved = [u for u in all_users if u.get("status") == "approved"]
                    
                    st.markdown("#### ⏳ Danh sách chờ duyệt")
                    if len(users_pending) == 0:
                        st.caption("🎉 Không có ai đang chờ duyệt!")
                    else:
                        for user in users_pending:
                            with st.expander(f"✉️ {user['email']}"):
                                col_d1, col_d2 = st.columns(2)
                                if col_d1.button("Duyệt ✅", key=f"ok_{user['id']}"):
                                    supabase.table("users").update({"status": "approved"}).eq("id", user['id']).execute()
                                    ghi_log_he_thong(st.session_state['user_email'], f"Đã duyệt tài khoản thành viên: {user['email']}")
                                    st.toast(f"Đã duyệt tài khoản {user['email']}")
                                    st.rerun()
                                if col_d2.button("Xóa ❌", key=f"del_{user['id']}"):
                                    supabase.table("users").delete().eq("id", user['id']).execute()
                                    ghi_log_he_thong(st.session_state['user_email'], f"Từ chối và xóa yêu cầu của: {user['email']}")
                                    st.toast(f"Đã xóa yêu cầu của {user['email']}")
                                    st.rerun()
                                    
                    st.write("")
                    st.markdown("#### 📋 Danh sách đã duyệt (Có thể kích)")
                    if len(users_approved) == 0:
                        st.caption("Chưa có tài khoản nào được duyệt hệ thống.")
                    else:
                        for user in users_approved:
                            col_mail, col_kick = st.columns([2.2, 1.3])
                            with col_mail:
                                st.text(user['email'])
                            with col_kick:
                                email_kiem_tra = str(user['email']).strip().lower()
                                if "admin" in email_kiem_tra or email_kiem_tra == "hasty_spider_admin":
                                    st.markdown('<span class="admin-badge">🔒 Admin</span>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<div class="kick-btn">', unsafe_allow_html=True)
                                    if st.button("Kích 🚪", key=f"kick_{user['id']}", type="secondary"):
                                        supabase.table("users").delete().eq("id", user['id']).execute()
                                        ghi_log_he_thong(st.session_state['user_email'], f"💥 Đã thực hiện kích tài khoản: {user['email']}")
                                        st.toast(f"💥 Đã kích thành công: {user['email']}", icon="ℹ️")
                                        st.rerun()
                                    st.markdown('</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Lỗi tải danh sách quản lý: {str(e)}")

        st.divider()
        st.markdown("### 📋 Trạng thái câu mẫu")
        for mon, info in DANH_SACH_MON.items():
            if os.path.exists(info["file"]): st.success(f"✅ {mon}")
            else: st.error(f"❌ {mon} (Thiếu file {info['file']})")
        st.divider()
        uploaded_bank_override = st.file_uploader("Cập nhật file mẫu riêng:", type=["xlsx"])

    # --- KHU VỰC THỂ HIỆN LỊCH SỬ HOẠT ĐỘNG (ĐỒNG BỘ ONLINE THỜI GIAN THỰC) ---
    if st.session_state["is_admin"]:
        st.markdown("### 🖥️ Lịch sử hoạt động của hệ thống (Đồng bộ thời gian thực từ Database)")
        
        # Cấu hình tự động quét và tải log mới từ database lên màn hình admin sau mỗi 5 giây
        st_autorefresh(interval=5000, limit=2000, key="admin_log_refresh")
        
        logs_he_thong_hien_tai = tai_log_he_thong_online()
        logs_html = "<br>".join(logs_he_thong_hien_tai)
        st.markdown(f'<div class="log-container">{logs_html}</div>', unsafe_allow_html=True)
        st.write("")

    # --- KHU VỰC CHỨC NĂNG CHÍNH CỦA USER THƯỜNG VÀ ADMIN ---
    st.markdown("### 📤 Bước 1: Tải lên file danh sách lớp học")
    uploaded_file = st.file_uploader("", type=["xlsx", "xlsm"])

    def tinh_do_trung_lap(cau1, cau2):
        words1 = set(cau1.lower().split())
        words2 = set(cau2.lower().split())
        if not words1 or not words2: return 0.0
        return len(words1.intersection(words2)) / max(len(words1), len(words2))

    def goi_ai_paraphrase(cau_goc, lich_su_gan_nhat):
        try:
            system_instr = (
                "Bạn là giáo viên tiểu học Việt Nam.\n"
                "Nhiệm vụ: Viết lại câu nhận xét được cho bằng từ đồng nghĩa hoặc đảo vế khéo léo.\n"
                "YÊU CẦU:\n"
                "- CHỈ trả về duy nhất 1 câu bắt đầu bằng chữ 'Em'.\n"
                "- TUYỆT ĐỐI KHÔNG thêm lời dẫn giải, không giải thích, không viết thêm ký tự khác."
            )
            cam_trung = " ; ".join(lich_su_gan_nhat[-5:]) if lich_su_gan_nhat else "Không có"
            prompt = f"Hãy viết lại câu này một cách khác biệt:\n'{cau_goc}'\nTránh trùng lặp với các câu này: {cam_trung}"
            
            resp = requests.post("http://localhost:11434/api/chat", json={
                "model": "qwen2.5:1.5b",
                "messages": [{"role": "system", "content": system_instr}, {"role": "user", "content": prompt}],
                "stream": False, "options": {"temperature": 0.85, "top_p": 0.9, "presence_penalty": 1.2}
            }, timeout=5)
            return resp.json().get("message", {}).get("content", "").strip()
        except: 
            return ""

    def code_tu_doi_tu_dong_nghia(cau):
        tu_dien = [
            ("trôi chảy", ["lưu loát", "rành mạch", "rất suôn sẻ", "tốt và trôi chảy"]),
            ("mạch lạc", ["gãy gọn", "rõ ràng cụ thể", "chặt chẽ", "khoa học"]),
            ("sáng tạo", ["độc đáo", "giàu ý tưởng", "đầy mới mẻ", "nhạy bén"]),
            ("chính xác", ["đúng yêu cầu", "chuẩn xác", "rất chính xác", "đúng đắn"]),
            ("tích cực", ["hăng hái", "chủ động", "tự giác tham gia", "năng nổ"]),
            ("hoàn thành tốt", ["đạt kết quả cao", "đáng khen ngợi", "có sự tiến bộ vượt bậc", "nắm rất vững kiến thức"]),
            ("hoàn thành", ["đạt yêu cầu môn học", "có nỗ lực hoàn thành tốt", "đạt chuẩn kiến thức"]),
            ("có ý thức học tập", ["chăm chỉ học tập", "chú ý nghe giảng", "có tinh thần tự học cao", "rất cố gắng"])
        ]
        random.shuffle(tu_dien)
        for goc, thay in tu_dien:
            if goc in cau.lower() and random.random() > 0.2:
                cau = re.sub(rf"(?i){goc}", random.choice(thay), cau, count=1)
        
        if "," in cau and random.random() > 0.5:
            parts = cau.split(",", 1)
            p1 = parts[0].strip().replace("Em ", "")
            p2 = parts[1].strip()
            if p2:
                p2 = p2[0].upper() + p2[1:]
                cau = f"Em {p2}, {p1.lower()}"
        return cau

    def lam_sach_nhan_xet(text, ten_hs):
        if not text or len(text.split()) < 3: return ""
        tu_cam = ["cảm ơn", "bạn đã", "câu hỏi", "tôi là", "trợ lý", "chúc bạn", "diễn đạt", "câu dịch", "dưới đây là", "câu gốc"]
        for tk in tu_cam:
            if tk in text.lower(): return ""
        text = re.sub(r'(?i).*nhận xét.*?:|.*mức.*?:|.*diễn đạt lại.*?:|.*câu diễn đạt khác.*?:|.*câu viết lại.*?:', '', text)
        text = text.replace("**", "").replace("*", "").replace('"', '').replace("'", "")
        if ten_hs: text = re.sub(rf"(?i){ten_hs}", "", text)
        text = text.strip(' ".,-–\n\r\t')
        if not text.lower().startswith("em"): text = "Em " + text
        text = text[0].upper() + text[1:]
        return text + "." if not text.endswith(".") else text

    if uploaded_file:
        file_bytes = uploaded_file.read()
        xl = pd.ExcelFile(io.BytesIO(file_bytes), engine='openpyxl')
        st.info(f"📁 File lớp học có các Sheet: {', '.join(xl.sheet_names)}")

        st.markdown("### 🖱️ Bước 2: Chọn môn học cần AI nhận xét")
        cols = st.columns(len(DANH_SACH_MON))
        
        mon_duoc_chon = None
        for i, (ten_mon, info) in enumerate(DANH_SACH_MON.items()):
            if cols[i].button(ten_mon): mon_duoc_chon = ten_mon

        if mon_duoc_chon:
            # GHI LOG CHẠY FILE LÊN CLOUD
            ghi_log_he_thong(st.session_state['user_email'], f"Kích hoạt chạy nhận xét môn: {mon_duoc_chon}")
            info = DANH_SACH_MON[mon_duoc_chon]
            if info["sheet"] not in xl.sheet_names:
                st.error(f"Trong file lớp học không có Sheet tên: '{info['sheet']}'")
            elif not os.path.exists(info["file"]) and not uploaded_bank_override:
                st.error(f"Thiếu file ngân hàng câu mẫu: {info['file']}")
            else:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=info["sheet"], dtype=str)
                df = df.fillna("") 
                
                col_ten_key = None
                col_muc_key = None
                
                for c in df.columns:
                    c_clean = str(c).strip().lower()
                    if "họ và tên" in c_clean or "ho va ten" in c_clean or c_clean == "tên" or c_clean == "ten":
                        col_ten_key = c
                    if "mức" in c_clean or "muc" in c_clean or "đánh giá" in c_clean or "danh gia" in c_clean:
                        col_muc_key = c
                
                if not col_ten_key: col_ten_key = 'Họ và tên' if 'Họ và tên' in df.columns else df.columns[1]
                if not col_muc_key: col_muc_key = 'Mức đạt được' if 'Mức đạt được' in df.columns else ('Mức' if 'Mức' in df.columns else df.columns[2])

                df_bank = pd.read_excel(uploaded_bank_override if uploaded_bank_override else info["file"], dtype=str)
                
                kho_mau = {"T": [], "H": [], "C": []}
                for _, r in df_bank.iterrows():
                    m = str(r.get('Mức đạt được', r.get('Mức', 'T'))).strip().upper()
                    c = str(r.get('Nội dung nhận xét', '')).strip()
                    if len(c.split()) > 2:
                        if "T" in m: kho_mau["T"].append(c)
                        elif "H" in m: kho_mau["H"].append(c)
                        else: kho_mau["C"].append(c)
                
                df['Nội dung nhận xét'] = ""
                
                progress_bar = st.progress(0)
                tat_ca_cau_da_tao = []
                
                for idx, row in df.iterrows():
                    ten = str(row.get(col_ten_key, '')).strip()
                    muc = str(row.get(col_muc_key, '')).strip().upper()
                    
                    if not ten or ten == "0" or len(ten) < 2:
                        df.at[idx, 'Nội dung nhận xét'] = ""
                        continue
                        
                    muc_key = "T"
                    if "H" in muc: muc_key = "H"
                    elif "C" in muc: muc_key = "C"
                    
                    danh_sach_phu_hop = kho_mau.get(muc_key, kho_mau["T"])
                    if not danh_sach_phu_hop: 
                        danh_sach_phu_hop = kho_mau["T"] if kho_mau["T"] else ["Em hoàn thành tốt nội dung môn học."]
                    
                    final_cmt = ""
                    
                    for _ in range(6):
                        cau_goc_ngau_nhien = random.choice(danh_sach_phu_hop)
                        raw = goi_ai_paraphrase(cau_goc_ngau_nhien, tat_ca_cau_da_tao)
                        raw = lam_sach_nhan_xet(raw, ten)
                        
                        if raw and len(raw.split()) > 3 and not any(tinh_do_trung_lap(raw, h) > 0.65 for h in tat_ca_cau_da_tao[-10:]):
                            final_cmt = raw
                            break
                            
                    if not final_cmt or len(final_cmt.split()) < 3: 
                        for _ in range(4):
                            cau_goc_ngau_nhien = random.choice(danh_sach_phu_hop)
                            test_code = lam_sach_nhan_xet(code_tu_doi_tu_dong_nghia(cau_goc_ngau_nhien), ten)
                            if test_code and len(test_code.split()) > 3 and not any(tinh_do_trung_lap(test_code, h) > 0.65 for h in tat_ca_cau_da_tao[-10:]):
                                final_cmt = test_code
                                break
                        
                    if not final_cmt or len(final_cmt.split()) < 3:
                        final_cmt = lam_sach_nhan_xet(code_tu_doi_tu_dong_nghia(random.choice(danh_sach_phu_hop)), ten)
                    if not final_cmt or len(final_cmt.split()) < 3:
                        final_cmt = lam_sach_nhan_xet(random.choice(danh_sach_phu_hop), ten)
                    
                    if not final_cmt or len(final_cmt.split()) < 3:
                        if muc_key == "T": final_cmt = "Em hoàn thành tốt nội dung môn học, có ý thức tự giác cao."
                        elif muc_key == "H": final_cmt = "Em hoàn thành đầy đủ nội dung môn học và các bài tập được giao."
                        else: final_cmt = "Em cần cố gắng nhiều hơn và chú ý nghe giảng trong giờ học."
                    
                    tat_ca_cau_da_tao.append(final_cmt)
                    df.at[idx, 'Nội dung nhận xét'] = final_cmt
                    
                    percent = int((idx + 1) / len(df) * 100)
                    progress_bar.progress((idx + 1) / len(df), text=f"⏳ Môn {mon_duoc_chon}: {percent}% | {ten}")

                # GHI LOG HOÀN THÀNH LÊN CLOUD
                ghi_log_he_thong(st.session_state['user_email'], f"🎉 Đã tạo xong nhận xét môn {mon_duoc_chon} với tổng số {len(df)} học sinh.")

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=info["sheet"], index=False)
                    worksheet = writer.sheets[info["sheet"]]
                    
                    col_idx = None
                    for cell in worksheet[1]:
                        if cell.value == 'Nội dung nhận xét':
                            col_idx = cell.column
                            break
                    if col_idx:
                        col_letter = worksheet.cell(row=1, column=col_idx).column_letter
                        worksheet.column_dimensions[col_letter].width = 55
                        for row_cells in worksheet.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                            for cell in row_cells:
                                cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='left')

                output.seek(0)
                st.success(f"🎉 Đã xong môn {mon_duoc_chon}! Cột nhận xét đã được điền đều.")
                st.download_button(f"📥 TẢI FILE KẾT QUẢ {mon_duoc_chon.upper()}", output, f"Nhan_Xet_{mon_duoc_chon.
