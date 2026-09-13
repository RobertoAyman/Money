import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="مدير المصاريف", page_icon="💰", layout="wide")

# تصميم CSS لتحسين الشكل (Modern UI)
st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        text-align: center;
        border: 1px solid #e9ecef;
    }
    .metric-title {
        color: #6c757d;
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: bold;
    }
    .metric-value.green { color: #28a745; }
    .metric-value.red { color: #dc3545; }
    /* تحسين شكل أزرار الاختيار */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row;
        gap: 20px;
        background-color: white;
        padding: 10px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# الاتصال بقاعدة بيانات Firebase
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # قراءة بيانات الاعتماد من إعدادات Streamlit
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# دوال مساعدة لجلب وحفظ البيانات
def get_entities():
    doc_ref = db.collection('settings').document('options')
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('entities', [])
    else:
        doc_ref.set({'entities': ['أخرى']})
        return ['أخرى']

def add_entity(new_entity):
    entities = get_entities()
    if new_entity and new_entity not in entities:
        entities.append(new_entity)
        db.collection('settings').document('options').set({'entities': entities})
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
    data = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        data.append(d)
    return pd.DataFrame(data)

# --- القائمة الجانبية (Sidebar) ---
st.sidebar.header("🏢 إضافة جهة جديدة")
new_entity = st.sidebar.text_input("اكتب اسم الجهة:")
if st.sidebar.button("حفظ الجهة", type="primary"):
    if new_entity:
        if add_entity(new_entity):
            st.sidebar.success(f"تمت إضافة '{new_entity}' بنجاح!")
            st.rerun()
        else:
            st.sidebar.warning("الجهة دي موجودة بالفعل أو الاسم فارغ.")

st.sidebar.markdown("---")
st.sidebar.info("الجهات اللي هتضيفها هنا هتظهرلك تلقائياً في قائمة 'الجهة' وأنت بتسجل المعاملات.")

# --- واجهة عرض البيانات (Dashboard) ---
st.title("💰 مدير المصاريف الشخصية")

df = get_transactions()

today = date.today()
current_month = today.strftime("%Y-%m")
today_str = today.strftime("%Y-%m-%d")

total_saved = 0.0
total_spent_month = 0.0
spent_today = 0.0
daily_limit = 100.0

if not df.empty:
    # حسابات الشهر الحالي
    df['month'] = df['date'].str[:7]
    df_month = df[df['month'] == current_month]
    
    income_month = df_month[df_month['type'] == 'دخل']['amount'].sum()
    total_spent_month = df_month[df_month['type'] == 'مصروف']['amount'].sum()
    total_saved = income_month - total_spent_month
    
    # حسابات اليوم
    df_today = df[(df['date'] == today_str) & (df['type'] == 'مصروف')]
    spent_today = df_today['amount'].sum()

remaining_today = daily_limit - spent_today

# عرض الكروت العلوية
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">تحويشة الشهر ده 📈</div>
            <div class="metric-value {'green' if total_saved >= 0 else 'red'}">{total_saved:,.2f} ج.م</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">مصروفات الشهر ده 📉</div>
            <div class="metric-value red">{total_spent_month:,.2f} ج.م</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    limit_color = 'green' if remaining_today >= 0 else 'red'
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">متبقي من ليميت اليوم (100 ج) ⏱️</div>
            <div class="metric-value {limit_color}">{remaining_today:,.2f} ج.م</div>
        </div>
    """, unsafe_allow_html=True)
    if remaining_today < 0:
        st.error(f"خلي بالك! إنت عديت الليميت اليومي بـ {abs(remaining_today):.2f} جنيه.")

st.markdown("<br>", unsafe_allow_html=True)

# --- تسجيل معاملة جديدة ---
st.subheader("➕ إضافة معاملة جديدة")

t_type = st.radio("حدد نوع المعاملة:", ["مصروف", "دخل"], horizontal=True)

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

# --- عرض المعاملات السابقة ---
st.subheader("📊 آخر المعاملات")
if not df.empty:
    display_df = df[['date', 'type', 'category', 'entity', 'amount', 'notes']].copy()
    display_df.columns = ['التاريخ', 'النوع', 'البند', 'الجهة', 'المبلغ', 'ملاحظات']
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("لا توجد معاملات مسجلة حتى الآن.")
