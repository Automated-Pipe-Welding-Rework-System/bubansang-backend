from app.extensions import db

class Location(db.Model):
    __tablename__ = 'location'
    
    location_id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False)
    
    travel_from = db.relationship('TravelMatrix', foreign_keys='TravelMatrix.from_location_id', backref='from_location', lazy=True)
    travel_to = db.relationship('TravelMatrix', foreign_keys='TravelMatrix.to_location_id', backref='to_location', lazy=True)
    concurrent_a = db.relationship('ConcurrentRestriction', foreign_keys='ConcurrentRestriction.location_a_id', backref='location_a', lazy=True)
    concurrent_b = db.relationship('ConcurrentRestriction', foreign_keys='ConcurrentRestriction.location_b_id', backref='location_b', lazy=True)
    pipes = db.relationship('Pipe', backref='current_location', lazy=True)
    defects = db.relationship('Defect', backref='location', lazy=True)
    welders = db.relationship('Welder', backref='current_location', lazy=True)
    
    def __repr__(self):
        return f'<Location {self.location_id}: {self.location_name}>'

