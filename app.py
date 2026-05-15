from datetime import datetime, timedelta, timezone
import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from io import BytesIO

FILE = "child_ben_log.csv"
if not os.path.exists(FILE):
    pd.DataFrame(columns=[
        "日時",
        "硬さ",
        "量",
        "色",
        "出血",
        "薬量",
        "メモ"
    ]).to_csv(FILE, index=False)

st.set_page_config(
    page_title="幼児 排便記録",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("## 🌱 幼児 排便記録")

# データ読み込み
if os.path.exists(FILE):
    df = pd.read_csv(FILE)
else:
    df = pd.DataFrame(columns=["日時","硬さ","量","色","出血","薬量","メモ"])

# -------------------
# カレンダー表示（フォームの外）
# -------------------
st.subheader("📅 排便カレンダー")

events = []
for _, row in df.iterrows():
    events.append({
    "title": f"{'🔴' if str(row['出血']) == 'True' else '🟢'} {row['硬さ']} / {row['量']}",
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
today = datetime.now().strftime("%Y-%m-%d")

today_df = df[
    pd.to_datetime(df["日時"]).dt.strftime("%Y-%m-%d") == today
]

if today_df.empty:
    st.warning("今日はまだ記録されていません")
else:
    st.success("今日は記録済みです")

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
    medicine = st.radio(
        "薬量",
        [
            "なし",
            "1/4",
            "半分",
            "3/4",
            "1包"
        ],
        horizontal=True
    )
    memo = st.text_area("メモ")

    submitted = st.form_submit_button(
    "記録する",
    use_container_width=True
    )

    if submitted:
        new_data = {
            "日時": record_datetime.strftime("%Y-%m-%d %H:%M"),
            "硬さ": hardness,
            "量": amount,
            "色": color,
            "出血": blood,
            "薬量": medicine,
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

filtered_df["日時"] = pd.to_datetime(
    filtered_df["日時"],
    errors="coerce"
)

if period != "全期間":

    days = int(period.replace("日", ""))

    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)

    filtered_df = filtered_df[
        filtered_df["日時"] >= cutoff
    ]
st.subheader("排便記録")

if not filtered_df.empty:
    display_df = filtered_df.sort_values("日時", ascending=False).copy()

    display_df["出血"] = display_df["出血"].fillna(False)

    display_df["出血"] = display_df["出血"].apply(
        lambda x: "🔴あり" if str(x) == "True" else ""
    )

    columns_to_show = ["日時", "硬さ", "量", "色", "出血", "メモ"]

    if "薬量" in display_df.columns:
        columns_to_show.insert(5, "薬量")

    display_df = display_df[columns_to_show]
    edited_df = st.data_editor(
    
        display_df,
        use_container_width=True,
        num_rows="dynamic"
    )
    if st.button("履歴を保存"):

        edited_df.to_csv(FILE, index=False)

        st.success("履歴を更新しました！")

    st.subheader("記録削除")

    delete_index = st.selectbox(
        "削除する記録を選択",
        df.index,
        format_func=lambda x:
            f"{df.loc[x, '日時']} / 硬さ:{df.loc[x, '硬さ']} / 量:{df.loc[x, '量']}"
    )

    if st.button("この記録を削除", use_container_width=True):
        df = df.drop(delete_index)
        df.to_csv(FILE, index=False)
        st.success("削除しました！")

else:
    st.info("まだ記録がありません")

st.subheader("📄 診察用PDF")

if st.button("PDFを作成"):

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    pdfmetrics.registerFont(
        UnicodeCIDFont('HeiseiKakuGo-W5')
    )

    styles['Title'].fontName = 'HeiseiKakuGo-W5'
    styles['BodyText'].fontName = 'HeiseiKakuGo-W5'
    elements = []

    elements.append(
        Paragraph("排便記録", styles['Title'])
    )

    start_date = filtered_df["日時"].min()
    end_date = filtered_df["日時"].max()

    period_text = (
        f"対象期間: "
        f"{start_date.strftime('%Y/%m/%d')} "
        f"〜 "
        f"{end_date.strftime('%Y/%m/%d')}"
    )

    elements.append(
        Paragraph(period_text, styles['BodyText'])
    )

    elements.append(Spacer(1, 10))

    pdf_df = filtered_df.sort_values("日時")

    data = [
        ["日時", "硬さ", "量", "色", "薬量", "メモ"]
    ]

    for _, row in pdf_df.iterrows():

        medicine = row["薬量"] if pd.notna(row["薬量"]) else ""
        memo = row["メモ"] if pd.notna(row["メモ"]) else ""

        data.append([
            str(row["日時"]),
            str(row["硬さ"]),
            str(row["量"]),
            str(row["色"]),
            str(medicine),
            str(memo)
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("FONTNAME", (0,0), (-1,-1), "HeiseiKakuGo-W5"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ]))

    elements.append(table)

    doc.build(elements)

    pdf = buffer.getvalue()

    st.download_button(
        label="PDFダウンロード",
        data=pdf,
        file_name="排便記録.pdf",
        mime="application/pdf"
    )
# -------------------
# CSVバックアップ
# -------------------

st.subheader("💾 CSVバックアップ")

with open(FILE, "rb") as file:

    st.download_button(
        label="CSVをダウンロード",
        data=file,
        file_name="排便記録_backup.csv",
        mime="text/csv",
        use_container_width=True
    )    