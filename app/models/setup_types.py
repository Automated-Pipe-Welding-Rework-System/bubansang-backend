from app.extensions import db

class SetupType(db.Model):
    __tablename__ = 'setup_types'
    
    setup_type_id = db.Column(db.Integer, primary_key=True)
    setup_name = db.Column(db.String(100), nullable=False)
    setup_cost_minutes = db.Column(db.Integer, nullable=False)
    
    defects = db.relationship('Defect', backref='setup_type', lazy=True)
    welders = db.relationship('Welder', backref='current_setup', lazy=True)
    
    def __repr__(self):
        return f'<SetupType {self.setup_type_id}: {self.setup_name} ({self.setup_cost_minutes}min)>'

