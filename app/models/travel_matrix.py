from app.extensions import db

class TravelMatrix(db.Model):
    __tablename__ = 'travel_matrix'
    
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), primary_key=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.location_id'), primary_key=True)
    travel_time_minutes = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<TravelMatrix {self.from_location_id}→{self.to_location_id}: {self.travel_time_minutes}min>'

