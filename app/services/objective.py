# 결함 타입! 7개만
DEFECT_TYPES = {
    0: '균열',
    1: '용합 불량',
    2: '용입 부족',
    3: '기공',
    4: '슬래그 섞임',
    5: '언더컷',
    6: '왜곡'
}

#무관용 결함! -> 모델의 심각도 => 1로
CRITICAL_DEFECT_TYPES = [0, 1, 2]


#심각도 점수 계산 공식
## 무관용 결함이면 무조건 심각도 -> 1.0
## MVP에서는 p_in과 p_out중 큰 값
## priority_factor는 기본 1, 심각도가 0-1이므로 음수로 적용!
def calculate_severity_score(defect):
    if defect.defect_type in CRITICAL_DEFECT_TYPES:
        severity = 1.0
    else:
        severity = max(defect.p_in, defect.p_out)
    
    severity_score = severity ** (-defect.priority_factor)
    
    return severity_score

