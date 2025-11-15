from flask import Blueprint, request, jsonify
from app.models import Defect, Welder, ScheduleBatch, ScheduleJob
from app.services.scheduler_greedy import GreedyScheduler
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
    
    defects = Defect.query.filter(
        Defect.status == 'pending',
        Defect.location_id.notin_([1, 3, 4])  # 구역 A, C, D 제외
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

