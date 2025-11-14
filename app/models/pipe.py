from app.extensions import db

class Pipe(db.Model):
    __tablename__ = 'pipes'
    
    pipe_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    material = db.Column(db.String(100), nullable=False)  # 탄소강, 스테인리스강, 합강
    current_location_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), nullable=False)
    
    defects = db.relationship('Defect', backref='pipe', lazy=True)
    
    def __repr__(self):
        return f'<Pipe {self.pipe_id}: {self.material} at Location {self.current_location_id}>'

