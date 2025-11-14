from app.extensions import db

class ConcurrentRestriction(db.Model):
    __tablename__ = 'concurrent_restrictions'
    
    location_a_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), primary_key=True)
    location_b_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), primary_key=True)
    
    def __repr__(self):
        return f'<ConcurrentRestriction {self.location_a_id}↔{self.location_b_id}>'

