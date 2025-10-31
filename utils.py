import os
import logging
import numpy as np
import datetime
from models import SensorData, LandslideEvent, RiskZone, EmergencyFacility, Alert, MonitoredLocation, RiskAssessment
from app import db

logger = logging.getLogger(__name__)

def calculate_risk_score(rainfall, temperature, soil_moisture, historical_data=None):
    """
    Calculate landslide risk score based on sensor data and historical information
    
    Parameters:
    - rainfall: float, current rainfall in mm
    - temperature: float, current temperature in Celsius
    - soil_moisture: float, current soil moisture percentage
    - historical_data: list of historical data points (optional)
    
    Returns:
    - risk_score: float between 0-10, with 10 being highest risk
    """
    try:
        # Base weights for different factors
        rainfall_weight = 0.5  # Heavy rainfall is a major trigger
        soil_moisture_weight = 0.3  # Saturated soil increases risk
        temperature_weight = 0.2  # Temperature affects soil conditions
        
        # Normalize factors to a 0-1 scale
        
        # Rainfall risk: 0-25mm low risk, 25-100mm medium, >100mm high
        rainfall_risk = min(1.0, rainfall / 100.0)
        
        # Soil moisture risk: <20% low, 20-60% medium, >60% high
        soil_moisture_risk = min(1.0, soil_moisture / 100.0)
        
        # Temperature risk: extreme temperatures (very high or low) increase risk
        # Assuming optimal temperature is around 15°C
        temp_deviation = abs(temperature - 15) / 20.0  # Normalize
        temperature_risk = min(1.0, temp_deviation)
        
        # Calculate weighted score
        base_risk = (rainfall_weight * rainfall_risk + 
                    soil_moisture_weight * soil_moisture_risk + 
                    temperature_weight * temperature_risk)
        
        # Scale to 0-10
        risk_score = base_risk * 10.0
        
        # Add historical risk factor if available
        if historical_data:
            # If there are historical landslides in similar conditions, increase risk
            historical_risk = analyze_historical_data(rainfall, temperature, soil_moisture, historical_data)
            risk_score = min(10.0, risk_score + historical_risk)
        
        return round(risk_score, 2)
        
    except Exception as e:
        logger.error(f"Error calculating risk score: {str(e)}")
        return 0.0

def analyze_historical_data(rainfall, temperature, soil_moisture, historical_data):
    """
    Analyze historical landslide data to determine additional risk factor
    
    Parameters:
    - rainfall: current rainfall
    - temperature: current temperature
    - soil_moisture: current soil moisture
    - historical_data: list of historical data points
    
    Returns:
    - additional_risk: additional risk factor based on historical patterns
    """
    try:
        if not historical_data:
            return 0.0
        
        similar_conditions_count = 0
        total_records = len(historical_data)
        
        for record in historical_data:
            # Check if current conditions are similar to historical landslide conditions
            if (abs(record['rainfall'] - rainfall) < 10 and
                abs(record['temperature'] - temperature) < 5 and
                abs(record['soil_moisture'] - soil_moisture) < 10):
                similar_conditions_count += 1
        
        # Calculate similarity ratio
        similarity_ratio = similar_conditions_count / total_records if total_records > 0 else 0
        
        # Additional risk factor (0-2 scale)
        additional_risk = similarity_ratio * 2.0
        
        return additional_risk
        
    except Exception as e:
        logger.error(f"Error analyzing historical data: {str(e)}")
        return 0.0

def generate_alert(risk_score, location_lat, location_lng):
    """
    Generate alert based on risk score
    
    Parameters:
    - risk_score: float between 0-10
    - location_lat: latitude of location
    - location_lng: longitude of location
    
    Returns:
    - alert: Alert object or None if no alert is needed
    """
    try:
        if risk_score >= 7.0:
            message = "CRITICAL ALERT: Very high landslide risk detected. Immediate evacuation recommended."
            risk_level = 10
        elif risk_score >= 5.0:
            message = "HIGH ALERT: Significant landslide risk detected. Prepare for possible evacuation."
            risk_level = 8
        elif risk_score >= 3.0:
            message = "MODERATE ALERT: Elevated landslide risk. Monitor conditions closely."
            risk_level = 5
        else:
            # No alert needed for low risk
            return None
        
        # Create new alert
        alert = Alert(
            risk_level=risk_level,
            message=message,
            location_lat=location_lat,
            location_lng=location_lng,
            is_active=True
        )
        
        return alert
        
    except Exception as e:
        logger.error(f"Error generating alert: {str(e)}")
        return None

