#1번 스케줄러 - greedy (병렬 스케줄링 + 시간 제약)
from datetime import datetime, timedelta
from app.models import ScheduleBatch, ScheduleJob
from app.services.objective import calculate_severity_score
from app.utils.skill_matcher import get_available_welders
from app.extensions import db


class GreedyScheduler:
    
    def __init__(self):
        self.session_times = {
            'morning': (9, 12),
            'afternoon': (13, 18),
            'night': (19, 22)
        }
    
    def schedule(self, defects, welders, target_date, target_session):
        batch = ScheduleBatch(
            target_date=datetime.strptime(target_date, '%Y-%m-%d').date(),
            target_session=target_session,
            status='confirmed'
        )
        db.session.add(batch)
        db.session.flush()
        
        start_hour, end_hour = self.session_times[target_session]
        session_start = datetime.strptime(f"{target_date} {start_hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
        session_end = datetime.strptime(f"{target_date} {end_hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
        
        sorted_defects = sorted(
            defects,
            key=lambda d: calculate_severity_score(d),
            reverse=True
        )
        welder_available_time = {w.welder_id: session_start for w in welders}
        
        #병렬 스케쥴링
        jobs = []
        job_order = 1
        
        for defect in sorted_defects:
            available = get_available_welders(defect, welders)
            
            if not available:
                continue
            
            best_welder = None
            earliest_start = None
            
            for welder in available:
                possible_start = welder_available_time[welder.welder_id]
                possible_end = possible_start + timedelta(minutes=defect.rework_time)
                
                if possible_end <= session_end:
                    if earliest_start is None or possible_start < earliest_start:
                        earliest_start = possible_start
                        best_welder = welder
            
            if best_welder is None:
                continue
            
            job_start = welder_available_time[best_welder.welder_id]
            job_end = job_start + timedelta(minutes=defect.rework_time)
            
            job = ScheduleJob(
                batch_id=batch.batch_id,
                welder_id=best_welder.welder_id,
                defect_id=defect.defect_id,
                job_order=job_order,
                estimated_start_time=job_start,
                estimated_end_time=job_end,
                status='pending'
            )
            jobs.append(job)
            
            welder_available_time[best_welder.welder_id] = job_end
            job_order += 1
        
        # 6. DB 저장
        db.session.bulk_save_objects(jobs)
        db.session.commit()
        
        return batch

