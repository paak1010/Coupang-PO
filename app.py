import pandas as pd

# 1. 데이터 로드
# 파일명은 업로드하신 파일명에 맞춰져 있습니다.
df_upload = pd.read_csv('(발주서) 쿠팡 서식파일_260323납품.xlsx - 서식(수주업로드).csv')
df_stock = pd.read_csv('(발주서) 쿠팡 서식파일_260323납품.xlsx - Sheet1.csv')

# 2. 데이터 전처리
# 유효일자 정렬 (선입선출 준비)
df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
df_stock = df_stock.sort_values(by=['상품', '유효일자']).reset_index(drop=True)

# 할당할 열 초기화
df_upload['LOT'] = ""
df_upload['유효일자'] = ""

# 3. 단일 LOT 할당 로직 (수량 충족 시 차감)
for index, row in df_upload.iterrows():
    mecode = row['MECODE']
    order_qty = row['수량']
    
    # MECODE가 없거나 수량이 0인 경우 패스
    if pd.isna(mecode) or order_qty <= 0:
        continue
        
    # 해당 MECODE의 재고 중 수량이 남아있는 것들 필터링
    available_stock = df_stock[(df_stock['상품'] == mecode) & (df_stock['합계수량'] > 0)]
    
    assigned = False
    for s_idx, s_row in available_stock.iterrows():
        # 현재 LOT의 재고가 주문 수량보다 같거나 많은지 확인 (단일 LOT 할당 조건)
        if s_row['합계수량'] >= order_qty:
            # 1. 업로드 파일에 정보 기입
            df_upload.at[index, 'LOT'] = s_row['화주LOT']
            df_upload.at[index, '유효일자'] = s_row['유효일자'].strftime('%Y-%m-%d')
            
            # 2. Sheet1 재고에서 수량 차감 (다음 행의 중복 할당 방지)
            df_stock.at[s_idx, '합계수량'] -= order_qty
            
            assigned = True
            break # 할당 성공했으므로 다음 주문 행으로 이동
            
    # 만약 어떤 LOT도 단독으로 수량을 채울 수 없다면 공란으로 둠 (복수 안대 조건)
    if not assigned:
        df_upload.at[index, 'LOT'] = ""
        df_upload.at[index, '유효일자'] = ""

# 4. 결과 저장
output_name = '쿠팡_수주업로드_단일LOT적용.csv'
df_upload.to_csv(output_name, index=False, encoding='utf-8-sig')
print(f"작업 완료: {output_name} 파일이 생성되었습니다.")
