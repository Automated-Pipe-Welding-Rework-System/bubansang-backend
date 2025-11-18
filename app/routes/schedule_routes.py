from flask import Blueprint, request, jsonify
from app.models import Defect, Welder, ScheduleBatch, ScheduleJob
from app.services.scheduler_ortools import ORToolsScheduler
from app.services.objective import calculate_severity_score, DEFECT_TYPES
from app.extensions import db

schedule_bp = Blueprint('schedules', __name__, url_prefix='/api/schedules')


@schedule_bp.route('/optimize', methods=['POST'])
def optimize_schedule():
    data = request.json
    
    target_date = data.get('target_date')
    target_session = data.get('target_session')
    
    if not target_date or not target_session:
        return jsonify({'error': 'target_date and target_session are required'}), 400
    
    if target_session not in ['morning', 'afternoon', 'night']:
        return jsonify({'error': 'target_session must be morning, afternoon, or night'}), 400
    
    # 결함 (구역 A, C, D 제외 - 작업 불가능 구역)
    defects = Defect.query.filter(
        Defect.status == 'pending',
        Defect.location_id.notin_([1, 3, 4])  # 구역 A, C, D 제외
    ).all()
    if not defects:
        return jsonify({'error': 'No pending defects found'}), 400
    
    #가능한 용접공
    welders = Welder.query.filter(Welder.status.in_(['available', 'working'])).all()
    if not welders:
        return jsonify({'error': 'No available welders found'}), 400
    
    try:
        scheduler = GreedyScheduler()
        batch = scheduler.schedule(defects, welders, target_date, target_session)
        
        return get_schedule_response(batch.batch_id)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Scheduling failed: {str(e)}'}), 500


@schedule_bp.route('/optimize2', methods=['POST'])
def optimize_schedule_ortools():
    data = request.json
    
    target_date = data.get('target_date')
    target_session = data.get('target_session')
    
    if not target_date or not target_session:
        return jsonify({'error': 'target_date and target_session are required'}), 400
    
    if target_session not in ['morning', 'afternoon', 'night']:
        return jsonify({'error': 'target_session must be morning, afternoon, or night'}), 400
    
    from datetime import datetime
    target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    # 이미 확정된 이전 스케쥴의 결함들은 버림.!
    session_order = {'morning': 1, 'afternoon': 2, 'night': 3}
    current_session_order = session_order[target_session]
    
    already_scheduled_defect_ids = set()
    
    # 전날까지의 모든 확정된 스케줄
    past_batches = ScheduleBatch.query.filter(
        ScheduleBatch.target_date < target_date_obj,
        ScheduleBatch.status == 'confirmed'
    ).all()
    
    for batch in past_batches:
        jobs = ScheduleJob.query.filter_by(batch_id=batch.batch_id).all()
        already_scheduled_defect_ids.update([job.defect_id for job in jobs])
    
    # 같은 날 이전 세션의 확정된 스케줄
    same_day_batches = ScheduleBatch.query.filter(
        ScheduleBatch.target_date == target_date_obj,
        ScheduleBatch.status == 'confirmed'
    ).all()
    
    for batch in same_day_batches:
        batch_session_order = session_order.get(batch.target_session, 0)
        if batch_session_order < current_session_order:
            jobs = ScheduleJob.query.filter_by(batch_id=batch.batch_id).all()
            already_scheduled_defect_ids.update([job.defect_id for job in jobs])
    
    # pending 상태이면서 이미 스케줄되지 않은 결함만 가져오기
    defects = Defect.query.filter(
        Defect.status == 'pending',
        Defect.location_id.notin_([1, 3, 4]),  # 구역 A, C, D 제외
        ~Defect.defect_id.in_(already_scheduled_defect_ids) if already_scheduled_defect_ids else True
    ).all()
    
    if not defects:
        return jsonify({'error': 'No pending defects found'}), 400
    
    # 가능한 용접공
    welders = Welder.query.filter(Welder.status.in_(['available', 'working'])).all()
    if not welders:
        return jsonify({'error': 'No available welders found'}), 400
    
    try:
        scheduler = ORToolsScheduler()
        batch = scheduler.schedule(defects, welders, target_date, target_session)
        
        return get_schedule_response(batch.batch_id, method='ortools')
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Scheduling failed: {str(e)}'}), 500


