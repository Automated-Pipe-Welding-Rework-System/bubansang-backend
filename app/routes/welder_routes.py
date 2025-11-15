from flask import Blueprint, request, jsonify
from app.models import Welder, WelderSkill, Skill, Location, SetupType
from app.extensions import db

welder_bp = Blueprint('welders', __name__, url_prefix='/api/welders')

#용접공 목록록
@welder_bp.route('', methods=['GET'])
def get_welders():
    status_param = request.args.get('status', 'available,working')
    status_list = [s.strip() for s in status_param.split(',')]
    
    welders = Welder.query.filter(Welder.status.in_(status_list)).all()
    
    result = []
    for welder in welders:
        location = Location.query.get(welder.current_location_id)
        setup = SetupType.query.get(welder.current_setup_id)
        
        welder_skills = WelderSkill.query.filter_by(welder_id=welder.welder_id).all()
        skills = []
        for ws in welder_skills:
            skill = Skill.query.get(ws.skill_id)
            if skill:
                skills.append({
                    'skill_id': skill.skill_id,
                    'process': skill.process,
                    'position': skill.position,
                    'position_level': skill.position_level,
                    'material': skill.material,
                    'skill_name': f"{skill.process}-{skill.position}-{skill.material}"
                })
        
        result.append({
            'welder_id': welder.welder_id,
            'welder_name': welder.welder_name,
            'current_location_id': welder.current_location_id,
            'current_location_name': location.location_name if location else None,
            'current_setup_id': welder.current_setup_id,
            'current_setup_name': setup.setup_name if setup else None,
            'current_defect_id': welder.current_defect_id,
            'status': welder.status,
            'shift_end_time': welder.shift_end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'skills': skills,
            'skill_count': len(skills)
        })
    
    return jsonify({
        'welders': result,
        'total': len(result)
    }), 200

#용접공 status 수정
@welder_bp.route('/<int:welder_id>', methods=['PATCH'])
def update_welder(welder_id):
    welder = Welder.query.get_or_404(welder_id)
    data = request.json
    
    # status 수정
    if 'status' in data:
        status = data['status']
        
        valid_statuses = ['available', 'on_break', 'working', 'off_duty']
        if status not in valid_statuses:
            return jsonify({'error': f'status must be one of {valid_statuses}'}), 400
        
        welder.status = status
    
    db.session.commit()
    
    return jsonify({
        'welder_id': welder.welder_id,
        'welder_name': welder.welder_name,
        'status': welder.status,
        'message': 'Welder updated successfully'
    }), 200