def get_uttar_pradesh_risk_zones():
    """
    Get landslide-prone areas in Uttar Pradesh
    
    Returns:
    - risk_zones: list of risk zone dictionaries
    """
    try:
        # Query database for risk zones
        risk_zones = RiskZone.query.all()
        
        # Convert to list of dictionaries
        zones_list = [zone.to_dict() for zone in risk_zones]
        
        return zones_list
        
    except Exception as e:
        logger.error(f"Error retrieving risk zones: {str(e)}")
        return []

def get_emergency_facilities(facility_type=None):
    """
    Get emergency facilities (hospitals, rescue centers, mitigation centers)
    
    Parameters:
    - facility_type: optional filter for facility type
    
    Returns:
    - facilities: list of facility dictionaries
    """
    try:
        # Query database for facilities
        if facility_type:
            facilities = EmergencyFacility.query.filter_by(facility_type=facility_type).all()
        else:
            facilities = EmergencyFacility.query.all()
        
        # Convert to list of dictionaries
        facilities_list = [facility.to_dict() for facility in facilities]
        
        return facilities_list
        
    except Exception as e:
        logger.error(f"Error retrieving emergency facilities: {str(e)}")
        return []

def get_recent_sensor_data(hours=24):
    """
    Get recent sensor data for the specified time period
    
    Parameters:
    - hours: number of hours to look back
    
    Returns:
    - sensor_data: list of sensor data dictionaries
    """
    try:
        # Calculate time threshold
        time_threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        
        # Query database for recent sensor data
        data = SensorData.query.filter(SensorData.timestamp >= time_threshold).order_by(SensorData.timestamp).all()
        
        # Convert to list of dictionaries
        data_list = [item.to_dict() for item in data]
        
        return data_list
        
    except Exception as e:
        logger.error(f"Error retrieving recent sensor data: {str(e)}")
        return []

def get_active_alerts():
    """
    Get all active alerts
    
    Returns:
    - alerts: list of active alert dictionaries
    """
    try:
        # Query database for active alerts
        alerts = Alert.query.filter_by(is_active=True).order_by(Alert.timestamp.desc()).all()
        
        # Convert to list of dictionaries
        alerts_list = [alert.to_dict() for alert in alerts]
        
        return alerts_list
        
    except Exception as e:
        logger.error(f"Error retrieving active alerts: {str(e)}")
        return []