@schedule_bp.route('/<int:batch_id>', methods=['GET'])
def get_schedule(batch_id):
    return get_schedule_response(batch_id)


@schedule_bp.route('/query', methods=['GET'])
def query_schedule():
    """특정 날짜/세션의 스케줄 조회 (status 옵션: confirmed, draft, any)"""
    target_date = request.args.get('target_date')
    target_session = request.args.get('target_session')
    status_filter = request.args.get('status', 'any')  # 기본값: any (모든 상태)
    
    if not target_date or not target_session:
        return jsonify({'error': 'target_date and target_session are required'}), 400
    
    if target_session not in ['morning', 'afternoon', 'night']:
        return jsonify({'error': 'target_session must be morning, afternoon, or night'}), 400
    
    if status_filter not in ['confirmed', 'draft', 'any']:
        return jsonify({'error': 'status must be confirmed, draft, or any'}), 400
    
    # 해당 날짜/세션의 스케줄 찾기 (가장 최근 것)
    from datetime import datetime
    target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    query = ScheduleBatch.query.filter_by(
        target_date=target_date_obj,
        target_session=target_session
    )
    
    # status 필터 적용
    if status_filter == 'confirmed':
        query = query.filter_by(status='confirmed')
    elif status_filter == 'draft':
        query = query.filter_by(status='draft')
    # 'any'는 필터 없음
    
    batch = query.order_by(ScheduleBatch.created_at.desc()).first()
    
    if not batch:
        return jsonify({'message': f'No {status_filter if status_filter != "any" else ""} schedule found for this date and session'.strip()}), 404
    
    return get_schedule_response(batch.batch_id)


@schedule_bp.route('/<int:batch_id>/confirm', methods=['PATCH'])
def confirm_schedule(batch_id):
    """스케줄 확정"""
    batch = ScheduleBatch.query.get_or_404(batch_id)
    
    if batch.status == 'confirmed':
        return jsonify({'message': 'Schedule is already confirmed'}), 200
    
    # 기존의 같은 날짜/세션 스케줄이 있으면 draft로 변경
    existing_confirmed = ScheduleBatch.query.filter_by(
        target_date=batch.target_date,
        target_session=batch.target_session,
        status='confirmed'
    ).filter(ScheduleBatch.batch_id != batch_id).all()
    
    for old_batch in existing_confirmed:
        old_batch.status = 'draft'
    
    batch.status = 'confirmed'
    db.session.commit()
    
    return jsonify({
        'message': 'Schedule confirmed successfully',
        'batch_id': batch.batch_id,
        'status': batch.status
    }), 200


