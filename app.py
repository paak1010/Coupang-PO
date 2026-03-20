import streamlit as st
import pandas as pd
from datetime import datetime

st.title("📦 쿠팡 발주서 LOT 자동 할당 도구")
st.markdown("---")

# 파일 업로드
uploaded_order = st.file_uploader("1. 쿠팡 서식파일(수주업로드) 업로드", type=['csv', 'xlsx'])
uploaded_stock = st.file_uploader("2. 재고 파일(Sheet1) 업로드", type=['csv', 'xlsx'])

if uploaded_order and uploaded_stock:
    # 데이터 읽기
    df_upload = pd.read_csv(uploaded_order) if uploaded_order.name.endswith('.csv') else pd.read_excel(uploaded_order)
    df_stock = pd.read_csv(uploaded_stock) if uploaded_stock.name.endswith('.csv') else pd.read_excel(uploaded_stock)

    if st.button("LOT 할당 시작"):
        # 전처리: 유효일자 기준 정렬 (FEFO)
        df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
        df_stock = df_stock.sort_values(by=['상품', '유효일자']).reset_index(drop=True)
        
        df_upload['LOT'] = ""
        df_upload['유효일자'] = ""

        # 로직 실행
        for index, row in df_upload.iterrows():
            mecode = row['MECODE']
            order_qty = row['수량']
            
            if pd.isna(mecode) or order_qty <= 0:
                continue
                
            # 해당 상품의 잔여 재고 확인
            mask = (df_stock['상품'] == mecode) & (df_stock['합계수량'] >= order_qty)
            available_lots = df_stock[mask]
            
            if not available_lots.empty:
                # 가장 빠른 유효기간의 LOT 하나만 선택
                first_lot_idx = available_lots.index[0]
                s_row = available_lots.loc[first_lot_idx]
                
                # 할당 및 재고 차감
                df_upload.at[index, 'LOT'] = s_row['화주LOT']
                df_upload.at[index, '유효일자'] = s_row['유효일자'].strftime('%Y-%m-%d')
                df_stock.at[first_lot_idx, '합계수량'] -= order_qty

        st.success("할당 완료!")
        
        # 결과 다운로드 버튼
        csv = df_upload.to_csv(index=False).encode('utf-8-sig')
        st.download_button("결과 파일 다운로드 (CSV)", data=csv, file_name="쿠팡_수주업로드_완료.csv")