def calculate_enhanced_risk_score(rainfall, temperature, soil_moisture, historical_data=None, terrain_type=None, vegetation_density=None):
    """
    Calculate enhanced landslide risk score based on sensor data and terrain information
    
    Parameters:
    - rainfall: float, current rainfall in mm
    - temperature: float, current temperature in Celsius
    - soil_moisture: float, current soil moisture percentage
    - historical_data: list of historical data points (optional)
    - terrain_type: string, type of terrain (optional)
    - vegetation_density: float, vegetation density percentage (optional)
    
    Returns:
    - risk_data: dictionary with risk score and factor contributions
    """
    try:
        # Base weights for different factors
        rainfall_weight = 0.45  # Heavy rainfall is a major trigger
        soil_moisture_weight = 0.25  # Saturated soil increases risk
        temperature_weight = 0.15  # Temperature affects soil conditions
        terrain_weight = 0.10  # Terrain type affects stability
        vegetation_weight = 0.05  # Vegetation helps stabilize soil
        
        # Normalize factors to a 0-1 scale
        
        # Rainfall risk: 0-25mm low risk, 25-100mm medium, >100mm high
        rainfall_risk = min(1.0, rainfall / 100.0)
        
        # Soil moisture risk: <20% low, 20-60% medium, >60% high
        soil_moisture_risk = min(1.0, soil_moisture / 100.0)
        
        # Temperature risk: extreme temperatures (very high or low) increase risk
        # Assuming optimal temperature is around 15°C
        temp_deviation = abs(temperature - 15) / 20.0  # Normalize
        temperature_risk = min(1.0, temp_deviation)
        
        # Terrain risk based on type (mountain > hill > plain)
        terrain_risk = 0.5  # Default moderate risk
        if terrain_type:
            if 'mountain' in terrain_type.lower():
                terrain_risk = 0.9
            elif 'hill' in terrain_type.lower():
                terrain_risk = 0.6
            elif 'plain' in terrain_type.lower():
                terrain_risk = 0.2
        
        # Vegetation risk (inverse of density - more vegetation means less risk)
        vegetation_risk = 0.5  # Default moderate risk
        if vegetation_density is not None:
            vegetation_risk = 1.0 - (min(1.0, vegetation_density / 100.0))
        
        # Calculate weighted contributions of each factor
        rainfall_contribution = rainfall_weight * rainfall_risk
        soil_moisture_contribution = soil_moisture_weight * soil_moisture_risk
        temperature_contribution = temperature_weight * temperature_risk
        terrain_contribution = terrain_weight * terrain_risk
        vegetation_contribution = vegetation_weight * vegetation_risk
        
        # Calculate base risk score
        base_risk = (rainfall_contribution + 
                    soil_moisture_contribution + 
                    temperature_contribution +
                    terrain_contribution +
                    vegetation_contribution)
        
        # Scale to 0-10
        risk_score = base_risk * 10.0
        
        # Add historical risk factor if available
        historical_contribution = 0.0
        if historical_data:
            # If there are historical landslides in similar conditions, increase risk
            historical_risk = analyze_historical_data(rainfall, temperature, soil_moisture, historical_data)
            historical_contribution = historical_risk
            risk_score = min(10.0, risk_score + historical_contribution)
        
        # Prepare factor contributions for detailed analysis
        factor_contributions = {
            'rainfall_factor': round(rainfall_contribution * 10.0, 1),
            'soil_moisture_factor': round(soil_moisture_contribution * 10.0, 1),
            'temperature_factor': round(temperature_contribution * 10.0, 1),
            'terrain_factor': round(terrain_contribution * 10.0, 1),
            'vegetation_factor': round(vegetation_contribution * 10.0, 1),
            'historical_factor': round(historical_contribution, 1)
        }
        
        risk_data = {
            'risk_score': round(risk_score, 1),
            'factor_contributions': factor_contributions
        }
        
        return risk_data
        
    except Exception as e:
        logger.error(f"Error calculating enhanced risk score: {str(e)}")
        return {
            'risk_score': 0.0,
            'factor_contributions': {
                'rainfall_factor': 0.0,
                'soil_moisture_factor': 0.0,
                'temperature_factor': 0.0,
                'terrain_factor': 0.0,
                'vegetation_factor': 0.0,
                'historical_factor': 0.0
            }
        }

