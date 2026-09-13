import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import pandas as pd

st.set_page_config(page_title="مدير المصاريف", page_icon="💰", layout="wide")

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
        font-size: 15px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #ffffff;
    }
    .metric-value.green { color: #2ecc71; }
    .metric-value.red { color: #e74c3c; }
    .metric-value.blue { color: #3498db; }
    .metric-value.orange { color: #f39c12; }
    .metric-value.purple { color: #9b59b6; }
    
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

today = date.today()

def get_balance_info():
    doc = db.collection('settings').document('goal').get()
    if doc.exists:
        data = doc.to_dict()
        return data.get('balance', 0.0), data.get('last_update', today.strftime("%Y-%m-%d"))
    return 0.0, today.strftime("%Y-%m-%d")

def update_balance(new_balance):
    db.collection('settings').document('goal').set({
        'balance': float(new_balance),
        'last_update': today.strftime("%Y-%m-%d")
    }, merge=True)

base_b, last_update_str = get_balance_info()
last_update_date = datetime.strptime(last_update_str, "%Y-%m-%d").date()
days_passed = (today - last_update_date).days

if days_passed > 0:
    daily_rate = 0.18 / 365
    current_b = base_b * ((1 + daily_rate) ** days_passed)
    update_balance(current_b) 
else:
    current_b = base_b

daily_profit = current_b * (0.18 / 365) 

# --- القائمة الجانبية ---
st.sidebar.header("💸 إيداع في رصيد التحويش")
deposit_amount = st.sidebar.number_input("المبلغ اللي هتحوشه (ج.م):", min_value=0.0, step=500.0)
if st.sidebar.button("إضافة الإيداع", type="primary"):
    if deposit_amount > 0:
        new_balance = current_b + deposit_amount
        update_balance(new_balance)
        st.sidebar.success(f"عاش! رصيدك الكلي بقى {new_balance:,.0f} ج.م")
        st.rerun()
    else:
        st.sidebar.warning("اكتب مبلغ أكبر من صفر.")

st.sidebar.markdown("---")
st.sidebar.header("🏢 إضافة جهة جديدة")
new_entity = st.sidebar.text_input("اكتب اسم الجهة:")
if st.sidebar.button("حفظ الجهة"):
    if add_entity(new_entity):
        st.sidebar.success("تم الإضافة!")
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

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">فائض الشهر 📈</div><div class="metric-value {"green" if total_saved >= 0 else "red"}">{total_saved:,.0f} ج</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">مصروفات الشهر 📉</div><div class="metric-value red">{total_spent_month:,.0f} ج</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">متبقي من ليميت اليوم ⏱️</div><div class="metric-value {"green" if remaining_today >= 0 else "red"}">{remaining_today:,.0f} ج</div></div>', unsafe_allow_html=True)

st.markdown("---")

st.subheader("🎯 خطة الاستثمار لـ 350 ألف (أبريل 2027)")

target_amount = 350000.0
target_date_goal = date(2027, 4, 1)
days_left = (target_date_goal - today).days

remaining_goal = target_amount - current_b
if remaining_goal < 0: remaining_goal = 0

daily_required = remaining_goal / days_left if days_left > 0 else 0
progress = (current_b / target_amount)
if progress > 1.0: progress = 1.0

st.progress(progress)

g_col1, g_col2, g_col3, g_col4, g_col5 = st.columns(5)
with g_col1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">رصيدك الكلي</div><div class="metric-value green">{current_b:,.0f} ج</div></div>', unsafe_allow_html=True)
with g_col2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">عائدك اليومي 📈</div><div class="metric-value purple">+{daily_profit:,.1f} ج</div></div>', unsafe_allow_html=True)
with g_col3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للهدف</div><div class="metric-value orange">{remaining_goal:,.0f} ج</div></div>', unsafe_allow_html=True)
with g_col4:
    st.markdown(f'<div class="metric-card"><div class="metric-title">الأيام المتبقية</div><div class="metric-value blue">{days_left} يوم</div></div>', unsafe_allow_html=True)
with g_col5:
    st.markdown(f'<div class="metric-card"><div class="metric-title">المطلوب توفيره</div><div class="metric-value red">{daily_required:,.0f} ج/يوم</div></div>', unsafe_allow_html=True)

st.markdown("---")

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
