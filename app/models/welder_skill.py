from app.extensions import db

class WelderSkill(db.Model):
    __tablename__ = 'welder_skills'
    
    welder_id = db.Column(db.BigInteger, db.ForeignKey('welders.welder_id'), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.skill_id'), primary_key=True)
    
    def __repr__(self):
        return f'<WelderSkill Welder:{self.welder_id} Skill:{self.skill_id}>'

