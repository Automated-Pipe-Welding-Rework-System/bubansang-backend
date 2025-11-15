"""
기존 데이터 삭제 후 대량 샘플 데이터 생성 스크립트

- 용접공 10명 (다양한 스킬, 근무 시간)
- 결함 50개 (다양한 타입, 심각도, 위치)

실행 방법:
    python init_large_sample_data.py
"""

from app import create_app
from app.extensions import db
from app.models import Pipe, Welder, WelderSkill, Defect, Skill
from datetime import datetime, timedelta
import random

def clear_existing_data():
    """기존 샘플 데이터 삭제 (TRUNCATE CASCADE 사용)"""
    print("🗑️  Clearing existing sample data...")
    
    db.session.execute(db.text('TRUNCATE TABLE schedule_jobs, schedule_batches, welder_skills, welders, defects, pipes RESTART IDENTITY CASCADE'))
    
    db.session.commit()
    print("✅ Existing data cleared")


def init_pipes():
    """파이프 60개 생성 (결함 50개 + 여유)"""
    print("🔩 Creating 60 pipes...")
    
    materials = ['탄소강', '스테인리스강', '합강']
    work_locations = [2, 5, 6, 7]  # B, E, F, G (작업 가능 구역)
    
    pipes = []
    for i in range(1, 61):
        pipe = Pipe(
            pipe_id=i,
            material=random.choice(materials),
            current_location_id=random.choice(work_locations)
        )
        pipes.append(pipe)
    
    for pipe in pipes:
        db.session.add(pipe)
    
    db.session.commit()
    print(f"✅ {len(pipes)} pipes created")


def init_welders():
    """용접공 10명 생성 (다양한 근무 시간)"""
    print("👷 Creating 10 welders...")
    
    welder_data = [
        # (이름, 근무종료시간, 상태)
        ('김철수', '18:00:00', 'available'),   # 정시 퇴근
        ('이영희', '18:00:00', 'available'),   # 정시 퇴근
        ('박민수', '20:00:00', 'available'),   # 야근 (2시간)
        ('정수진', '18:00:00', 'available'),   # 정시 퇴근
        ('최동욱', '22:00:00', 'available'),   # 야근 (4시간)
        ('강서연', '18:00:00', 'available'),   # 정시 퇴근
        ('윤재호', '20:00:00', 'available'),   # 야근 (2시간)
        ('임하늘', '18:00:00', 'working'),     # 작업 중
        ('송민지', '22:00:00', 'available'),   # 야근 (4시간)
        ('한지우', '18:00:00', 'available'),   # 정시 퇴근
    ]
    
    welders = []
    for i, (name, shift_end, status) in enumerate(welder_data, start=1):
        welder = Welder(
            welder_id=i,
            welder_name=name,
            current_location_id=1,  # 구역 A (시작)
            current_setup_id=4,     # Base Setup
            current_defect_id=None,
            status=status,
            shift_end_time=datetime.strptime(f'2025-11-15 {shift_end}', '%Y-%m-%d %H:%M:%S')
        )
        welders.append(welder)
    
    for welder in welders:
        db.session.add(welder)
    
    db.session.commit()
    print(f"✅ {len(welders)} welders created")
    
    return welders


def init_welder_skills():
    """용접공별 스킬 할당 (1-3개)"""
    print("🎯 Assigning skills to welders...")
    
    # 모든 스킬 조회
    all_skills = Skill.query.all()
    
    # 용접공별 스킬 할당 (랜덤하게 1-3개)
    welder_skill_assignments = []
    
    for welder_id in range(1, 11):
        # 1-3개 랜덤 선택
        num_skills = random.randint(1, 3)
        selected_skills = random.sample(all_skills, num_skills)
        
        for skill in selected_skills:
            ws = WelderSkill(
                welder_id=welder_id,
                skill_id=skill.skill_id
            )
            welder_skill_assignments.append(ws)
    
    for ws in welder_skill_assignments:
        db.session.add(ws)
    
    db.session.commit()
    print(f"✅ {len(welder_skill_assignments)} welder-skill mappings created")


