from flask import Blueprint, request, jsonify
from app.models import Defect, Location, Skill, SetupType
from app.services.objective import calculate_severity_score, DEFECT_TYPES, CRITICAL_DEFECT_TYPES
from app.extensions import db

defect_bp = Blueprint('defects', __name__, url_prefix='/api/defects')


@defect_bp.route('', methods=['GET'])
def get_defects():
    status = request.args.get('status', 'pending')
    
    defects = Defect.query.filter_by(status=status).all()
    
    result = []
    for defect in defects:
        location = Location.query.get(defect.location_id)
        skill = Skill.query.get(defect.required_skill_id)
        setup = SetupType.query.get(defect.setup_type_id)
        
        severity_score = calculate_severity_score(defect)
        
        result.append({
            'defect_id': defect.defect_id,
            'pipe_id': defect.pipe_id,
            'location_id': defect.location_id,
            'location_name': location.location_name if location else None,
            'defect_type': defect.defect_type,
            'defect_type_name': DEFECT_TYPES.get(defect.defect_type, 'Unknown'),
            'is_critical': defect.defect_type in CRITICAL_DEFECT_TYPES,
            'p_in': defect.p_in,
            'p_out': defect.p_out,
            'severity_score': round(severity_score, 2),
            'required_skill_id': defect.required_skill_id,
            'required_skill': f"{skill.process}-{skill.position}-{skill.material}" if skill else None,
            'setup_type_id': defect.setup_type_id,
            'setup_type_name': setup.setup_name if setup else None,
            'priority_factor': defect.priority_factor,
            'rework_time': defect.rework_time,
            'status': defect.status,
            'created_at': defect.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({
        'defects': result,
        'total': len(result)
    }), 200


@defect_bp.route('/<int:defect_id>', methods=['PATCH'])
def update_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    data = request.json
    
    # priority_factor 수정 (반장용)
    if 'priority_factor' in data:
        priority_factor = data['priority_factor']
        
        if not isinstance(priority_factor, int) or priority_factor < 1 or priority_factor > 10:
            return jsonify({'error': 'priority_factor must be between 1 and 10'}), 400
        
        defect.priority_factor = priority_factor
    
    # status 수정
    if 'status' in data:
        status = data['status']
        
        valid_statuses = ['pending', 'in_progress', 'completed']
        if status not in valid_statuses:
            return jsonify({'error': f'status must be one of {valid_statuses}'}), 400
        
        defect.status = status
    
    db.session.commit()
    
    return jsonify({
        'defect_id': defect.defect_id,
        'priority_factor': defect.priority_factor,
        'status': defect.status,
        'severity_score': round(calculate_severity_score(defect), 2),
        'message': 'Defect updated successfully'
    }), 200


@defect_bp.route('/batch-priority', methods=['PATCH'])
def batch_update_priority():
    data = request.json
    
    if not data or 'priorities' not in data:
        return jsonify({'error': 'priorities array is required'}), 400
    
    priorities = data['priorities']
    
    updated_count = 0
    errors = []
    
    for item in priorities:
        defect_id = item.get('defect_id')
        priority_factor = item.get('priority_factor')
        
        if not defect_id or priority_factor is None:
            errors.append(f"Invalid item: {item}")
            continue
        
        if not isinstance(priority_factor, int) or priority_factor < 1 or priority_factor > 10:
            errors.append(f"Invalid priority_factor for defect {defect_id}: {priority_factor}")
            continue
        
        defect = Defect.query.get(defect_id)
        if not defect:
            errors.append(f"Defect {defect_id} not found")
            continue
        
        defect.priority_factor = priority_factor
        updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'message': f'Updated {updated_count} defects',
        'updated_count': updated_count,
        'errors': errors if errors else None
    }), 200
