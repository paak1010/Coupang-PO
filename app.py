import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="쿠팡 LOT 할당 도구", layout="wide")
st.title("📦 쿠팡 발주서 LOT 자동 할당 (환산 단순 차감)")

uploaded_file = st.file_uploader("쿠팡 서식 엑셀 파일을 업로드하세요", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        # 시트 데이터 로드
        df_upload = pd.read_excel(xls, sheet_name='서식(수주업로드)')
        df_stock = pd.read_excel(xls, sheet_name='Sheet1')
        
        if st.button("LOT 할당 시작"):
            # 1. 재고 데이터 정렬 (유효일자 -> LOT 순)
            df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
            df_stock = df_stock.sort_values(by=['상품', '유효일자', '화주LOT']).reset_index(drop=True)
            
            # 결과 열 초기화
            df_upload['LOT'] = ""
            df_upload['유효일자'] = ""

            # 2. 할당 로직 (한 줄씩 검사하며 단순 차감)
            for index, row in df_upload.iterrows():
                mecode = row['MECODE']
                order_qty = row['수량']
                
                if pd.isna(mecode) or order_qty <= 0:
                    continue
                
                # Sheet1에서 조건에 맞는 '첫 번째 줄'만 찾기
                # 조건: 상품 일치 & 해당 줄의 '환산' 재고가 주문량 이상
                found = False
                for s_idx, s_row in df_stock.iterrows():
                    if s_row['상품'] == mecode and s_row['환산'] >= order_qty:
                        # 정보 기입
                        df_upload.at[index, 'LOT'] = s_row['화주LOT']
                        df_upload.at[index, '유효일자'] = s_row['유효일자'].strftime('%Y-%m-%d')
                        
                        # [핵심] 해당 줄의 재고 즉시 차감
                        df_stock.at[s_idx, '환산'] -= order_qty
                        found = True
                        break # 단일 할당이므로 찾으면 바로 다음 주문으로
                
            st.success("✅ 할당이 완료되었습니다.")

            # 3. 엑셀 파일 생성
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_upload.to_excel(writer, index=False, sheet_name='서식(수주업로드)')
                df_stock.to_excel(writer, index=False, sheet_name='Sheet1_차감결과')
            
            st.download_button(
                label="📥 결과 엑셀 다운로드",
                data=output.getvalue(),
                file_name=f"완료_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"오류 발생: {e}")
