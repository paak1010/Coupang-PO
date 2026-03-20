import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="쿠팡 발주서 LOT 할당 (정렬 강화)", layout="wide")
st.title("📦 쿠팡 발주서 LOT 자동 할당")
st.info("로직: 유효일자 빠른 순 ➔ 로트 번호 작은 순 ➔ 단일 LOT 할당 ➔ 환산 재고 차감")

uploaded_file = st.file_uploader("쿠팡 서식 엑셀 파일(단일 파일)을 업로드하세요", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        if '서식(수주업로드)' in sheet_names and 'Sheet1' in sheet_names:
            df_upload = pd.read_excel(xls, sheet_name='서식(수주업로드)')
            df_stock = pd.read_excel(xls, sheet_name='Sheet1')
            
            if st.button("LOT 할당 시작"):
                # 1. 재고 데이터 정렬 강화
                # [상품]별로 [유효일자]가 빠른 순, 유효일자가 같다면 [화주LOT]가 작은 순으로 정렬
                df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
                df_stock = df_stock.sort_values(by=['상품', '유효일자', '화주LOT']).reset_index(drop=True)
                
                # 결과 기입 열 초기화
                df_upload['LOT'] = ""
                df_upload['유효일자'] = ""

                # 2. 할당 로직
                for index, row in df_upload.iterrows():
                    mecode = row['MECODE']
                    order_qty = row['수량']
                    
                    # 수량이 0이거나 MECODE가 없는 경우 스킵
                    if pd.isna(mecode) or order_qty <= 0:
                        continue
                        
                    # 필터링: 상품 일치 & 재고 있음 & 단일 LOT로 수량 충족 가능
                    mask = (
                        (df_stock['상품'] == mecode) & 
                        (df_stock['환산'] > 0) & 
                        (df_stock['환산'] >= order_qty)
                    )
                    available_lots = df_stock[mask]
                    
                    if not available_lots.empty:
                        # 정렬된 상태이므로 첫 번째 행(가장 빠른 날짜 & 가장 작은 LOT 번호) 선택
                        target_idx = available_lots.index[0]
                        s_row = available_lots.loc[target_idx]
                        
                        # 업로드 시트에 기입
                        df_upload.at[index, 'LOT'] = s_row['화주LOT']
                        df_upload.at[index, '유효일자'] = s_row['유효일자'].strftime('%Y-%m-%d')
                        
                        # [핵심] '환산' 재고 실시간 차감 (박스 단위 상관없이 자유롭게 조절)
                        df_stock.at[target_idx, '환산'] -= order_qty
                    else:
                        # 재고가 부족한 경우 빈칸 유지 (복수 LOT 할당 안 함)
                        pass

                st.success("✅ 할당 완료! 유효일자와 로트 순서가 모두 반영되었습니다.")

                # 3. 엑셀 파일 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_upload.to_excel(writer, index=False, sheet_name='서식(수주업로드)')
                    df_stock.to_excel(writer, index=False, sheet_name='Sheet1(차감후재고)')
                
                processed_data = output.getvalue()
                st.download_button(
                    label="📥 결과 엑셀 다운로드",
                    data=processed_data,
                    file_name=f"완료_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("파일 내에 '서식(수주업로드)'와 'Sheet1' 시트가 필요합니다.")
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
