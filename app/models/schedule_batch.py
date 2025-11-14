from app.extensions import db
from datetime import datetime

class ScheduleBatch(db.Model):
    __tablename__ = 'schedule_batches'
    
    batch_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    target_date = db.Column(db.Date, nullable=False)
    target_session = db.Column(db.String(10), nullable=False)  # morning, afternoon, night
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, confirmed, in_progress
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    schedule_jobs = db.relationship('ScheduleJob', backref='batch', lazy=True)
    
    def __repr__(self):
        return f'<ScheduleBatch {self.batch_id}: {self.target_date} {self.target_session} ({self.status})>'

