#OR-Tools CP-SAT 기반 스케쥴러
## 제약1 : 병렬
## 제약2 : 이동시간 travelMatrix로 최소화 (=> 같은 구역 최대한 같이 처리)
## 제약3 : 셋업 시간 setupType으로 최소화 (=> 같은 구역 최대한 같이 처리), 셋업은 D구역에서!
## 제약4 : 동시작업 금지 (F, G구역)
## 제약5 : 용접공별 근무시간 (shift_end_time 지키기. 퇴근 시간 지켜!)
## 제약6 : 목적함수 완성 (심각도 - 이동비용 - 셋업비용 를 최대화)

"""
TODO : 필요시 가중치 변경!
목적함수:
  Maximize: Σ severity_score - λ * Σ travel_time - μ * Σ setup_time
  - λ = 0.1 (이동 1분 = 심각도 0.1)
  - μ = 0.2 (셋업 1분 = 심각도 0.2)
"""

from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from app.models import ScheduleBatch, ScheduleJob, TravelMatrix, SetupType, Defect, Location
from app.services.objective import calculate_severity_score
from app.utils.skill_matcher import check_skill_match
from app.extensions import db


class ORToolsScheduler:
    
    def __init__(self):
        self.session_times = {
            'morning': (9, 12),
            'afternoon': (13, 18),
            'night': (19, 22)
        }
        
        self.setup_location_id = 4  # 구역 D에서 셋업
        self.concurrent_restricted_locations = [(6, 7), (7, 6)]  # 구역 F,G는 동시 작업 불가능!
    
    def get_travel_time(self, from_location_id, to_location_id):
        if from_location_id == to_location_id:
            return 0
        
        travel = TravelMatrix.query.filter_by(
            from_location_id=from_location_id,
            to_location_id=to_location_id
        ).first()
        
        return travel.travel_time_minutes if travel else 0
    
    def get_setup_time(self, setup_type_id):
        setup = SetupType.query.get(setup_type_id)
        return setup.setup_cost_minutes if setup else 0
    
    
    ###########스케쥴링!!!!!!!!!##############
    
    def schedule(self, defects, welders, target_date, target_session):
        start_hour, end_hour = self.session_times[target_session]
        session_start = datetime.strptime(f"{target_date} {start_hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
        session_end = datetime.strptime(f"{target_date} {end_hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
        
        horizon = int((session_end - session_start).total_seconds() / 60)
        
        model = cp_model.CpModel()
        
        task_vars = {}  # [welder_id][defect_id] = (start_var, end_var, interval_var, is_assigned_var)
        is_assigned = {}  # (welder_id, defect_id) -> BoolVar
        
        defect_locations = {d.defect_id: d.location_id for d in defects}
        defect_setups = {d.defect_id: d.setup_type_id for d in defects}
        
        #용접공 시작 정보!
        welder_start_location = {} # A구역에서 시작
        welder_start_time = {}
        welder_start_setup = {}
        
        for welder in welders:
            if welder.status == 'working' and welder.current_defect_id:
                # wroking일 때 현재 진행중인 재작업이 언제 끝날지 -> 그 이후부터 스케쥴링
                current_defect = Defect.query.get(welder.current_defect_id)
                if current_defect:
                    estimated_end = session_start + timedelta(minutes=current_defect.rework_time)
                    
                    if estimated_end > session_start:
                        welder_start_time[welder.welder_id] = int((estimated_end - session_start).total_seconds() / 60)
                    else:
                        welder_start_time[welder.welder_id] = 0
                    
                    welder_start_location[welder.welder_id] = current_defect.location_id
                    welder_start_setup[welder.welder_id] = current_defect.setup_type_id
                else:
                    welder_start_time[welder.welder_id] = 0
                    welder_start_location[welder.welder_id] = 1 # 구역 A
                    welder_start_setup[welder.welder_id] = welder.current_setup_id or 4
            else:
                # available -> 무조건 구역 A에서 
                welder_start_time[welder.welder_id] = 0
                welder_start_location[welder.welder_id] = 1
                welder_start_setup[welder.welder_id] = welder.current_setup_id or 4
        
        for welder in welders:
            task_vars[welder.welder_id] = {}
            
            for defect in defects:
                if not check_skill_match(welder, defect):
                    continue
                
                duration = defect.rework_time
                suffix = f'_w{welder.welder_id}_d{defect.defect_id}'
                
                start_var = model.NewIntVar(0, horizon, f'start{suffix}')
                end_var = model.NewIntVar(0, horizon, f'end{suffix}')
                is_assigned_var = model.NewBoolVar(f'assigned{suffix}')
                
                interval_var = model.NewOptionalIntervalVar(
                    start_var, duration, end_var, is_assigned_var, f'interval{suffix}'
                )
                
                task_vars[welder.welder_id][defect.defect_id] = (
                    start_var, end_var, interval_var, is_assigned_var
                )
                is_assigned[(welder.welder_id, defect.defect_id)] = is_assigned_var
        
        #1. 결함은 1명에게만 할당
        for defect in defects:
            assigned_to_defect = []
            for welder in welders:
                if defect.defect_id in task_vars.get(welder.welder_id, {}):
                    assigned_to_defect.append(
                        is_assigned[(welder.welder_id, defect.defect_id)]
                    )
            if assigned_to_defect:
                model.Add(sum(assigned_to_defect) <= 1)
        
        #2. 각 용접공은 하나의 작업만
            if welder.welder_id in task_vars:
                intervals = [
                    task_vars[welder.welder_id][defect_id][2]
                    for defect_id in task_vars[welder.welder_id]
                ]
                if intervals:
                    model.AddNoOverlap(intervals)
        
        #3. 시간제약 : session + 용접공 퇴근 전
        for welder in welders:
            if welder.welder_id not in task_vars:
                continue
            welder_end_time = welder.shift_end_time
            
            if welder_end_time <= session_start:
                welder_horizon = 0
            elif welder_end_time >= session_end:
                welder_horizon = horizon
            else:
                welder_horizon = int((welder_end_time - session_start).total_seconds() / 60)
            
            for defect_id in task_vars[welder.welder_id]:
                start_var, end_var, _, is_assigned_var = task_vars[welder.welder_id][defect_id]
                model.Add(end_var <= welder_horizon).OnlyEnforceIf(is_assigned_var)
            
            #첫 작업 A에서 이동시간 고려 or working일 경우
            start_loc = welder_start_location[welder.welder_id]
            start_setup = welder_start_setup[welder.welder_id]
            earliest_start = welder_start_time[welder.welder_id]
            
            for defect_id in task_vars[welder.welder_id]:
                start_var, _, _, is_assigned_var = task_vars[welder.welder_id][defect_id]
                
                defect_loc = defect_locations[defect_id]
                defect_setup = defect_setups[defect_id]
                
                if start_setup != defect_setup:
                    #셋업 변경이 필요한 경우 D구역에서 셋업 변경 하고 화야함.
                    travel_to_d = self.get_travel_time(start_loc, self.setup_location_id)
                    setup_time = self.get_setup_time(defect_setup)
                    travel_to_work = self.get_travel_time(self.setup_location_id, defect_loc)
                    min_start_time = earliest_start + travel_to_d + setup_time + travel_to_work
                else:
                    travel_time = self.get_travel_time(start_loc, defect_loc)
                    min_start_time = earliest_start + travel_time
                
                model.Add(start_var >= min_start_time).OnlyEnforceIf(is_assigned_var)
        
        #4. 작업 순서, 이동, 셋업 비용
        travel_cost_vars = {}  # [welder_id][(d1, d2)] -> IntVar
        setup_cost_vars = {}   # [welder_id][(d1, d2)] -> IntVar
        order_vars = {}        # [welder_id][(d1, d2)] -> BoolVar (순서 추적)
        
        for welder in welders:
            if welder.welder_id not in task_vars:
                continue
            
            travel_cost_vars[welder.welder_id] = {}
            setup_cost_vars[welder.welder_id] = {}
            order_vars[welder.welder_id] = {}
            
            defect_ids = list(task_vars[welder.welder_id].keys())
            
            # 모든 작업 쌍에 대해 순서 제약
            for i, defect_id_1 in enumerate(defect_ids):
                for defect_id_2 in defect_ids[i+1:]:
                    _, end_1, _, assigned_1 = task_vars[welder.welder_id][defect_id_1]
                    start_2, _, _, assigned_2 = task_vars[welder.welder_id][defect_id_2]
                    
                    # 두 작업이 모두 할당된 경우
                    both_assigned = model.NewBoolVar(f'both_w{welder.welder_id}_d{defect_id_1}_d{defect_id_2}')
                    model.AddMultiplicationEquality(both_assigned, [assigned_1, assigned_2])
                    
                    # 작업1 -> 작업2 순서인 경우
                    task1_before_task2 = model.NewBoolVar(f'order_w{welder.welder_id}_d{defect_id_1}_before_d{defect_id_2}')
                    order_vars[welder.welder_id][(defect_id_1, defect_id_2)] = task1_before_task2
                    
                    # 작업1이 작업2보다 먼저 끝나는 경우
                    model.Add(end_1 < start_2).OnlyEnforceIf([both_assigned, task1_before_task2])
                    
                    # 이동 시간 계산
                    loc_1 = defect_locations[defect_id_1]
                    loc_2 = defect_locations[defect_id_2]
                    setup_1 = defect_setups[defect_id_1]
                    setup_2 = defect_setups[defect_id_2]
                    
                    # Phase 6: 비용 변수 생성 (최대값으로 초기화)
                    max_travel = 30  # 최대 이동 시간 (분)
                    max_setup = 30   # 최대 셋업 시간 (분)
                    
                    travel_cost_12 = model.NewIntVar(0, max_travel, f'travel_w{welder.welder_id}_d{defect_id_1}_to_d{defect_id_2}')
                    setup_cost_12 = model.NewIntVar(0, max_setup, f'setup_w{welder.welder_id}_d{defect_id_1}_to_d{defect_id_2}')
                    
                    travel_cost_vars[welder.welder_id][(defect_id_1, defect_id_2)] = travel_cost_12
                    setup_cost_vars[welder.welder_id][(defect_id_1, defect_id_2)] = setup_cost_12
                    
                    #셋업 변경 시 구역 D 경유
                    if setup_1 != setup_2:
                        # 작업1 끝 -> 구역D 이동 -> 셋업 -> 작업2 위치 이동 -> 작업2 시작
                        travel_to_setup = self.get_travel_time(loc_1, self.setup_location_id)
                        setup_time = self.get_setup_time(setup_2)
                        travel_to_work = self.get_travel_time(self.setup_location_id, loc_2)
                        
                        total_overhead = travel_to_setup + setup_time + travel_to_work
                        travel_time_12 = travel_to_setup + travel_to_work
                        setup_time_12 = setup_time
                    else:
                        # 단순 이동
                        total_overhead = self.get_travel_time(loc_1, loc_2)
                        travel_time_12 = total_overhead
                        setup_time_12 = 0
                    
                    #시간적으로 뒤에 와야함 > 작업2 시작 >= 작업1 종료 + overhead
                    model.Add(start_2 >= end_1 + total_overhead).OnlyEnforceIf([both_assigned, task1_before_task2])
                    
                    #비용 계산 (작업1 -> 작업2 순서일 때만)
                    model.Add(travel_cost_12 == travel_time_12).OnlyEnforceIf([both_assigned, task1_before_task2])
                    model.Add(travel_cost_12 == 0).OnlyEnforceIf([both_assigned, task1_before_task2.Not()])
                    model.Add(travel_cost_12 == 0).OnlyEnforceIf(both_assigned.Not())
                    
                    model.Add(setup_cost_12 == setup_time_12).OnlyEnforceIf([both_assigned, task1_before_task2])
                    model.Add(setup_cost_12 == 0).OnlyEnforceIf([both_assigned, task1_before_task2.Not()])
                    model.Add(setup_cost_12 == 0).OnlyEnforceIf(both_assigned.Not())
                    
                    # 반대 순서 (작업2 -> 작업1)
                    start_1, _, _, _ = task_vars[welder.welder_id][defect_id_1]
                    _, end_2, _, _ = task_vars[welder.welder_id][defect_id_2]
                    
                    model.Add(end_2 < start_1).OnlyEnforceIf([both_assigned, task1_before_task2.Not()])
                    
                    # 반대 방향 overhead 계산
                    if setup_2 != setup_1:
                        travel_to_setup_rev = self.get_travel_time(loc_2, self.setup_location_id)
                        setup_time_rev = self.get_setup_time(setup_1)
                        travel_to_work_rev = self.get_travel_time(self.setup_location_id, loc_1)
                        total_overhead_rev = travel_to_setup_rev + setup_time_rev + travel_to_work_rev
                    else:
                        total_overhead_rev = self.get_travel_time(loc_2, loc_1)
                    
                    model.Add(start_1 >= end_2 + total_overhead_rev).OnlyEnforceIf([both_assigned, task1_before_task2.Not()])
        
        #5. F,G구역 동시 작업X
        for t in range(horizon):
            working_at_f = []
            working_at_g = []
            
            for welder_id in task_vars:
                for defect_id in task_vars[welder_id]:
                    start_var, end_var, _, is_assigned_var = task_vars[welder_id][defect_id]
                    loc = defect_locations[defect_id]
                    
                    is_working_at_t = model.NewBoolVar(f'working_w{welder_id}_d{defect_id}_t{t}')
                    
                    model.Add(start_var <= t).OnlyEnforceIf([is_assigned_var, is_working_at_t])
                    model.Add(end_var > t).OnlyEnforceIf([is_assigned_var, is_working_at_t])
                    
                    if loc == 6:
                        working_at_f.append(is_working_at_t)
                    elif loc == 7:
                        working_at_g.append(is_working_at_t)
            
            if working_at_f and working_at_g:
                model.Add(sum(working_at_f) + sum(working_at_g) <= 1)
        
        #6.목적함수 세팅
        objective_terms = []
        
        for defect in defects:
            severity = int(calculate_severity_score(defect) * 100)
            for welder in welders:
                if (welder.welder_id, defect.defect_id) in is_assigned:
                    objective_terms.append(
                        severity * is_assigned[(welder.welder_id, defect.defect_id)]
                    )
        
        lambda_weight = 10
        
        for welder_id in travel_cost_vars:
            for (d1, d2), travel_var in travel_cost_vars[welder_id].items():
                objective_terms.append(-lambda_weight * travel_var)
        
        mu_weight = 20
        
        for welder_id in setup_cost_vars:
            for (d1, d2), setup_var in setup_cost_vars[welder_id].items():
                objective_terms.append(-mu_weight * setup_var)
        
        model.Maximize(sum(objective_terms))
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0
        
        status = solver.Solve(model)
        
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            raise Exception(f"No feasible solution found. Status: {solver.StatusName(status)}")
        batch = ScheduleBatch(
            target_date=datetime.strptime(target_date, '%Y-%m-%d').date(),
            target_session=target_session,
            status='confirmed'
        )
        db.session.add(batch)
        db.session.flush()
        
        assignments = []
        total_travel_cost = 0
        total_setup_cost = 0
        
        for welder in welders:
            if welder.welder_id not in task_vars:
                continue
            
            for defect_id in task_vars[welder.welder_id]:
                start_var, end_var, _, is_assigned_var = task_vars[welder.welder_id][defect_id]
                
                if solver.Value(is_assigned_var) == 1:
                    start_minutes = solver.Value(start_var)
                    end_minutes = solver.Value(end_var)
                    
                    defect = next(d for d in defects if d.defect_id == defect_id)
                    
                    assignments.append({
                        'welder_id': welder.welder_id,
                        'defect_id': defect_id,
                        'start_minutes': start_minutes,
                        'end_minutes': end_minutes,
                        'severity': calculate_severity_score(defect)
                    })
        
        #실제 발생한 이동/셋업 비용 계산
        for welder_id in travel_cost_vars:
            for (d1, d2), travel_var in travel_cost_vars[welder_id].items():
                total_travel_cost += solver.Value(travel_var)
        
        for welder_id in setup_cost_vars:
            for (d1, d2), setup_var in setup_cost_vars[welder_id].items():
                total_setup_cost += solver.Value(setup_var)
        
        assignments.sort(key=lambda x: (x['welder_id'], x['start_minutes']))
        
        #ScheduleJob 생성
        jobs = []
        for job_order, assignment in enumerate(assignments, start=1):
            job_start = session_start + timedelta(minutes=assignment['start_minutes'])
            job_end = session_start + timedelta(minutes=assignment['end_minutes'])
            
            job = ScheduleJob(
                batch_id=batch.batch_id,
                welder_id=assignment['welder_id'],
                defect_id=assignment['defect_id'],
                job_order=job_order,
                estimated_start_time=job_start,
                estimated_end_time=job_end,
                status='pending'
            )
            jobs.append(job)
        
        db.session.bulk_save_objects(jobs)
        db.session.commit()
        
        #API 응답 용으로 비용 정보를 배치 객체에 임시 저장
        batch.total_travel_cost = total_travel_cost
        batch.total_setup_cost = total_setup_cost
        batch.solver_time = solver.WallTime()
        
        return batch