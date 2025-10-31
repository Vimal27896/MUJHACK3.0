import os
import random
import logging
import datetime
import requests
import json

logger = logging.getLogger(__name__)

# Configuration
RASPBERRY_PI_API_URL = os.environ.get("RASPBERRY_PI_API_URL", "")
RASPBERRY_PI_API_KEY = os.environ.get("RASPBERRY_PI_API_KEY", "")

# Default location (Mirzapur, Uttar Pradesh)
DEFAULT_LATITUDE = 25.1480
DEFAULT_LONGITUDE = 82.5689

def get_raspberry_pi_data():
    """
    Get real sensor data from Raspberry Pi
    
    Returns:
    - data: dictionary containing sensor readings
    
    Raises:
    - Exception: if unable to retrieve sensor data
    """
    try:
        api_url = os.environ.get('RASPBERRY_PI_API_URL')
        api_key = os.environ.get('RASPBERRY_PI_API_KEY')
        
        if not api_url:
            raise Exception("RASPBERRY_PI_API_URL environment variable not set")
            
        # Set up headers with API key if provided
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Set up headers with API key if provided
        headers = {}
        if RASPBERRY_PI_API_KEY:
            headers["Authorization"] = f"Bearer {RASPBERRY_PI_API_KEY}"
        
        # Make request to Raspberry Pi API
        response = requests.get(RASPBERRY_PI_API_URL, headers=headers, timeout=5)
        
        # Check if request was successful
        if response.status_code != 200:
            raise Exception(f"Failed to get sensor data: HTTP {response.status_code}")
        
        # Parse response
        data = response.json()
        
        # Validate data
        required_fields = ["rainfall", "temperature", "soil_moisture", "location"]
        for field in required_fields:
            if field not in data:
                raise Exception(f"Missing required field: {field}")
        
        # Return data
        return data
        
    except Exception as e:
        logger.error(f"Error getting Raspberry Pi data: {str(e)}")
        raise

def simulate_sensor_data(location_id=None):
    """
    Simulate sensor data for demonstration purposes
    
    Parameters:
    - location_id: optional ID for a specific monitored location
    
    Returns:
    - data: dictionary containing simulated sensor readings
    """
    try:
        # Locations in Uttar Pradesh with their baseline characteristics
        monitored_locations = [
            {
                "name": "Mirzapur Agricultural Valley",
                "lat": 25.1420, 
                "lng": 82.5625,
                "rainfall_factor": 1.0,  # Normal rainfall
                "temp_factor": 1.0,      # Normal temperature
                "moisture_factor": 1.2,  # Higher soil moisture (agricultural)
                "high_risk_chance": 0.2  # 20% chance of high risk conditions
            },
            {
                "name": "Chitrakoot Mountain Pass",
                "lat": 25.2100,
                "lng": 80.9150,
                "rainfall_factor": 1.3,  # Higher rainfall (mountain area)
                "temp_factor": 0.9,      # Slightly cooler (higher elevation)
                "moisture_factor": 0.8,  # Lower soil moisture (rocky terrain)
                "high_risk_chance": 0.25 # 25% chance of high risk conditions
            },
            {
                "name": "Sonbhadra Mining Area",
                "lat": 24.6750,
                "lng": 83.0620,
                "rainfall_factor": 0.9,  # Lower rainfall
                "temp_factor": 1.1,      # Higher temperatures
                "moisture_factor": 0.7,  # Drier soil (mining area)
                "high_risk_chance": 0.3  # 30% chance of high risk (disturbed soil)
            },
            {
                "name": "Robertsganj River Bank",
                "lat": 24.7125,
                "lng": 83.0680,
                "rainfall_factor": 1.0,  # Normal rainfall
                "temp_factor": 1.0,      # Normal temperature
                "moisture_factor": 1.4,  # Much higher soil moisture (river bank)
                "high_risk_chance": 0.35 # 35% chance of high risk (erosion)
            },
            {
                "name": "Chandauli Forest Reserve",
                "lat": 25.2550,
                "lng": 83.2730,
                "rainfall_factor": 1.1,  # Slightly higher rainfall (forest)
                "temp_factor": 0.95,     # Slightly cooler (forest cover)
                "moisture_factor": 1.0,  # Normal soil moisture
                "high_risk_chance": 0.15 # 15% chance of high risk (stable soil)
            }
        ]
        
        # Select a location (either by ID or randomly)
        if location_id is not None and 0 <= location_id < len(monitored_locations):
            location = monitored_locations[location_id]
        else:
            location = random.choice(monitored_locations)
        
        # Get current month to simulate seasonal variations
        current_month = datetime.datetime.now().month
        
        # Seasonal factors (Monsoon season in Uttar Pradesh is roughly June to September)
        is_monsoon = 6 <= current_month <= 9
        
        # Determine if this reading will be a high-risk scenario
        high_risk_scenario = random.random() < location["high_risk_chance"]
        
        # Base values adjusted by location factors
        if is_monsoon:
            # Monsoon season base values
            base_rainfall = 35.0 * location["rainfall_factor"]
            base_temperature = 28.0 * location["temp_factor"]
            base_soil_moisture = 50.0 * location["moisture_factor"]
            
            if high_risk_scenario:
                # High risk during monsoon - very heavy rain
                rainfall_variation = random.uniform(10.0, 30.0)
                soil_moisture_variation = random.uniform(10.0, 20.0)
            else:
                # Normal monsoon variation
                rainfall_variation = random.uniform(-5.0, 15.0)
                soil_moisture_variation = random.uniform(-5.0, 10.0)
        else:
            # Non-monsoon season base values
            base_rainfall = 8.0 * location["rainfall_factor"]
            base_temperature = 32.0 * location["temp_factor"]
            base_soil_moisture = 25.0 * location["moisture_factor"]
            
            if high_risk_scenario:
                # High risk outside monsoon - sudden unseasonal rain
                rainfall_variation = random.uniform(5.0, 20.0)
                soil_moisture_variation = random.uniform(5.0, 15.0)
            else:
                # Normal non-monsoon variation
                rainfall_variation = random.uniform(-5.0, 5.0)
                soil_moisture_variation = random.uniform(-5.0, 5.0)
        
        # Temperature variation (less affected by risk scenarios)
        temperature_variation = random.uniform(-3.0, 3.0)
        
        # Calculate final values with constraints
        rainfall = max(0, base_rainfall + rainfall_variation)
        temperature = base_temperature + temperature_variation
        soil_moisture = min(100, max(0, base_soil_moisture + soil_moisture_variation))
        
        # Add small random variation to the location coordinates
        lat_variation = random.uniform(-0.005, 0.005)
        lng_variation = random.uniform(-0.005, 0.005)
        
        # Construct data object
        data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "rainfall": round(rainfall, 2),  # mm
            "temperature": round(temperature, 2),  # Celsius
            "soil_moisture": round(soil_moisture, 2),  # percentage
            "location": {
                "lat": location["lat"] + lat_variation,
                "lng": location["lng"] + lng_variation
            }
        }
        
        return data
        
    except Exception as e:
        logger.error(f"Error simulating sensor data: {str(e)}")
        # Return fallback data if simulation fails
        return {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "rainfall": 10.0,
            "temperature": 25.0,
            "soil_moisture": 30.0,
            "location": {
                "lat": DEFAULT_LATITUDE,
                "lng": DEFAULT_LONGITUDE
            }
        }
