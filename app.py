from datetime import datetime, timedelta, timezone
import streamlit as st
import pandas as pd
from datetime import date
from streamlit_calendar import calendar
import os
import sqlite3

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from io import BytesIO

FILE = "child_ben_log.csv"
MED_FILE = "medicine_log.csv"
DB_FILE = "poop_log.db"

if not os.path.exists(FILE):
    pd.DataFrame(columns=[
        "日時",
        "硬さ",
        "量",
        "色",
        "出血",
        "腹痛",
        "排便痛",
        "メモ"
    ]).to_csv(FILE, index=False)

if not os.path.exists(MED_FILE):
    pd.DataFrame(columns=[
        "日付",
        "薬量",
        "メモ"
    ]).to_csv(MED_FILE, index=False)

# SQLiteデータベースの初期化
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS poop_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT,
        hardness INTEGER,
        amount TEXT,
        color TEXT,
        blood BOOLEAN,
        memo TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS medicine_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        medicine_amount TEXT,
        memo TEXT
    )
''')

conn.commit()
# conn.close()

if not os.path.exists(FILE):
    pd.DataFrame(columns=[
        "日時",
        "硬さ",
        "量",
        "色",
        "出血",
        "腹痛",
        "排便痛",
        "メモ"
    ]).to_csv(FILE, index=False)
if not os.path.exists(MED_FILE):

    pd.DataFrame(columns=[
        "日付",
        "薬量",
        "メモ"
    ]).to_csv(MED_FILE, index=False)

st.set_page_config(
    page_title="幼児 排便記録",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("## 🌱 幼児 排便記録")

tab1, tab2 = st.tabs([" 排便記録", "💊 薬記録"])

with tab1:

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

    med_df = pd.read_csv(MED_FILE)

    med_dates = set(
    pd.to_datetime(
        med_df["日付"],
        errors="coerce"
    )
        .dropna()
        .dt.strftime("%Y-%m-%d")
    )

    poop_dates = set()

    # 排便記録イベント
    for _, row in df.iterrows():

        poop_date = pd.to_datetime(
            row["日時"],
            errors="coerce"
        )

        if pd.notna(poop_date):
            poop_date = poop_date.strftime("%Y-%m-%d")

            poop_dates.add(poop_date)

            events.append({
                "title": f"{row['硬さ']} / {row['量']}",
                "start": poop_date
            })

    # 薬だけの日イベント
    for med_date in med_dates:
        events.append({
            "title": "💊",
            "start": med_date
        })

    calendar_options = {
        "initialView": "dayGridMonth",
        "locale": "ja",
        "height": 650,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": ""
        }
    }

    calendar(
        events=events,
        options=calendar_options,
        key="poop_calendar"
    )
    today = datetime.now().strftime("%Y-%m-%d")

    today_df = df[
        pd.to_datetime(df["日時"], errors="coerce").dt.strftime("%Y-%m-%d") == today
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
                "メモ": memo
            }

            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            c.execute("""
            INSERT INTO poop_logs
            (date_time, hardness, amount, color, blood, memo)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                now,
                hardness,
                amount,
                color,
                blood,
                memo
            ))
            conn.commit()
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

        if "薬量" in filtered_df.columns:
            columns_to_show.insert(5, "薬量")
        display_df = display_df[columns_to_show]
        edited_df = st.data_editor(    
            display_df,
            use_container_width=True,
            num_rows="dynamic"
            )
        #if st.button("履歴を保存"):

        #   edited_df.to_csv(FILE, index=False)
        #   st.success("履歴を更新しました！")

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

        pdfmetrics.registerFont(
            UnicodeCIDFont("HeiseiKakuGo-W5")
        )
        doc = SimpleDocTemplate(buffer)
        elements = []

        # 表作成
        data = [["日付", "薬量", "減量メモ", "排便"]]

        # 排便データを日付ごとにまとめる
        df["日付"] = pd.to_datetime(
            df["日時"],
            errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        poop_grouped = {}

        for date_value, group in df.groupby("日付"):
            poop_list = []

            group = group.sort_values("日時")

            for _, row in group.iterrows():
                time_str = pd.to_datetime(
                    row["日時"],
                    errors="coerce"
                ).strftime("%H:%M")

                poop_list.append(
                    f"{time_str} 硬{row['硬さ']}/{row['量']}/{row['色']}"
                )

            poop_grouped[date_value] = "、".join(poop_list)

        # 薬データ読み込み
        med_df = pd.read_csv(MED_FILE)

        med_grouped = {}

        if not med_df.empty:
            for date_value, group in med_df.groupby("日付"):

                amount_list = []
                memo_list = []

                for _, row in group.iterrows():
                    amount_list.append(str(row["薬量"]))

                    if pd.notna(row["メモ"]) and str(row["メモ"]).strip():
                        memo_list.append(str(row["メモ"]))

                med_grouped[date_value] = {
                    "amount": " / ".join(amount_list),
                    "memo": " / ".join(memo_list)
                }
        # 全日付まとめ
        all_dates = sorted(
            set(poop_grouped.keys()) | set(med_grouped.keys()),
            reverse=True
        )

        for date_value in all_dates:
            medicine = med_grouped.get(
                date_value,
                {"amount": "", "memo": ""}
            )

            poop_text = poop_grouped.get(date_value, "")

            data.append([
                str(date_value),
                medicine["amount"],
                medicine["memo"],
                poop_text
            ])

        table = Table(
            data,
            colWidths=[80, 60, 100, 260]
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("FONTNAME", (0,0), (-1,-1), "HeiseiKakuGo-W5"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
        ]))

        elements.append(table)
        doc.build(elements)

        st.download_button(
            "PDFダウンロード",
            data=buffer.getvalue(),
            file_name="排便記録.pdf",
            mime="application/pdf"
        )
    st.subheader("💾 CSVバックアップ")

    with open(FILE, "rb") as file:

        st.download_button(
            label="CSVをダウンロード",
            data=file,
            file_name="排便記録_backup.csv",
            mime="text/csv",
            use_container_width=True,
            key="csv_download"
        )

with tab2:

    st.subheader("💊 薬記録")

    med_date = st.date_input("日付", value=date.today())

    medicine_amount = st.radio(
        "薬量",
        ["なし", "少", "普", "多"],
        horizontal=True
    )

    memo = st.text_input("メモ（任意）")

    if st.button("薬を保存"):

        new_med = {
            "日付": str(med_date),
            "薬量": medicine_amount,
            "メモ": memo
        }

        med_df = pd.read_csv(MED_FILE)
        med_df = pd.concat(
            [med_df, pd.DataFrame([new_med])],
            ignore_index=True
        )
        med_df.to_csv(MED_FILE, index=False)

        st.success("薬記録を保存しました")

    # 常時履歴表示
    med_df = pd.read_csv(MED_FILE)
    st.dataframe(med_df, use_container_width=True)
# CSVバックアップ
# -------------------
