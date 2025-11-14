from app.extensions import db
from datetime import datetime

class Welder(db.Model):
    __tablename__ = 'welders'
    
    welder_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    welder_name = db.Column(db.String(100), nullable=False)
    current_location_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), nullable=False)
    current_setup_id = db.Column(db.Integer, db.ForeignKey('setup_types.setup_type_id'), nullable=True)
    current_defect_id = db.Column(db.BigInteger, db.ForeignKey('defects.defect_id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='available')  # available, on_break, working, off_duty
    shift_end_time = db.Column(db.DateTime, nullable=False)
    
    welder_skills = db.relationship('WelderSkill', backref='welder', lazy=True)
    schedule_jobs = db.relationship('ScheduleJob', backref='welder', lazy=True)
    
    def __repr__(self):
        return f'<Welder {self.welder_id}: {self.welder_name} ({self.status})>'