def init_defects():
    """결함 50개 생성 (다양한 타입, 심각도)"""
    print("💥 Creating 50 defects...")
    
    # 결함 타입 (0-6)
    defect_types = [0, 1, 2, 3, 4, 5, 6]
    
    # 작업 가능 구역
    work_locations = [2, 5, 6, 7]  # B, E, F, G
    
    # 모든 스킬 조회
    all_skills = Skill.query.all()
    
    defects = []
    
    for i in range(1, 51):
        # 결함 타입 선택
        defect_type = random.choice(defect_types)
        
        # 무관용 결함(0,1,2)은 더 자주 나오도록
        if random.random() < 0.3:  # 30% 확률
            defect_type = random.choice([0, 1, 2])
        
        # p_in, p_out (0.1 ~ 1.0)
        p_in = round(random.uniform(0.1, 1.0), 2)
        p_out = round(random.uniform(0.1, 1.0), 2)
        
        # priority_factor (1-10, 대부분 1-3)
        if random.random() < 0.7:  # 70%는 낮은 우선순위
            priority_factor = random.randint(1, 3)
        else:  # 30%는 높은 우선순위
            priority_factor = random.randint(4, 10)
        
        # rework_time (30-120분)
        rework_time = random.randint(30, 120)
        
        # 랜덤 스킬 선택
        required_skill = random.choice(all_skills)
        
        # 셋업 타입 (스킬의 process에 따라)
        setup_type_map = {
            'SMAW': 1,
            'GTAW': 2,
            'GMAW': 3,
            'FCAW': 3
        }
        setup_type_id = setup_type_map.get(required_skill.process, 1)
        
        defect = Defect(
            defect_id=i,
            pipe_id=i,  # 파이프 1:1 매핑
            location_id=random.choice(work_locations),
            defect_type=defect_type,
            p_in=p_in,
            p_out=p_out,
            required_skill_id=required_skill.skill_id,
            setup_type_id=setup_type_id,
            priority_factor=priority_factor,
            rework_time=rework_time,
            status='pending',
            created_at=datetime.now() - timedelta(hours=random.randint(1, 48))
        )
        defects.append(defect)
    
    for defect in defects:
        db.session.add(defect)
    
    db.session.commit()
    print(f"✅ {len(defects)} defects created")


def print_summary():
    """데이터 요약 출력"""
    print("\n" + "="*80)
    print("📊 Large Sample Data Summary")
    print("="*80)
    
    # 용접공 요약
    print("\n👷 Welders (10명):")
    welders = Welder.query.all()
    for welder in welders:
        skills = WelderSkill.query.filter_by(welder_id=welder.welder_id).all()
        skill_names = []
        for ws in skills:
            skill = Skill.query.get(ws.skill_id)
            skill_names.append(f"{skill.process}-{skill.position}-{skill.material}")
        
        shift_end = welder.shift_end_time.strftime('%H:%M')
        overtime = "야근" if shift_end > "18:00" else "정시"
        
        print(f"   {welder.welder_id:2d}. {welder.welder_name:6s} | "
              f"퇴근: {shift_end} ({overtime}) | "
              f"스킬: {len(skills)}개 | "
              f"상태: {welder.status}")
    
    # 결함 요약
    print(f"\n💥 Defects (50개):")
    defects = Defect.query.all()
    
    # 타입별 집계
    type_counts = {}
    for defect in defects:
        type_counts[defect.defect_type] = type_counts.get(defect.defect_type, 0) + 1
    
    defect_type_names = {
        0: '균열', 1: '용합불량', 2: '용입부족',
        3: '기공', 4: '슬래그섞임', 5: '언더컷', 6: '왜곡'
    }
    
    for dtype, count in sorted(type_counts.items()):
        is_critical = "⚠️ 무관용" if dtype in [0, 1, 2] else ""
        print(f"   - {defect_type_names[dtype]:8s}: {count:2d}개 {is_critical}")
    
    # 우선순위별 집계
    print(f"\n📈 Priority Distribution:")
    priority_counts = {}
    for defect in defects:
        priority_counts[defect.priority_factor] = priority_counts.get(defect.priority_factor, 0) + 1
    
    for priority, count in sorted(priority_counts.items()):
        bar = "█" * count
        print(f"   Priority {priority:2d}: {bar} ({count}개)")
    
    # 구역별 집계
    print(f"\n📍 Location Distribution:")
    location_counts = {}
    for defect in defects:
        location_counts[defect.location_id] = location_counts.get(defect.location_id, 0) + 1
    
    location_names = {2: '구역 B', 5: '구역 E', 6: '구역 F', 7: '구역 G'}
    for loc_id, count in sorted(location_counts.items()):
        print(f"   - {location_names[loc_id]}: {count}개")
    
    print("\n" + "="*80)
    print(f"Total: {len(welders)} welders, {len(defects)} defects, {Pipe.query.count()} pipes")
    print("="*80 + "\n")


def main():
    """메인 실행 함수"""
    print("\n" + "="*80)
    print("🚀 Starting Large Sample Data Generation")
    print("="*80 + "\n")
    
    app = create_app()
    
    with app.app_context():
        # 기존 데이터 삭제
        clear_existing_data()
        
        # 새 데이터 생성
        init_pipes()
        init_welders()
        init_welder_skills()
        init_defects()
        
        print("\n" + "="*80)
        print("✨ Large Sample Data Generation Complete!")
        print("="*80)
        
        # 요약 출력
        print_summary()
        
        print("💡 Tip: 이제 스케줄 최적화를 테스트해보세요!")
        print("   POST /api/schedules/optimize")
        print("   {")
        print('     "target_date": "2025-11-15",')
        print('     "target_session": "morning"')
        print("   }\n")


if __name__ == '__main__':
    main()

