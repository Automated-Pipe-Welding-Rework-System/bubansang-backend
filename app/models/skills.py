from app.extensions import db

class Skill(db.Model):
    __tablename__ = 'skills'
    
    skill_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    process = db.Column(db.String(10), nullable=False)  # SMAW, GTAW, GMAW, FCAW
    position = db.Column(db.String(5), nullable=False)  # 1G, 2G, 3G, 4G, 5G, 6G
    position_level = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4, 5, 6
    material = db.Column(db.String(20), nullable=False)  # 탄소강, 스테인리스강, 합강
    
    defects = db.relationship('Defect', backref='required_skill', lazy=True)
    welder_skills = db.relationship('WelderSkill', backref='skill', lazy=True)
    
    def __repr__(self):
        return f'<Skill {self.skill_id}: {self.process}-{self.position}-{self.material}>'