def assess_multiple_locations():
    """
    Assess landslide risk for all monitored locations
    
    Returns:
    - assessment_results: list of risk assessment results for all locations
    """
    try:
        # Get all active monitored locations
        locations = MonitoredLocation.query.filter_by(is_active=True).all()
        
        if not locations:
            logger.warning("No active monitored locations found")
            return []
        
        # Get recent sensor data (last 24 hours)
        sensor_data = get_recent_sensor_data(hours=24)
        
        # Get historical landslide events
        historical_events = LandslideEvent.query.all()
        historical_data = [event.to_dict() for event in historical_events]
        
        assessment_results = []
        
        for location in locations:
            # Find closest sensor data to this location
            closest_sensor = find_closest_sensor_data(location.location_lat, location.location_lng, sensor_data)
            
            if not closest_sensor:
                logger.warning(f"No nearby sensor data found for location: {location.name}")
                continue
            
            # Calculate risk score with all available factors
            risk_data = calculate_enhanced_risk_score(
                rainfall=closest_sensor['rainfall'],
                temperature=closest_sensor['temperature'],
                soil_moisture=closest_sensor['soil_moisture'],
                historical_data=historical_data,
                terrain_type=location.terrain_type,
                vegetation_density=location.vegetation_density
            )
            
            # Create and store risk assessment
            assessment = RiskAssessment(
                location_id=location.id,
                risk_score=risk_data['risk_score'],
                rainfall_factor=risk_data['factor_contributions']['rainfall_factor'],
                temperature_factor=risk_data['factor_contributions']['temperature_factor'],
                soil_moisture_factor=risk_data['factor_contributions']['soil_moisture_factor'],
                historical_factor=risk_data['factor_contributions']['historical_factor'],
                terrain_factor=risk_data['factor_contributions']['terrain_factor']
            )
            
            db.session.add(assessment)
            
            # Generate alert if risk is high
            if risk_data['risk_score'] >= 5.0:
                alert = generate_alert(risk_data['risk_score'], location.location_lat, location.location_lng)
                if alert:
                    db.session.add(alert)
            
            # Calculate infrastructure resilience score
            resilience_data = calculate_infrastructure_resilience(
                location_name=location.name,
                risk_score=risk_data['risk_score']
            )
            
            # Prepare result for API
            result = {
                'location': location.to_dict(),
                'risk_assessment': {
                    'risk_score': risk_data['risk_score'],
                    'factor_contributions': risk_data['factor_contributions'],
                    'timestamp': datetime.datetime.utcnow().isoformat(),
                    'sensor_data': {
                        'rainfall': closest_sensor['rainfall'],
                        'temperature': closest_sensor['temperature'],
                        'soil_moisture': closest_sensor['soil_moisture']
                    }
                },
                'infrastructure_resilience': resilience_data
            }
            
            assessment_results.append(result)
        
        # Commit all database changes
        db.session.commit()
        
        return assessment_results
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assessing multiple locations: {str(e)}")
        return []

def find_closest_sensor_data(lat, lng, sensor_data_list):
    """
    Find the closest sensor data point to a given location
    
    Parameters:
    - lat: latitude of location
    - lng: longitude of location
    - sensor_data_list: list of sensor data dictionaries
    
    Returns:
    - closest_sensor: dictionary of closest sensor data or None if list is empty
    """
    if not sensor_data_list:
        return None
    
    # Find most recent data point first (assuming sorted by timestamp)
    recent_data = sensor_data_list[-1]
    
    # In a real system, we would calculate actual distance and find closest
    # For demo purposes, we'll just use the most recent data
    return recent_data

def get_monitored_locations():
    """
    Get all monitored locations
    
    Returns:
    - locations: list of location dictionaries
    """
    try:
        # Query database for all monitored locations
        locations = MonitoredLocation.query.all()
        
        # Convert to list of dictionaries
        locations_list = [location.to_dict() for location in locations]
        
        return locations_list
        
    except Exception as e:
        logger.error(f"Error retrieving monitored locations: {str(e)}")
        return []

