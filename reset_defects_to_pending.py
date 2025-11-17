#python reset_defects_to_pending.py
import requests

BASE_URL = "http://localhost:5000"

def reset_all_defects_to_pending():
    print("=" * 60)
    print("모든 결함 상태를 pending으로 변경합니다...")
    print("=" * 60)
    
    all_defects = []
    
    for status in ['pending', 'in_progress', 'completed']:
        print(f"\n'{status}' 상태의 결함 조회 중...")
        try:
            response = requests.get(f"{BASE_URL}/api/defects?status={status}")
            if response.status_code == 200:
                defects_data = response.json()
                defects = defects_data.get('defects', [])
                all_defects.extend(defects)
                print(f"  → {len(defects)}개 발견")
            else:
                print(f"  → 오류: {response.status_code}")
        except Exception as e:
            print(f"  → 오류 발생: {e}")
    
    print(f"\n총 {len(all_defects)}개의 결함을 찾았습니다.")
    
    if not all_defects:
        print("변경할 결함이 없습니다.")
        return
    
    print("\n" + "=" * 60)
    print("상태 변경 시작...")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for defect in all_defects:
        defect_id = defect['defect_id']
        current_status = defect['status']
        
        if current_status == 'pending':
            print(f"Defect ID {defect_id}: 이미 pending 상태 (스킵)")
            success_count += 1
            continue
        
        try:
            response = requests.patch(
                f"{BASE_URL}/api/defects/{defect_id}",
                json={'status': 'pending'}
            )
            
            if response.status_code == 200:
                print(f"Defect ID {defect_id}: {current_status} → pending ✓")
                success_count += 1
            else:
                print(f"Defect ID {defect_id}: 실패 ({response.status_code})")
                fail_count += 1
        except Exception as e:
            print(f"Defect ID {defect_id}: 오류 발생 - {e}")
            fail_count += 1
    
    # 3. 결과 요약
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    print(f"총 결함 수: {len(all_defects)}")
    print(f"성공: {success_count}")
    print(f"실패: {fail_count}")
    print("=" * 60)

if __name__ == '__main__':
    reset_all_defects_to_pending()

