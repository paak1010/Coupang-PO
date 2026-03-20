import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="쿠팡 발주서 LOT 할당 (환산 기준)", layout="wide")
st.title("📦 쿠팡 발주서 LOT 자동 할당 (환산 재고 차감 방식)")

uploaded_file = st.file_uploader("쿠팡 서식 엑셀 파일(단일 파일)을 업로드하세요", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        if '서식(수주업로드)' in sheet_names and 'Sheet1' in sheet_names:
            df_upload = pd.read_excel(xls, sheet_name='서식(수주업로드)')
            df_stock = pd.read_excel(xls, sheet_name='Sheet1')
            
            if st.button("LOT 할당 시작"):
                # 1. 재고 데이터 정렬 (유효일자 빠른 순 - FEFO)
                df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
                df_stock = df_stock.sort_values(by=['상품', '유효일자']).reset_index(drop=True)
                
                # 결과 기입 열 초기화 (기존 데이터가 있다면 덮어쓰기 위해)
                df_upload['LOT'] = ""
                df_upload['유효일자'] = ""

                # 2. 할당 로직 (환산 열 기준 차감)
                for index, row in df_upload.iterrows():
                    mecode = row['MECODE']
                    order_qty = row['수량']
                    
                    if pd.isna(mecode) or order_qty <= 0:
                        continue
                        
                    # 해당 MECODE의 재고 중 [환산] 수량이 주문수량 이상인 LOT 필터링
                    # '환산' 열을 가용 재고의 총합으로 간주함
                    mask = (df_stock['상품'] == mecode) & (df_stock['환산'] >= order_qty)
                    available_lots = df_stock[mask]
                    
                    if not available_lots.empty:
                        target_idx = available_lots.index[0]
                        s_row = available_lots.loc[target_idx]
                        
                        # 업로드 시트에 할당 정보 기입
                        df_upload.at[index, 'LOT'] = s_row['화주LOT']
                        df_upload.at[index, '유효일자'] = s_row['유효일자'].strftime('%Y-%m-%d')
                        
                        # [핵심] '환산' 열에서 주문 수량만큼 차감 (누적 반영)
                        df_stock.at[target_idx, '환산'] -= order_qty
                    else:
                        # 재고 부족 시 빈칸 유지 (혹은 필요시 '재고부족' 등 텍스트 기입 가능)
                        pass

                st.success("✅ 할당 및 환산 재고 차감이 완료되었습니다!")

                # 3. 엑셀 파일 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_upload.to_excel(writer, index=False, sheet_name='서식(수주업로드)')
                    df_stock.to_excel(writer, index=False, sheet_name='Sheet1')
                
                processed_data = output.getvalue()
                st.download_button(
                    label="📥 결과 엑셀 다운로드",
                    data=processed_data,
                    file_name=f"결과_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("파일 내에 '서식(수주업로드)'와 'Sheet1' 시트가 필요합니다.")
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