def calculate_infrastructure_resilience(location_name, risk_score, infrastructure_data=None):
    """
    Calculate infrastructure resilience score based on infrastructure type, age, maintenance, and current risk factors
    
    Parameters:
    - location_name: string, name of the location for predefined infrastructure data
    - risk_score: float, current landslide risk score (0-10)
    - infrastructure_data: dict, custom infrastructure data (optional)
    
    Returns:
    - resilience_data: dictionary with resilience score and factor contributions
    """
    try:
        # Define infrastructure data for known locations if not provided
        if infrastructure_data is None:
            # Default infrastructure data by location
            infrastructure_database = {
                "Mirzapur": {
                    "building_density": 65,  # percentage area covered by buildings
                    "building_age": 15,      # average age in years
                    "road_quality": 72,      # percentage quality (0-100)
                    "bridge_count": 4,       # number of major bridges
                    "bridge_age": 10,        # average age of bridges in years
                    "drain_capacity": 60,    # percentage of ideal capacity
                    "utility_resilience": 68, # percentage (0-100)
                    "emergency_readiness": 75, # percentage (0-100)
                    "recent_maintenance": True # whether maintenance was done in the last year
                },
                "Sonbhadra": {
                    "building_density": 40,
                    "building_age": 20,
                    "road_quality": 55,
                    "bridge_count": 2,
                    "bridge_age": 25,
                    "drain_capacity": 45,
                    "utility_resilience": 50,
                    "emergency_readiness": 60,
                    "recent_maintenance": False
                },
                "Chandauli": {
                    "building_density": 55,
                    "building_age": 12,
                    "road_quality": 78,
                    "bridge_count": 5,
                    "bridge_age": 8,
                    "drain_capacity": 70,
                    "utility_resilience": 65,
                    "emergency_readiness": 70,
                    "recent_maintenance": True
                },
                "Varanasi": {
                    "building_density": 85,
                    "building_age": 35,  # older, historical buildings
                    "road_quality": 65,
                    "bridge_count": 8,
                    "bridge_age": 18,
                    "drain_capacity": 50,
                    "utility_resilience": 60,
                    "emergency_readiness": 80,
                    "recent_maintenance": True
                },
                "Chitrakoot": {
                    "building_density": 45,
                    "building_age": 22,
                    "road_quality": 60,
                    "bridge_count": 3,
                    "bridge_age": 14,
                    "drain_capacity": 55,
                    "utility_resilience": 58,
                    "emergency_readiness": 65,
                    "recent_maintenance": False
                },
                "Allahabad": {
                    "building_density": 75,
                    "building_age": 25,
                    "road_quality": 70,
                    "bridge_count": 6,
                    "bridge_age": 15,
                    "drain_capacity": 65,
                    "utility_resilience": 70,
                    "emergency_readiness": 85,
                    "recent_maintenance": True
                }
            }
            
            # Use location-specific data or default to a moderate resilience profile
            infrastructure_data = infrastructure_database.get(location_name, {
                "building_density": 60,
                "building_age": 20,
                "road_quality": 65,
                "bridge_count": 4,
                "bridge_age": 15,
                "drain_capacity": 60,
                "utility_resilience": 65,
                "emergency_readiness": 70,
                "recent_maintenance": False
            })
        
        # Initialize factor scores
        factors = {}
        
        # Calculate building resilience factor (newer buildings with lower density are more resilient)
        building_age_factor = max(0, min(10, (40 - infrastructure_data.get("building_age", 20)) / 4))
        building_density_factor = max(0, min(10, (100 - infrastructure_data.get("building_density", 60)) / 10))
        factors["building_resilience"] = (building_age_factor + building_density_factor) / 2
        
        # Calculate transportation infrastructure resilience
        road_factor = infrastructure_data.get("road_quality", 65) / 10
        bridge_age_factor = max(0, min(10, (50 - infrastructure_data.get("bridge_age", 15)) / 5))
        bridge_count_factor = min(10, infrastructure_data.get("bridge_count", 4) * 1.5)
        factors["transportation_resilience"] = (road_factor + bridge_age_factor + bridge_count_factor) / 3
        
        # Calculate drainage resilience
        factors["drainage_resilience"] = infrastructure_data.get("drain_capacity", 60) / 10
        
        # Calculate utility resilience (power, water, communications)
        factors["utility_resilience"] = infrastructure_data.get("utility_resilience", 65) / 10
        
        # Calculate emergency response readiness
        factors["emergency_readiness"] = infrastructure_data.get("emergency_readiness", 70) / 10
        
        # Maintenance bonus
        maintenance_bonus = 1.0 if infrastructure_data.get("recent_maintenance", False) else 0.0
        factors["maintenance_bonus"] = maintenance_bonus
        
        # Calculate base resilience score (without considering current risk)
        base_resilience = (
            factors["building_resilience"] * 0.25 +
            factors["transportation_resilience"] * 0.25 +
            factors["drainage_resilience"] * 0.2 +
            factors["utility_resilience"] * 0.15 +
            factors["emergency_readiness"] * 0.15 +
            factors["maintenance_bonus"] * 0.5  # bonus points for recent maintenance
        )
        
        # Risk adaptability factor - how well infrastructure can handle the current risk
        # (higher risk means infrastructure is tested more severely)
        risk_adaptability = max(0, 10 - (risk_score * 0.5))
        factors["risk_adaptability"] = risk_adaptability
        
        # Final resilience score calculation
        resilience_score = (base_resilience * 0.7) + (risk_adaptability * 0.3)
        
        # Apply random small variation for dynamic display (±0.3)
        variation = (np.random.random() * 0.6) - 0.3
        resilience_score += variation
        
        # Ensure score is within 0-10 range
        resilience_score = max(0, min(10, resilience_score))
        
        # Create resilience data object
        resilience_data = {
            "location": location_name,
            "resilience_score": round(resilience_score, 2),
            "factors": {k: round(v, 2) for k, v in factors.items()},
            "risk_score": risk_score,
            "infrastructure_data": infrastructure_data,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        return resilience_data
        
    except Exception as e:
        logger.error(f"Error calculating infrastructure resilience: {str(e)}")
        return {
            "location": location_name,
            "resilience_score": 5.0,
            "factors": {},
            "risk_score": risk_score,
            "infrastructure_data": {},
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

def get_seismic_data(location_name=None, hours=24):
    """
    Get seismic data for a specific location or all monitored locations
    
    Parameters:
    - location_name: string, optional filter for a specific location
    - hours: number of hours to look back
    
    Returns:
    - seismic_data: list of seismic readings with location information
    """
    try:
        # Define sample seismic data for Uttar Pradesh districts
        seismic_regions = [
            "Mirzapur",
            "Sonbhadra",
            "Chandauli",
            "Varanasi",
            "Chitrakoot",
            "Allahabad"
        ]
        
        # Filter by location if specified
        if location_name:
            if location_name in seismic_regions:
                regions = [location_name]
            else:
                return []
        else:
            regions = seismic_regions
        
        result = []
        current_time = datetime.datetime.utcnow()
        
        # Generate seismic data for each region
        for region in regions:
            # Base magnitude for each region (different baseline per region)
            base_magnitudes = {
                "Mirzapur": 0.8,
                "Sonbhadra": 1.2,
                "Chandauli": 0.5,
                "Varanasi": 0.4,
                "Chitrakoot": 1.0,
                "Allahabad": 0.6
            }
            
            base_magnitude = base_magnitudes.get(region, 0.7)
            
            # Create data points for the requested time period
            for hour in range(hours):
                # More recent times have more data points
                points_per_hour = max(1, min(6, int((hours - hour) / 2)))
                
                for i in range(points_per_hour):
                    # Calculate timestamp
                    time_offset = datetime.timedelta(hours=hour, minutes=i*(60//points_per_hour))
                    timestamp = current_time - time_offset
                    
                    # Generate realistic seismic data
                    # Base magnitude + random component + small time-based pattern
                    hour_factor = abs(np.sin(timestamp.hour / 24.0 * np.pi)) * 0.3
                    random_factor = (np.random.random() * 0.6) - 0.2
                    
                    magnitude = base_magnitude + hour_factor + random_factor
                    magnitude = max(0.1, min(5.0, magnitude))  # Limit range
                    
                    # Occasionally add a small aftershock or foreshock pattern
                    if np.random.random() < 0.1:  # 10% chance
                        aftershock_pattern = 0.8 * np.exp(-i/5) if i > 0 else 0
                        magnitude += aftershock_pattern
                    
                    # Depth varies by region and has some randomness
                    base_depth = {
                        "Mirzapur": 8,
                        "Sonbhadra": 12,
                        "Chandauli": 7,
                        "Varanasi": 5,
                        "Chitrakoot": 15,
                        "Allahabad": 9
                    }.get(region, 10)
                    
                    depth = base_depth + (np.random.random() * 6) - 3
                    depth = max(2, depth)  # Minimum depth of 2km
                    
                    # Add data point
                    data_point = {
                        "region": region,
                        "timestamp": timestamp.isoformat(),
                        "magnitude": round(magnitude, 2),
                        "depth": round(depth, 1),
                        "location": get_region_coordinates(region)
                    }
                    
                    result.append(data_point)
        
        # Sort by timestamp, newest first
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating seismic data: {str(e)}")
        return []

def get_region_coordinates(region_name):
    """
    Get coordinates for a specific region in Uttar Pradesh
    
    Parameters:
    - region_name: string, name of the region
    
    Returns:
    - coordinates: dict with lat and lng
    """
    region_coordinates = {
        "Mirzapur": {"lat": 25.1464, "lng": 82.5697},
        "Sonbhadra": {"lat": 24.6772, "lng": 83.0593},
        "Chandauli": {"lat": 25.2571, "lng": 83.2760},
        "Varanasi": {"lat": 25.3176, "lng": 82.9739},
        "Chitrakoot": {"lat": 25.2138, "lng": 80.9019},
        "Allahabad": {"lat": 25.4358, "lng": 81.8463}
    }
    
    return region_coordinates.get(region_name, {"lat": 25.0, "lng": 82.0})

def get_recent_risk_assessments(hours=24):
    """
    Get recent risk assessments for all locations
    
    Parameters:
    - hours: number of hours to look back
    
    Returns:
    - assessments: list of assessment dictionaries grouped by location
    """
    try:
        # Calculate time threshold
        time_threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        
        # Query database for recent risk assessments
        recent_assessments = RiskAssessment.query.filter(
            RiskAssessment.timestamp >= time_threshold
        ).order_by(RiskAssessment.timestamp).all()
        
        # Group by location
        location_assessments = {}
        
        for assessment in recent_assessments:
            location_id = assessment.location_id
            
            if location_id not in location_assessments:
                location = MonitoredLocation.query.get(location_id)
                location_assessments[location_id] = {
                    'location': location.to_dict() if location else {'id': location_id, 'name': 'Unknown'},
                    'assessments': []
                }
            
            location_assessments[location_id]['assessments'].append(assessment.to_dict())
        
        return list(location_assessments.values())
        
    except Exception as e:
        logger.error(f"Error retrieving recent risk assessments: {str(e)}")
        return []

def init_sample_data():
    """Initialize sample data for demonstration purposes (if database is empty)"""
    try:
        # Delete related risk assessments first to avoid foreign key constraint issues
        try:
            RiskAssessment.query.delete()
            # Now we can safely delete monitored locations
            MonitoredLocation.query.delete()
        except Exception as e:
            logger.warning(f"Failed to clear previous data: {str(e)}")
        
        # Add monitored locations
        monitored_locations = [
            MonitoredLocation(
                name="Mirzapur",
                description="Agricultural land with frequent rainfall",
                location_lat=25.1420, 
                location_lng=82.5625,
                elevation=90.0,
                terrain_type="valley",
                vegetation_density=65.0,
                is_active=True
            ),
            MonitoredLocation(
                name="Chitrakoot",
                description="Steep slopes with sparse vegetation",
                location_lat=25.2100,
                location_lng=80.9150,
                elevation=320.0,
                terrain_type="mountain",
                vegetation_density=25.0,
                is_active=True
            ),
            MonitoredLocation(
                name="Sonbhadra",
                description="Surface mining with disturbed soil",
                location_lat=24.6750,
                location_lng=83.0620,
                elevation=185.0,
                terrain_type="hill",
                vegetation_density=10.0,
                is_active=True
            ),
            MonitoredLocation(
                name="Varanasi",
                description="River bank with erosion concerns",
                location_lat=25.3176,
                location_lng=82.9739,
                elevation=110.0,
                terrain_type="riverside",
                vegetation_density=40.0,
                is_active=True
            ),
            MonitoredLocation(
                name="Chandauli",
                description="Dense forest with moderate slopes",
                location_lat=25.2550,
                location_lng=83.2730,
                elevation=230.0,
                terrain_type="forest",
                vegetation_density=85.0,
                is_active=True
            ),
            MonitoredLocation(
                name="Allahabad",
                description="Historic city with floodplain region",
                location_lat=25.4358, 
                location_lng=81.8463,
                elevation=98.0,
                terrain_type="plain",
                vegetation_density=30.0,
                is_active=True
            )
        ]
        
        for location in monitored_locations:
            db.session.add(location)
        
        # Commit the monitored locations
        db.session.commit()
        
        # Only add sample data if the database is empty
        if RiskZone.query.count() == 0:
            # Add sample risk zones in Uttar Pradesh
            risk_zones = [
                RiskZone(name="Mirzapur Hills", location_lat=25.1480, location_lng=82.5689, risk_level=8,
                        description="Steep hills with history of landslides during monsoon season"),
                RiskZone(name="Chitrakoot Region", location_lat=25.2138, location_lng=80.9019, risk_level=7,
                        description="Rocky terrain with significant erosion risk"),
                RiskZone(name="Sonbhadra District", location_lat=24.6772, location_lng=83.0593, risk_level=9,
                        description="Mining area with unstable slopes and heavy rainfall"),
                RiskZone(name="Robertsganj Hills", location_lat=24.7142, location_lng=83.0656, risk_level=6,
                        description="Moderate risk zone with increasing development"),
                RiskZone(name="Chandauli Highlands", location_lat=25.2571, location_lng=83.2760, risk_level=5,
                        description="Mixed forest and agricultural land with moderate slopes")
            ]
            
            for zone in risk_zones:
                db.session.add(zone)
            
            # Add sample emergency facilities
            facilities = [
                EmergencyFacility(name="District Hospital Mirzapur", facility_type="hospital", 
                                location_lat=25.1460, location_lng=82.5710, 
                                contact_number="+91-5442-222222", address="Civil Lines, Mirzapur, UP"),
                EmergencyFacility(name="Chitrakoot Medical Center", facility_type="hospital", 
                                location_lat=25.2045, location_lng=80.9204, 
                                contact_number="+91-5198-224567", address="Karwi Road, Chitrakoot, UP"),
                EmergencyFacility(name="Sonbhadra Rescue Center", facility_type="rescue center", 
                                location_lat=24.6798, location_lng=83.0645, 
                                contact_number="+91-5444-233333", address="Main Road, Robertsganj, Sonbhadra, UP"),
                EmergencyFacility(name="UP State Disaster Response Center", facility_type="rescue center", 
                                location_lat=25.1502, location_lng=82.5744, 
                                contact_number="+91-5442-255555", address="Airport Road, Mirzapur, UP"),
                EmergencyFacility(name="Chandauli Landslide Mitigation Center", facility_type="mitigation center", 
                                location_lat=25.2610, location_lng=83.2790, 
                                contact_number="+91-5412-266666", address="Zamania Road, Chandauli, UP")
            ]
            
            for facility in facilities:
                db.session.add(facility)
                
            # Add sample monitored locations
            monitored_locations = [
                MonitoredLocation(
                    name="Mirzapur Agricultural Valley",
                    description="Agricultural land with frequent rainfall",
                    location_lat=25.1420, 
                    location_lng=82.5625,
                    elevation=90.0,
                    terrain_type="valley",
                    vegetation_density=65.0
                ),
                MonitoredLocation(
                    name="Chitrakoot Mountain Pass",
                    description="Steep slopes with sparse vegetation",
                    location_lat=25.2100,
                    location_lng=80.9150,
                    elevation=320.0,
                    terrain_type="mountain",
                    vegetation_density=25.0
                ),
                MonitoredLocation(
                    name="Sonbhadra Mining Area",
                    description="Surface mining with disturbed soil",
                    location_lat=24.6750,
                    location_lng=83.0620,
                    elevation=185.0,
                    terrain_type="hill",
                    vegetation_density=10.0
                ),
                MonitoredLocation(
                    name="Robertsganj River Bank",
                    description="River bank with erosion concerns",
                    location_lat=24.7125,
                    location_lng=83.0680,
                    elevation=110.0,
                    terrain_type="riverside",
                    vegetation_density=40.0
                ),
                MonitoredLocation(
                    name="Chandauli Forest Reserve",
                    description="Dense forest with moderate slopes",
                    location_lat=25.2550,
                    location_lng=83.2730,
                    elevation=230.0,
                    terrain_type="forest",
                    vegetation_density=85.0
                )
            ]
            
            for location in monitored_locations:
                db.session.add(location)
            
            # Commit changes
            db.session.commit()
            logger.info("Sample data initialized successfully")
        else:
            logger.info("Database already contains data, skipping initialization")
            
    except Exception as e:
        logger.error(f"Error initializing sample data: {str(e)}")
        db.session.rollback()