@schedule_bp.route('/welder/<int:welder_id>/ticket', methods=['GET'])
def get_welder_ticket(welder_id):
    target_date = request.args.get('target_date')
    target_session = request.args.get('target_session')
    
    if not target_date or not target_session:
        return jsonify({'error': 'target_date and target_session are required'}), 400
    
    # 해당 날짜/세션의 확정된 스케줄 찾기
    from datetime import datetime
    target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    batch = ScheduleBatch.query.filter_by(
        target_date=target_date_obj,
        target_session=target_session,
        status='confirmed'
    ).order_by(ScheduleBatch.created_at.desc()).first()
    
    if not batch:
        return jsonify({'error': 'No confirmed schedule found'}), 404
    
    # 해당 용접공의 작업 조회
    welder = Welder.query.get_or_404(welder_id)
    jobs = ScheduleJob.query.filter_by(
        batch_id=batch.batch_id,
        welder_id=welder_id
    ).order_by(ScheduleJob.job_order).all()
    
    if not jobs:
        return jsonify({'error': 'No jobs found for this welder'}), 404
    
    session_time_map = {
        'morning': '09:00-12:00',
        'afternoon': '13:00-18:00',
        'night': '19:00-22:00'
    }
    
    job_list = []
    for job in jobs:
        job_list.append({
            'job_id': job.job_id,
            'job_order': job.job_order,
            'defect_id': job.defect_id,
            'defect_type': job.defect.defect_type,
            'defect_type_name': DEFECT_TYPES.get(job.defect.defect_type, 'Unknown'),
            'location_id': job.defect.location_id,
            'location_name': job.defect.location.location_name,
            'severity_score': round(calculate_severity_score(job.defect), 2),
            'estimated_start_time': job.estimated_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'estimated_end_time': job.estimated_end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'rework_time': job.defect.rework_time,
            'status': job.status
        })
    
    # 용접공의 스킬 조회
    from app.models import WelderSkill, Skill
    welder_skills = WelderSkill.query.filter_by(welder_id=welder_id).all()
    skills = []
    for ws in welder_skills:
        skill = Skill.query.get(ws.skill_id)
        if skill:
            skills.append({
                'process': skill.process,
                'position': skill.position,
                'material': skill.material,
                'skill_name': f"{skill.process}-{skill.position}-{skill.material}"
            })
    
    return jsonify({
        'welder_id': welder.welder_id,
        'welder_name': welder.welder_name,
        'target_date': batch.target_date.strftime('%Y-%m-%d'),
        'target_session': batch.target_session,
        'session_time': session_time_map.get(batch.target_session, 'Unknown'),
        'shift_end_time': welder.shift_end_time.strftime('%H:%M'),
        'skills': skills,
        'total_jobs': len(jobs),
        'jobs': job_list
    }), 200


def get_schedule_response(batch_id, method='greedy'):
    batch = ScheduleBatch.query.get_or_404(batch_id)
    jobs = ScheduleJob.query.filter_by(batch_id=batch_id).order_by(ScheduleJob.job_order).all()
    
    session_time_map = {
        'morning': '09:00-12:00',
        'afternoon': '13:00-18:00',
        'night': '19:00-22:00'
    }
    
    total_severity = sum(calculate_severity_score(job.defect) for job in jobs)
    
    job_list = []
    for job in jobs:
        job_list.append({
            'job_id': job.job_id,
            'job_order': job.job_order,
            'welder_id': job.welder_id,
            'welder_name': job.welder.welder_name,
            'defect_id': job.defect_id,
            'defect_type': job.defect.defect_type,
            'defect_type_name': DEFECT_TYPES.get(job.defect.defect_type, 'Unknown'),
            'location_id': job.defect.location_id,
            'location_name': job.defect.location.location_name,
            'severity_score': round(calculate_severity_score(job.defect), 2),
            'estimated_start_time': job.estimated_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'estimated_end_time': job.estimated_end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'rework_time': job.defect.rework_time,
            'status': job.status
        })
    
    optimization_metrics = {
        'method': method,
        'total_severity_score': round(total_severity, 2),
        'total_defects_scheduled': len(jobs)
    }
    
    if hasattr(batch, 'total_travel_cost'):
        optimization_metrics['total_travel_time_minutes'] = batch.total_travel_cost
    if hasattr(batch, 'total_setup_cost'):
        optimization_metrics['total_setup_time_minutes'] = batch.total_setup_cost
    if hasattr(batch, 'solver_time'):
        optimization_metrics['solver_time_seconds'] = round(batch.solver_time, 2)
    
    return jsonify({
        'batch_id': batch.batch_id,
        'status': batch.status,
        'target_date': batch.target_date.strftime('%Y-%m-%d'),
        'target_session': batch.target_session,
        'session_time': session_time_map.get(batch.target_session, 'Unknown'),
        'created_at': batch.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'total_jobs': len(jobs),
        'optimization_metrics': optimization_metrics,
        'jobs': job_list
    }), 200

