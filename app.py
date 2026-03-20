import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="쿠팡 발주서 LOT 할당 (최종)", layout="wide")
st.title("📦 쿠팡 발주서 LOT 자동 할당 (단일 할당 & LOT 합산 로직)")

uploaded_file = st.file_uploader("쿠팡 서식 엑셀 파일(단일 파일)을 업로드하세요", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        if '서식(수주업로드)' in sheet_names and 'Sheet1' in sheet_names:
            df_upload = pd.read_excel(xls, sheet_name='서식(수주업로드)')
            df_stock = pd.read_excel(xls, sheet_name='Sheet1')
            
            if st.button("LOT 할당 시작"):
                # 1. 재고 데이터 정렬 (유효일자 순 -> LOT 순)
                df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
                df_stock = df_stock.sort_values(by=['상품', '유효일자', '화주LOT']).reset_index(drop=True)
                
                # 결과 열 초기화
                df_upload['LOT'] = ""
                df_upload['유효일자'] = ""

                # 2. 할당 로직 (단일 할당 원칙)
                for index, row in df_upload.iterrows():
                    mecode = row['MECODE']
                    order_qty = row['수량']
                    
                    if pd.isna(mecode) or order_qty <= 0:
                        continue
                        
                    # 현재 상품의 재고만 추출
                    current_item_stock = df_stock[df_stock['상품'] == mecode]
                    
                    # [핵심] LOT별로 그룹화하여 '해당 LOT의 총 재고' 계산 (단일 할당 판단 기준)
                    lot_summary = current_item_stock.groupby(['화주LOT', '유효일자'], sort=False)['환산'].sum().reset_index()
                    
                    assigned_lot = None
                    assigned_date = None
                    
                    # 합산된 재고가 주문 수량보다 큰 첫 번째 LOT 찾기
                    for l_idx, l_row in lot_summary.iterrows():
                        if l_row['환산'] >= order_qty:
                            assigned_lot = l_row['화주LOT']
                            assigned_date = l_row['유효일자']
                            break 
                            
                    if assigned_lot:
                        # 서식 파일에 기입
                        df_upload.at[index, 'LOT'] = assigned_lot
                        df_upload.at[index, '유효일자'] = assigned_date.strftime('%Y-%m-%d')
                        
                        # [실시간 재고 차감] 동일 LOT가 여러 줄에 나뉘어 있을 수 있으므로 순차 차감
                        remain_to_deduct = order_qty
                        stock_indices = df_stock[(df_stock['상품'] == mecode) & (df_stock['화주LOT'] == assigned_lot)].index
                        
                        for s_idx in stock_indices:
                            if remain_to_deduct <= 0: break
                            line_stock = df_stock.at[s_idx, '환산']
                            if line_stock > 0:
                                take_qty = min(remain_to_deduct, line_stock)
                                df_stock.at[s_idx, '환산'] -= take_qty
                                remain_to_deduct -= take_qty

                st.success("✅ 정답 로직 반영 완료! (LOT 합산 및 단일 할당)")

                # 3. 엑셀 파일 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_upload.to_excel(writer, index=False, sheet_name='서식(수주업로드)')
                    df_stock.to_excel(writer, index=False, sheet_name='Sheet1(차감후)')
                
                processed_data = output.getvalue()
                st.download_button(
                    label="📥 결과 엑셀 다운로드",
                    data=processed_data,
                    file_name=f"완료_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("시트명을 확인해주세요: '서식(수주업로드)', 'Sheet1'")
            
    except Exception as e:
        st.error(f"오류 발생: {e}")
