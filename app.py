import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import pandas as pd

st.set_page_config(page_title="مدير المصاريف", page_icon="💳", layout="wide")

# CSS بتصميم عصري (Dark Fintech Theme)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1a1a24, #252532);
        padding: 25px 20px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        text-align: center;
        border: 1px solid #333344;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 20px;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
        border-color: #444455;
    }
    
    .metric-title {
        color: #9ea3b0;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }
    
    .metric-value {
        font-size: 26px;
        font-weight: 900;
        color: #ffffff;
    }
    
    .entity-card {
        background: #1e1e2d;
        padding: 20px;
        border-radius: 12px;
        border-right: 5px solid #00b0ff;
        margin-bottom: 15px;
    }
    
    .text-green { color: #00e676; }
    .text-red { color: #ff1744; }
    .text-blue { color: #00b0ff; }
    .text-orange { color: #ff9100; }
    .text-purple { color: #d500f9; }
    
    div[data-testid="stRadio"] > div {
        background: #1a1a24;
        padding: 10px 20px;
        border-radius: 12px;
        border: 1px solid #333344;
        display: flex;
        gap: 20px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        font-weight: bold;
        padding-bottom: 10px;
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

# --- دوال قاعدة البيانات ---
def get_entities():
    docs = db.collection('entities').stream()
    return {doc.id: doc.to_dict() for doc in docs}

def add_entity_with_limit(name, limit):
    if name:
        db.collection('entities').document(name).set({
            'name': name,
            'limit': float(limit)
        })
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

def delete_all_data():
    for doc in db.collection('transactions').stream():
        db.collection('transactions').document(doc.id).delete()
    for doc in db.collection('entities').stream():
        db.collection('entities').document(doc.id).delete()
    for doc in db.collection('settings').stream():
        db.collection('settings').document(doc.id).delete()

# --- دوال الاستثمار ---
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
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=80)
    st.header("الإدارة والتحكم")
    st.markdown("---")
    
    st.subheader("🏢 إضافة جهة / أكونت")
    new_entity_name = st.text_input("اسم الجهة:")
    new_entity_limit = st.number_input("ميزانية الجهة (الليميت):", min_value=0.0, step=1000.0)
    if st.button("حفظ الجهة", use_container_width=True):
        if add_entity_with_limit(new_entity_name, new_entity_limit):
            st.success("تم الإضافة!")
            st.rerun()

    st.markdown("---")
    st.subheader("💸 إيداع سريع للتحويش")
    deposit_amount = st.number_input("المبلغ (ج.م):", min_value=0.0, step=500.0, key="deposit")
    if st.button("تأكيد الإيداع", type="primary", use_container_width=True):
        if deposit_amount > 0:
            new_balance = current_b + deposit_amount
            update_balance(new_balance)
            st.success(f"تم! رصيدك: {new_balance:,.0f} ج.م")
            st.rerun()
            
    st.markdown("---")
    st.subheader("⚙️ تعديل الرصيد الكلي يدوياً")
    manual_balance = st.number_input("الرصيد الفعلي:", min_value=0.0, value=float(current_b), step=1000.0, key="manual")
    if st.button("تحديث السجل", use_container_width=True):
        update_balance(manual_balance)
        st.success("تم التحديث!")
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ مسح جميع البيانات")
    del_pass = st.text_input("كلمة المرور:", type="password")
    if del_pass == "1234":
        if st.button("فرمتة النظام ⚠️", type="primary", use_container_width=True):
            delete_all_data()
            st.success("تم مسح الداتابيز بالكامل، اعمل ريفرش للصفحة!")
            st.rerun()

# --- جلب البيانات الأساسية ---
df = get_transactions()
entities_data = get_entities()
current_month = today.strftime("%Y-%m")

total_saved, total_spent_month, personal_spent_month = 0.0, 0.0, 0.0
personal_monthly_limit = 2500.0

if not df.empty:
    df['month'] = df['date'].str[:7]
    df_month = df[df['month'] == current_month]
    
    income_month = df_month[df_month['type'] == 'دخل']['amount'].sum()
    total_spent_month = df_month[df_month['type'] == 'مصروف']['amount'].sum()
    
    # حساب المصاريف الشخصية فقط
    personal_spent_month = df_month[(df_month['type'] == 'مصروف') & (df_month['category'] == 'مصاريف شخصية')]['amount'].sum()
    
    total_saved = income_month - total_spent_month

remaining_personal_limit = personal_monthly_limit - personal_spent_month

# --- واجهة التطبيق الرئيسية ---
st.title("محفظتي الذكية 🚀")

tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة القيادة", "🏢 حسابات الأكونتات", "🎯 خطة الاستثمار", "📝 المعاملات"])

# التبويب الأول: لوحة القيادة
with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">فائض الشهر</div><div class="metric-value {"text-green" if total_saved >= 0 else "text-red"}">{total_saved:,.0f} ج</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي مصروفات الشهر</div><div class="metric-value text-red">{total_spent_month:,.0f} ج</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">متبقي ليميت شخصي (2500ج)</div><div class="metric-value {"text-green" if remaining_personal_limit >= 0 else "text-red"}">{remaining_personal_limit:,.0f} ج</div></div>', unsafe_allow_html=True)

# التبويب الثاني: حسابات الأكونتات (الجهات)
with tab2:
    st.subheader("متابعة أرصدة وميزانيات الأكونتات")
    if not entities_data:
        st.info("لا توجد جهات مسجلة. قم بإضافة جهة من القائمة الجانبية.")
    else:
        for e_name, e_info in entities_data.items():
            e_limit = e_info.get('limit', 0)
            
            e_received = df[(df['entity'] == e_name) & (df['type'] == 'دخل')]['amount'].sum() if not df.empty else 0
            e_spent = df[(df['entity'] == e_name) & (df['type'] == 'مصروف')]['amount'].sum() if not df.empty else 0
            e_balance = e_received - e_spent
            
            st.markdown(f"""
            <div class="entity-card">
                <h4 style="color: #ffffff; margin-bottom: 15px;">🏢 {e_name}</h4>
                <div style="display: flex; justify-content: space-between;">
                    <div><span style="color: #9ea3b0;">الميزانية (الليميت):</span> <strong class="text-blue">{e_limit:,.0f} ج</strong></div>
                    <div><span style="color: #9ea3b0;">الوارد (الدفعات):</span> <strong class="text-green">{e_received:,.0f} ج</strong></div>
                    <div><span style="color: #9ea3b0;">المنصرف:</span> <strong class="text-red">{e_spent:,.0f} ج</strong></div>
                    <div><span style="color: #9ea3b0;">الرصيد في إيدك:</span> <strong class="{'text-green' if e_balance >= 0 else 'text-red'}" style="font-size: 18px;">{e_balance:,.0f} ج</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# التبويب الثالث: الاستثمار
with tab3:
    target_amount = 350000.0
    target_date_goal = date(2027, 4, 1)
    days_left = (target_date_goal - today).days
    remaining_goal = max(target_amount - current_b, 0)
    daily_required = remaining_goal / days_left if days_left > 0 else 0
    progress = min(current_b / target_amount, 1.0)
    
    st.progress(progress)
    
    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الأصول 💼</div><div class="metric-value text-green">{current_b:,.0f} ج</div></div>', unsafe_allow_html=True)
    with g_col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">الأرباح اليومية 📈</div><div class="metric-value text-purple">+{daily_profit:,.1f} ج</div></div>', unsafe_allow_html=True)
    with g_col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">المطلوب يومياً 🎯</div><div class="metric-value text-orange">{daily_required:,.0f} ج</div></div>', unsafe_allow_html=True)

# التبويب الرابع: تسجيل المعاملات
with tab4:
    with st.container():
        t_type_raw = st.radio("نوع الحركة:", ["🔴 سحب / مصروف", "🟢 إيداع / دخل"], horizontal=True)
        t_type = "مصروف" if "سحب" in t_type_raw else "دخل"

        col_a, col_b = st.columns(2)
        with col_a:
            category = st.selectbox("التصنيف:", ["مونتاج", "أكونتات", "فلوس خارجية", "راتب", "مصاريف شخصية"])
            amount = st.number_input("القيمة (ج.م):", min_value=0.0, step=50.0)

        with col_b:
            entities_list = ["أخرى"] + list(entities_data.keys())
            entity = st.selectbox("الجهة / الأكونت:", entities_list)
            t_date = st.date_input("التاريخ:", value=today)

        notes = st.text_input("ملاحظات إضافية:")

        if st.button("تأكيد العملية 💾", use_container_width=True, type="primary"):
            if amount > 0:
                add_transaction(t_type, category, entity, amount, t_date, notes)
                st.success("تم تسجيل الحركة بنجاح!")
                st.rerun()
            else:
                st.warning("المبلغ لازم يكون أكبر من صفر.")
                
    st.markdown("### سجل الحركة الأخير")
    if not df.empty:
        display_df = df[['date', 'type', 'category', 'entity', 'amount', 'notes']].copy()
        display_df.columns = ['التاريخ', 'النوع', 'البند', 'الجهة', 'المبلغ', 'الملاحظات']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
