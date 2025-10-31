from datetime import datetime
from app import db

class MonitoredLocation(db.Model):
    """Model for locations being actively monitored for landslides"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    elevation = db.Column(db.Float, nullable=True)  # in meters
    terrain_type = db.Column(db.String(50), nullable=True)  # e.g., mountain, hill, plain
    vegetation_density = db.Column(db.Float, nullable=True)  # percentage
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MonitoredLocation id={self.id} name={self.name}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            },
            'elevation': self.elevation,
            'terrain_type': self.terrain_type,
            'vegetation_density': self.vegetation_density,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SensorData(db.Model):
    """Model for storing sensor data from Raspberry Pi"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    rainfall = db.Column(db.Float, nullable=False)  # in mm
    temperature = db.Column(db.Float, nullable=False)  # in Celsius
    soil_moisture = db.Column(db.Float, nullable=False)  # percentage
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f"<SensorData id={self.id} timestamp={self.timestamp}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'rainfall': self.rainfall,
            'temperature': self.temperature,
            'soil_moisture': self.soil_moisture,
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            }
        }

class LandslideEvent(db.Model):
    """Model for historical landslide events"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    severity = db.Column(db.Integer, nullable=False)  # 1-10 scale
    description = db.Column(db.Text, nullable=True)
    before_image_url = db.Column(db.String(255), nullable=True)
    after_image_url = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<LandslideEvent id={self.id} timestamp={self.timestamp}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            },
            'severity': self.severity,
            'description': self.description,
            'before_image_url': self.before_image_url,
            'after_image_url': self.after_image_url
        }

class RiskZone(db.Model):
    """Model for landslide-prone areas"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.Integer, nullable=False)  # 1-10 scale
    description = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"<RiskZone id={self.id} name={self.name}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            },
            'risk_level': self.risk_level,
            'description': self.description
        }

class EmergencyFacility(db.Model):
    """Model for emergency facilities (hospitals, rescue centers)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    facility_type = db.Column(db.String(50), nullable=False)  # hospital, rescue center, mitigation center
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    contact_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"<EmergencyFacility id={self.id} name={self.name} type={self.facility_type}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'facility_type': self.facility_type,
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            },
            'contact_number': self.contact_number,
            'address': self.address
        }

class RiskAssessment(db.Model):
    """Model for storing risk assessments for monitored locations"""
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('monitored_location.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    risk_score = db.Column(db.Float, nullable=False)  # 0-10 scale
    rainfall_factor = db.Column(db.Float, nullable=False)  # contribution to risk
    temperature_factor = db.Column(db.Float, nullable=False)  # contribution to risk
    soil_moisture_factor = db.Column(db.Float, nullable=False)  # contribution to risk
    historical_factor = db.Column(db.Float, nullable=True)  # contribution based on history
    terrain_factor = db.Column(db.Float, nullable=True)  # contribution based on terrain
    
    # Relationship with MonitoredLocation
    location = db.relationship('MonitoredLocation', backref=db.backref('risk_assessments', lazy='dynamic'))
    
    def __repr__(self):
        return f"<RiskAssessment id={self.id} location_id={self.location_id} risk_score={self.risk_score}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'location_id': self.location_id,
            'timestamp': self.timestamp.isoformat(),
            'risk_score': self.risk_score,
            'rainfall_factor': self.rainfall_factor,
            'temperature_factor': self.temperature_factor,
            'soil_moisture_factor': self.soil_moisture_factor,
            'historical_factor': self.historical_factor,
            'terrain_factor': self.terrain_factor,
            'location_name': self.location.name if self.location else None
        }

class Alert(db.Model):
    """Model for landslide risk alerts"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    risk_level = db.Column(db.Integer, nullable=False)  # 1-10 scale
    message = db.Column(db.Text, nullable=False)
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<Alert id={self.id} risk_level={self.risk_level}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'risk_level': self.risk_level,
            'message': self.message,
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            },
            'is_active': self.is_active
        }
