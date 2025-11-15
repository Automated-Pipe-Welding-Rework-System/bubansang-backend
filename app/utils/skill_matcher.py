from app.models import WelderSkill, Skill


def check_skill_match(welder, defect):
    required_skill = Skill.query.get(defect.required_skill_id)
    welder_skills = WelderSkill.query.filter_by(welder_id=welder.welder_id).all()
    
    for ws in welder_skills:
        welder_skill = Skill.query.get(ws.skill_id)
        
        if welder_skill.process != required_skill.process:
            continue
        
        if welder_skill.material != required_skill.material:
            continue
        
        if welder_skill.position_level >= required_skill.position_level:
            return True
    
    return False


def get_available_welders(defect, welders):
    available = []
    
    for welder in welders:
        if welder.status not in ['available', 'working']:
            continue
        
        if check_skill_match(welder, defect):
            available.append(welder)
    
    return available

