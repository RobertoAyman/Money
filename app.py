import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="مدير المصاريف", page_icon="💰", layout="wide")

# تصميم CSS متوافق مع الوضع الليلي
st.markdown("""
    <style>
    .metric-card {
        background-color: #2b2b2b;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: center;
        border: 1px solid #444;
        margin-bottom: 15px;
    }
    .metric-title {
        color: #cccccc;
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #ffffff;
    }
    .metric-value.green { color: #2ecc71; }
    .metric-value.red { color: #e74c3c; }
    .metric-value.blue { color: #3498db; }
    .metric-value.orange { color: #f39c12; }
    
    div.row-widget.stRadio > div {
        display: flex;
        gap: 20px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# دوال الجهات والمعاملات
def get_entities():
    doc = db.collection('settings').document('options').get()
    return doc.to_dict().get('entities', ['أخرى']) if doc.exists else ['أخرى']

def add_entity(new_entity):
    entities = get_entities()
    if new_entity and new_entity not in entities:
        entities.append(new_entity)
        db.collection('settings').document('options').set({'entities': entities}, merge=True)
        return True
    return False

def add_transaction(t_type, category, entity, amount, t_date, notes):
    db.collection('transactions').add({
        'type': t_type,
        'category': category,
        'entity': entity,
        'amount': float(amount),
        'date': t_date.strftime("%Y-%m-%d"),
        'notes': notes,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

def get_transactions():
    docs = db.collection('transactions').order_by('date', direction=firestore.Query.DESCENDING).stream()
    data = [{'id': doc.id, **doc.to_dict()} for doc in docs]
    return pd.DataFrame(data)

# دوال هدف التحويش
def get_current_balance():
    doc = db.collection('settings').document('goal').get()
    return doc.to_dict().get('balance', 0.0) if doc.exists else 0.0

def update_balance(new_balance):
    db.collection('settings').document('goal').set({'balance': float(new_balance)}, merge=True)

today = date.today()

# --- القائمة الجانبية (Sidebar) ---
st.sidebar.header("🎯 رصيد التحويش الفعلي")
current_b = get_current_balance()
new_b = st.sidebar.number_input("الفلوس اللي معاك دلوقتي (ج.م):", min_value=0.0, value=float(current_b), step=1000.0)
if st.sidebar.button("تحديث الرصيد", type="primary"):
    update_balance(new_b)
    st.sidebar.success("تم تحديث رصيدك بنجاح!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🏢 إضافة جهة جديدة")
new_entity = st.sidebar.text_input("اكتب اسم الجهة:")
if st.sidebar.button("حفظ الجهة"):
    if add_entity(new_entity):
        st.sidebar.success(f"تم الإضافة!")
        st.rerun()
    else:
        st.sidebar.warning("موجودة أو فارغة.")

# --- واجهة عرض البيانات ---
st.title("💰 مدير المصاريف الشخصية")

df = get_transactions()
current_month = today.strftime("%Y-%m")
today_str = today.strftime("%Y-%m-%d")

total_saved, total_spent_month, spent_today = 0.0, 0.0, 0.0
daily_limit = 100.0

if not df.empty:
    df['month'] = df['date'].str[:7]
    df_month = df[df['month'] == current_month]
    
    income_month = df_month[df_month['type'] == 'دخل']['amount'].sum()
    total_spent_month = df_month[df_month['type'] == 'مصروف']['amount'].sum()
    total_saved = income_month - total_spent_month
    
    df_today = df[(df['date'] == today_str) & (df['type'] == 'مصروف')]
    spent_today = df_today['amount'].sum()

remaining_today = daily_limit - spent_today

# ملخص الشهر واليوم
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">فائض الشهر ده 📈</div><div class="metric-value {"green" if total_saved >= 0 else "red"}">{total_saved:,.0f} ج.م</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">مصروفات الشهر ده 📉</div><div class="metric-value red">{total_spent_month:,.0f} ج.م</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">متبقي من ليميت اليوم ⏱️</div><div class="metric-value {"green" if remaining_today >= 0 else "red"}">{remaining_today:,.0f} ج.م</div></div>', unsafe_allow_html=True)

st.markdown("---")

# --- قسم هدف التحويش ---
st.subheader("🎯 خطة تحويش 350 ألف (أبريل 2027)")

target_amount = 350000.0
target_date_goal = date(2027, 4, 1) # تاريخ الهدف
days_left = (target_date_goal - today).days

remaining_goal = target_amount - current_b
if remaining_goal < 0: remaining_goal = 0

daily_required = remaining_goal / days_left if days_left > 0 else 0
progress = (current_b / target_amount)
if progress > 1.0: progress = 1.0

# شريط التقدم
st.progress(progress)

g_col1, g_col2, g_col3, g_col4 = st.columns(4)
with g_col1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">معاك دلوقتي</div><div class="metric-value green">{current_b:,.0f} ج</div></div>', unsafe_allow_html=True)
with g_col2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للهدف</div><div class="metric-value orange">{remaining_goal:,.0f} ج</div></div>', unsafe_allow_html=True)
with g_col3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">الأيام المتبقية</div><div class="metric-value blue">{days_left} يوم</div></div>', unsafe_allow_html=True)
with g_col4:
    st.markdown(f'<div class="metric-card"><div class="metric-title">المطلوب يومياً</div><div class="metric-value red">{daily_required:,.0f} ج/يوم</div></div>', unsafe_allow_html=True)

st.markdown("---")

# --- تسجيل معاملة جديدة ---
st.subheader("➕ إضافة معاملة جديدة")

t_type_raw = st.radio("حدد نوع المعاملة:", ["🔴 مصروف", "🟢 دخل"], horizontal=True)
t_type = "مصروف" if "مصروف" in t_type_raw else "دخل"

col_a, col_b = st.columns(2)
with col_a:
    category = st.selectbox("البند:", ["مونتاج", "أكونتات", "فلوس خارجية", "راتب"])
    amount = st.number_input("المبلغ (ج.م):", min_value=0.0, step=10.0)

with col_b:
    entities_list = get_entities()
    entity = st.selectbox("الجهة:", entities_list)
    t_date = st.date_input("التاريخ:", value=today)

notes = st.text_input("ملاحظات (اختياري):")

if st.button("💾 حفظ المعاملة", use_container_width=True, type="primary"):
    if amount > 0:
        add_transaction(t_type, category, entity, amount, t_date, notes)
        st.success("تم الحفظ بنجاح! 🚀")
        st.rerun()
    else:
        st.warning("برجاء إدخال مبلغ أكبر من صفر.")

st.markdown("---")
st.subheader("📊 آخر المعاملات")
if not df.empty:
    display_df = df[['date', 'type', 'category', 'entity', 'amount', 'notes']].copy()
    display_df.columns = ['التاريخ', 'النوع', 'البند', 'الجهة', 'المبلغ', 'ملاحظات']
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("لا توجد معاملات مسجلة حتى الآن.")
