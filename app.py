from datetime import datetime, timedelta, timezone
import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

FILE = "child_ben_log.csv"

st.set_page_config(page_title="幼児 排便記録", layout="centered")

st.title("🧸 幼児 排便記録アプリ")

# データ読み込み
if os.path.exists(FILE):
    df = pd.read_csv(FILE)
else:
    df = pd.DataFrame(columns=["日時","硬さ","量","色","出血","メモ"])

# -------------------
# カレンダー表示（フォームの外）
# -------------------
st.subheader("📅 排便カレンダー")

events = []
for _, row in df.iterrows():
    events.append({
    "title": f"{'🔴' if row['出血'] else '🟢'} {row['硬さ']} / {row['量']}",
    "start": row["日時"][:10]
    })
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ja",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": ""
    }
}

calendar(events=events, options=calendar_options)

# -------------------
# 入力フォーム
# -------------------
with st.form("record_form"):
    st.subheader("記録する")

    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)

    selected_date = st.date_input(
    "日付",
    value=now.date()
    )

    selected_time = st.time_input(
    "時刻",
    value=now.time()
    )

    record_datetime = datetime.combine(selected_date, selected_time)

    hardness = st.slider(
    "便スケール（1=コロコロ硬便 / 7=水様便）",
    1,
    7,
    4
    )
    amount = st.radio("量", ["少", "中", "多"])
    color = st.selectbox("色", ["黄", "茶", "濃茶", "黒", "緑"])
    blood = st.checkbox("出血あり")
    memo = st.text_input("メモ")

    submitted = st.form_submit_button("記録する")

    if submitted:
        new_data = {
            "日時": record_datetime.strftime("%Y-%m-%d %H:%M"),
            "硬さ": hardness,
            "量": amount,
            "色": color,
            "出血": blood,
            "メモ": memo
        }

        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        df.to_csv(FILE, index=False)
        st.success("記録しました！")

# -------------------
# 履歴
# -------------------

st.subheader("表示期間")

period = st.selectbox(

    "期間を選択",

    ["7日", "14日", "30日", "全期間"]

)

filtered_df = df.copy()

if period != "全期間":

    days = int(period.replace("日", ""))

    filtered_df["日時"] = pd.to_datetime(filtered_df["日時"])

    cutoff = datetime.now() - timedelta(days=days)

    filtered_df = filtered_df[filtered_df["日時"] >= cutoff]

st.subheader("履歴")

if not filtered_df.empty:
    display_df = filtered_df.sort_values("日時", ascending=False).copy()

    display_df["出血"] = display_df["出血"].apply(
        lambda x: "🔴あり" if x else ""
    )

    st.dataframe(
        display_df,
        use_container_width=True
    )

    st.line_chart(filtered_df["硬さ"])

else:
    st.info("まだ記録がありません")

st.subheader("📄 診察用PDF")

if st.button("PDFを作成"):

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph("排便記録", styles['Title'])
    )

    elements.append(Spacer(1, 12))

    for _, row in filtered_df.iterrows():

        text = (
            f"{row['日時']} / "
            f"便スケール:{row['硬さ']} / "
            f"量:{row['量']} / "
            f"色:{row['色']} / "
            f"出血:{row['出血']} / "
            f"メモ:{row['メモ']}"
        )

        elements.append(
            Paragraph(text, styles['BodyText'])
        )

        elements.append(Spacer(1, 6))

    doc.build(elements)

    pdf = buffer.getvalue()

    st.download_button(
        label="PDFダウンロード",
        data=pdf,
        file_name="排便記録.pdf",
        mime="application/pdf"
    )