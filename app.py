import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="쿠팡 발주서 자동 할당", layout="wide")
st.title("📦 쿠팡 발주서 LOT 자동 할당 (단일 파일용)")

# 파일 업로드 (xlsx만 허용)
uploaded_file = st.file_uploader("쿠팡 서식 엑셀 파일을 업로드하세요", type=['xlsx'])

if uploaded_file:
    # 1. 엑셀 파일 내의 모든 시트 읽기
    try:
        # 시트명 확인을 위해 전체 로드
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        if '서식(수주업로드)' in sheet_names and 'Sheet1' in sheet_names:
            df_upload = pd.read_excel(xls, sheet_name='서식(수주업로드)')
            df_stock = pd.read_excel(xls, sheet_name='Sheet1')
            
            if st.button("LOT 할당 및 재고 차감 시작"):
                # 전처리: 유효일자 기준 정렬 (FEFO - 선입선출)
                # Sheet1의 유효일자 컬럼명 확인 필수
                df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
                df_stock = df_stock.sort_values(by=['상품', '유효일자']).reset_index(drop=True)
                
                # 결과 기입용 열 초기화 (O, P열 위치)
                df_upload['LOT'] = ""
                df_upload['유효일자'] = ""

                # 2. 로직 실행 (앞에서부터 수량 차감하며 할당)
                for index, row in df_upload.iterrows():
                    mecode = row['MECODE']
                    order_qty = row['수량']
                    
                    if pd.isna(mecode) or order_qty <= 0:
                        continue
                        
                    # 해당 MECODE의 재고 중 주문수량 이상 남아있는 첫 번째 LOT 찾기
                    mask = (df_stock['상품'] == mecode) & (df_stock['합계수량'] >= order_qty)
                    available_lots = df_stock[mask]
                    
                    if not available_lots.empty:
                        # 가장 빠른 유효기간의 LOT 인덱스 가져오기
                        target_idx = available_lots.index[0]
                        s_row = available_lots.loc[target_idx]
                        
                        # 할당 (단일 LOT 조건)
                        df_upload.at[index, 'LOT'] = s_row['화주LOT']
                        df_upload.at[index, '유효일자'] = s_row['유효일자'].strftime('%Y-%m-%d')
                        
                        # 재고 차감 (동일 MECODE 다음 행 계산에 반영됨)
                        df_stock.at[target_idx, '합계수량'] -= order_qty
                    else:
                        # 수량이 모자라거나 LOT가 없으면 빈칸 유지
                        pass

                st.success("✅ 할당 작업 완료!")

                # 3. 결과 파일 생성 (다운로드용)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_upload.to_excel(writer, index=False, sheet_name='결과_수주업로드')
                    df_stock.to_excel(writer, index=False, sheet_name='남은재고_확인용')
                
                processed_data = output.getvalue()
                
                st.download_button(
                    label="📥 결과 엑셀 다운로드",
                    data=processed_data,
                    file_name=f"쿠팡_할당완료_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("파일 내에 '서식(수주업로드)' 시트와 'Sheet1' 시트가 모두 있어야 합니다.")
            st.info(f"현재 확인된 시트명: {', '.join(sheet_names)}")

    except Exception as e:
        st.error(f"에러 발생: {e}")
