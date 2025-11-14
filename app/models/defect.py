from app.extensions import db
from datetime import datetime

class Defect(db.Model):
    __tablename__ = 'defects'
    
    defect_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    pipe_id = db.Column(db.BigInteger, db.ForeignKey('pipes.pipe_id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), nullable=False)
    defect_type = db.Column(db.Integer, nullable=False)  # 0-6: 균열, 용합불량, 용입부족, 기공, 슬래그섞임, 언더컷, 왜곡
    p_in = db.Column(db.Float, nullable=False)  # 내부 결함 심각도 (0-1)
    p_out = db.Column(db.Float, nullable=False)  # 외부 결함 심각도 (0-1)
    required_skill_id = db.Column(db.Integer, db.ForeignKey('skills.skill_id'), nullable=False)
    setup_type_id = db.Column(db.Integer, db.ForeignKey('setup_types.setup_type_id'), nullable=False)
    priority_factor = db.Column(db.Integer, nullable=False, default=1)  # 1-10, 1이 기본. 반장이 10까지 입력 가능
    rework_time = db.Column(db.Integer, nullable=False)  # 리워크 시간 (분)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, in_progress, completed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    welders = db.relationship('Welder', backref='current_defect_ref', lazy=True)
    schedule_jobs = db.relationship('ScheduleJob', backref='defect', lazy=True)
    
    def __repr__(self):
        return f'<Defect {self.defect_id}: Type {self.defect_type} at Location {self.location_id}>'
