import pandas as pd

# 1. 데이터 로드
df_upload = pd.read_excel('파일명.xlsx', sheet_name='서식(수주업로드)')
df_stock = pd.read_excel('파일명.xlsx', sheet_name='Sheet1')

# 2. 재고 전처리: 유효일자 순 -> LOT 순으로 정렬
df_stock['유효일자'] = pd.to_datetime(df_stock['유효일자'])
df_stock = df_stock.sort_values(by=['상품', '유효일자', '화주LOT']).reset_index(drop=True)

# 결과 열 초기화
df_upload['LOT'] = ""
df_upload['유효일자'] = ""

# 3. 할당 시작
for index, row in df_upload.iterrows():
    mecode = row['MECODE']
    order_qty = row['수량']
    
    if pd.isna(mecode) or order_qty <= 0:
        continue
        
    # 현재 시점의 재고에서 해당 상품만 추출
    current_item_stock = df_stock[df_stock['상품'] == mecode]
    
    # [핵심 수정] LOT별로 그룹화하여 해당 LOT의 '전체 환산 재고' 계산
    # 재고 파일에 같은 LOT가 여러 줄이어도 하나로 합쳐서 판단함
    lot_summary = current_item_stock.groupby(['화주LOT', '유효일자'], sort=False)['환산'].sum().reset_index()
    
    assigned_lot = None
    assigned_date = None
    
    for l_idx, l_row in lot_summary.iterrows():
        # 단일 LOT의 총 합계가 주문 수량보다 큰지 확인
        if l_row['환산'] >= order_qty:
            assigned_lot = l_row['화주LOT']
            assigned_date = l_row['유효일자']
            break # 조건 충족하는 가장 빠른 LOT 찾으면 종료
            
    if assigned_lot:
        # 업로드 시트에 기입
        df_upload.at[index, 'LOT'] = assigned_lot
        df_upload.at[index, '유효일자'] = assigned_date.strftime('%Y-%m-%d')
        
        # [중요] 실제 재고(df_stock)에서 수량 차감 (여러 줄에 나눠져 있을 수 있으므로 순차 차감)
        remain_to_deduct = order_qty
        stock_indices = df_stock[(df_stock['상품'] == mecode) & (df_stock['화주LOT'] == assigned_lot)].index
        
        for s_idx in stock_indices:
            if remain_to_deduct <= 0: break
            current_line_stock = df_stock.at[s_idx, '환산']
            take_qty = min(remain_to_deduct, current_line_stock)
            df_stock.at[s_idx, '환산'] -= take_qty
            remain_to_deduct -= take_qty

# 결과 저장...
