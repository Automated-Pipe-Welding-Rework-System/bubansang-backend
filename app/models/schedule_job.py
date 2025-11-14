from app.extensions import db
from datetime import datetime

class ScheduleJob(db.Model):
    __tablename__ = 'schedule_jobs'
    
    job_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.BigInteger, db.ForeignKey('schedule_batches.batch_id'), nullable=False)
    welder_id = db.Column(db.BigInteger, db.ForeignKey('welders.welder_id'), nullable=False)
    defect_id = db.Column(db.BigInteger, db.ForeignKey('defects.defect_id'), nullable=False)
    job_order = db.Column(db.SmallInteger, nullable=False)
    estimated_start_time = db.Column(db.DateTime, nullable=False)
    estimated_end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, started, completed, delayed
    
    def __repr__(self):
        return f'<ScheduleJob {self.job_id}: Batch {self.batch_id} Order {self.job_order} ({self.status})>'

