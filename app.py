import streamlit as st
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# إعداد الصفحة
st.set_page_config(page_title="إدارة الماليات - الإصدار السحابي", layout="wide")

# ربط الفايربيز بشكل آمن باستخدام أسرار Streamlit
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # هنا بنجيب البيانات السرية من إعدادات Streamlit
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

st.title("💰 لوحة تحكم الإدارة المالية (Firebase)")
st.markdown("تتبع دخلك، مصاريفك، أرباح المشاريع، وهدف التحويش.")

# --- القائمة الجانبية: إضافة معاملة ---
st.sidebar.header("➕ إضافة معاملة جديدة")
trans_type = st.sidebar.selectbox("النوع", ["دخل", "مصروف"])
category = st.sidebar.selectbox("البند / المجال", ["راتب الشركة", "مونتاج فيديو", "تسويق", "مشروع/عميل", "أقساط", "مصاريف شخصية"])
client_name = st.sidebar.text_input("اسم العميل أو الجهة (مثال: سرايا العرب)", value="")
amount = st.sidebar.number_input("المبلغ (جنيه)", min_value=0.0, step=100.0)
date = st.sidebar.date_input("التاريخ", datetime.now())
notes = st.sidebar.text_area("ملاحظات (مثال: دفعة أولى، مصاريف إعلانات)")

if st.sidebar.button("حفظ المعاملة"):
    # تجهيز البيانات للرفع على فايربيز
    doc_ref = db.collection("transactions").document()
    doc_ref.set({
        "type": trans_type,
        "category": category,
        "client": client_name.strip(),
        "amount": amount,
        "date": str(date),
        "notes": notes,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    st.sidebar.success("✅ تم الحفظ في الفايربيز بنجاح!")
    st.rerun()

# --- جلب البيانات من فايربيز ---
docs = db.collection("transactions").stream()
data = []
for doc in docs:
    doc_data = doc.to_dict()
    doc_data['id'] = doc.id
    data.append(doc_data)

df = pd.DataFrame(data)

if not df.empty:
    # --- الإحصائيات الرئيسية ---
    st.header("📊 نظرة عامة")
    total_income = df[df['type'] == 'دخل']['amount'].sum()
    total_expense = df[df['type'] == 'مصروف']['amount'].sum()
    net_balance = total_income - total_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الدخل", f"{total_income:,.2f} ج.م")
    col2.metric("إجمالي المصروفات والأقساط", f"{total_expense:,.2f} ج.م")
    col3.metric("الصافي (في جيبك)", f"{net_balance:,.2f} ج.م")

    st.divider()

    # --- متابعة هدف التحويش (350,000) ---
    st.subheader("🎯 متابعة هدف التحويش (350,000 جنيه حتى مايو 2027)")
    target_amount = 350000.0
    progress = min(max(net_balance / target_amount, 0.0), 1.0)
    st.progress(progress)
    st.write(f"المتبقي للوصول للهدف: **{target_amount - net_balance:,.2f}** جنيه")

    st.divider()

    # --- حساب أرباح المشاريع/العملاء (زي ما طلبت بالظبط) ---
    st.subheader("💼 صافي أرباح العملاء والمشاريع")
    st.write("هنا بيحسبلك كل عميل دخل منه كام، واتصرف عليه كام، والصافي بتاعك منه كام.")
    
    # تصفية المعاملات اللي ليها اسم عميل
    client_df = df[df['client'] != ''].copy()
    if not client_df.empty:
        # تجميع الدخل والمصروفات لكل عميل
        client_summary = client_df.groupby(['client', 'type'])['amount'].sum().unstack(fill_value=0).reset_index()
        
        # التأكد من وجود عواميد الدخل والمصروف
        if 'دخل' not in client_summary.columns: client_summary['دخل'] = 0
        if 'مصروف' not in client_summary.columns: client_summary['مصروف'] = 0
            
        client_summary['صافي الربح'] = client_summary['دخل'] - client_summary['مصروف']
        client_summary.rename(columns={'client': 'العميل / المشروع'}, inplace=True)
        st.dataframe(client_summary, use_container_width=True)
    else:
        st.info("لا توجد بيانات مسجلة بأسماء عملاء حتى الآن.")

    st.divider()

    # --- سجل المعاملات بالكامل مع إمكانية الحذف ---
    st.subheader("📋 السجل الكامل")
    st.dataframe(df[['date', 'type', 'category', 'client', 'amount', 'notes']], use_container_width=True)
    
    st.sidebar.divider()
    st.sidebar.header("🗑️ حذف معاملة")
    # عمل قائمة للمسح بشكل يسهل قراءته
    delete_options = {f"{row['date']} - {row['type']} - {row['amount']}ج": row['id'] for index, row in df.iterrows()}
    selected_to_delete = st.sidebar.selectbox("اختر المعاملة لحذفها", ["اختر..."] + list(delete_options.keys()))
    
    if selected_to_delete != "اختر..." and st.sidebar.button("حذف نهائي"):
        doc_id = delete_options[selected_to_delete]
        db.collection("transactions").document(doc_id).delete()
        st.sidebar.success("تم الحذف بنجاح!")
        st.rerun()

else:
    st.info("🚀 لا توجد أي معاملات مسجلة حتى الآن. أضف أول معاملة من القائمة الجانبية!")
