#python update_welder_shift_times.py
#용접공들의 날짜를 오늘 날짜로
from app import create_app
from app.extensions import db
from app.models import Welder
from datetime import datetime

def update_welder_shift_times():
    print("=" * 60)
    print("용접공들의 근무 종료 시간을 오늘 날짜로 업데이트합니다...")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        welders = Welder.query.all()
        
        if not welders:
            print("용접공이 없습니다.")
            return
        
        print(f"\n총 {len(welders)}명의 용접공을 찾았습니다.")
        print(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}\n")
        
        success_count = 0
        
        for welder in welders:
            old_shift_end = welder.shift_end_time
            old_time_str = old_shift_end.strftime('%H:%M:%S')
            
            today = datetime.now().date()
            new_shift_end = datetime.combine(today, old_shift_end.time())
            
            welder.shift_end_time = new_shift_end
            
            print(f"용접공 ID {welder.welder_id} ({welder.welder_name:6s}): "
                  f"{old_shift_end.strftime('%Y-%m-%d %H:%M')} → "
                  f"{new_shift_end.strftime('%Y-%m-%d %H:%M')} ✓")
            
            success_count += 1
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("결과 요약")
        print("=" * 60)
        print(f"총 용접공 수: {len(welders)}")
        print(f"성공: {success_count}")
        print("=" * 60)
        print("\n✅ 모든 용접공의 근무 종료 시간이 오늘 날짜로 업데이트되었습니다!")

if __name__ == '__main__':
    update_welder_shift_times()

