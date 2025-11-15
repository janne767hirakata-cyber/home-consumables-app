import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="家庭の消耗品管理", page_icon="🏠", layout="wide")

# --- 認証機能 ---
def login():
    st.title("🔐 家族専用ログイン")
    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if username == st.secrets["USERNAME"] and password == st.secrets["PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("ユーザー名またはパスワードが間違っています")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- データ管理 ---
FILE_PATH = "consumables.csv"
os.makedirs("images", exist_ok=True)

if os.path.exists(FILE_PATH):
    df = pd.read_csv(FILE_PATH)
    if "アラートしきい値" not in df.columns:
        df["アラートしきい値"] = 3
else:
    df = pd.DataFrame(columns=["名前", "数量", "カテゴリー", "期限", "備考", "画像", "アラートしきい値"])

st.title("🏠 家庭の消耗品管理アプリ（田口家）")

# --- 登録フォーム ---
st.subheader("消耗品を登録")
name = st.text_input("名前")
quantity = st.number_input("数量", min_value=1, step=1)
category = st.selectbox("カテゴリー", ["食品", "洗剤", "トイレットペーパー", "調味料", "その他"])

expiry_option = st.selectbox("使用期限の設定", ["日付を選択", "なし"])
expiry = ""
if expiry_option == "日付を選択":
    expiry = st.date_input("使用期限（賞味期限）").strftime("%Y-%m-%d")

note = st.text_area("備考")
alert_threshold = st.number_input("在庫アラートしきい値", min_value=1, value=3)
image_file = st.file_uploader("画像アップロード", type=["jpg", "png"])

if st.button("追加"):
    img_path = ""
    if image_file:
        img_path = f"images/{image_file.name}"
        with open(img_path, "wb") as f:
            f.write(image_file.read())
    new_data = pd.DataFrame([[name, quantity, category, expiry, note, img_path, alert_threshold]], columns=df.columns)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
    st.success(f"{name} を追加しました！")

# --- 検索機能 ---
st.subheader("検索・絞り込み")
search_name = st.text_input("名前で検索")
search_category = st.selectbox("カテゴリーで絞り込み", ["すべて"] + df["カテゴリー"].dropna().unique().tolist())

filtered_df = df.copy()
if search_name:
    filtered_df = filtered_df[filtered_df["名前"].fillna("").str.contains(search_name, case=False)]
if search_category != "すべて":
    filtered_df = filtered_df[filtered_df["カテゴリー"] == search_category]

# --- 自動削除オプション ---
auto_delete = st.checkbox("数量が0になったら自動削除", value=True)

# --- 商品一覧表示 ---
st.subheader("消耗品一覧")
for i, row in filtered_df.iterrows():
    st.markdown('<div style="background-color:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:15px; border:1px solid #ddd;">', unsafe_allow_html=True)
    cols = st.columns([1, 3, 2, 2, 1])
    with cols[0]:
        if isinstance(row["画像"], str) and os.path.exists(row["画像"]):
            st.image(row["画像"], width=100)
    with cols[1]:
        st.markdown(f"<h4>{row['名前']}</h4>", unsafe_allow_html=True)
        st.write(f"数量: {row['数量']} | カテゴリー: {row['カテゴリー']}")
        st.write(f"期限: {row['期限'] if row['期限'] else 'なし'} | 備考: {row['備考']}")
    # 減らす
    with cols[2]:
        current_qty = int(row["数量"]) if pd.notna(row["数量"]) else 1
        reduce_qty = st.number_input("減らす数量", min_value=1, max_value=max(current_qty, 1), value=1, key=f"reduce_qty_{i}")
        if st.button("減らす", key=f"reduce_btn_{i}"):
            df.at[i, "数量"] = max(0, df.at[i, "数量"] - reduce_qty)
            if auto_delete and df.at[i, "数量"] == 0:
                df = df.drop(i)
            df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
            st.rerun()
    # 増やす
    with cols[3]:
        add_qty = st.number_input("増やす数量", min_value=1, value=1, key=f"add_qty_{i}")
        if st.button("増やす", key=f"add_btn_{i}"):
            df.at[i, "数量"] = df.at[i, "数量"] + add_qty
            df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
            st.rerun()
    # 削除
    with cols[4]:
        if st.button("削除", key=f"delete_{i}"):
            confirm = st.checkbox("確認", key=f"confirm_{i}")
            if confirm:
                df = df.drop(i)
                df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- アラート ---
st.subheader("⚠ アラート")
today = datetime.today().date()
df["期限"] = pd.to_datetime(df["期限"], errors="coerce")

low_stock_items = df[df["数量"] <= df["アラートしきい値"]]
expired_items = df[df["期限"].notna() & (df["期限"] < pd.Timestamp(today))]

if not low_stock_items.empty:
    st.error("在庫が少ない消耗品があります！")
    st.table(low_stock_items[["名前", "数量", "カテゴリー", "アラートしきい値"]])

if not expired_items.empty:
    st.warning("期限切れの消耗品があります！")
    st.table(expired_items[["名前", "期限", "カテゴリー"]])

# --- Excel出力 ---
st.subheader("Excel出力")
if st.button("Excelに出力"):
    df.to_excel("consumables.xlsx", index=False)
    with open("consumables.xlsx", "rb") as f:
        st.download_button("Excelをダウンロード", f, file_name="consumables.xlsx")