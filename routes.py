import os
import logging
import json
from datetime import datetime, timedelta
import tempfile
import numpy as np
from flask import render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

from app import db
from models import SensorData, LandslideEvent, RiskZone, EmergencyFacility, Alert, MonitoredLocation, RiskAssessment
from dl_model import landslide_model
from utils import (
    calculate_risk_score, calculate_enhanced_risk_score, generate_alert, 
    get_uttar_pradesh_risk_zones, get_emergency_facilities, 
    get_recent_sensor_data, get_active_alerts, init_sample_data,
    assess_multiple_locations, get_monitored_locations, 
    get_recent_risk_assessments, calculate_infrastructure_resilience,
    get_seismic_data, get_region_coordinates, find_closest_sensor_data
)
from sensor_data import get_raspberry_pi_data, simulate_sensor_data

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all routes with the Flask app"""
    
    # Initialize sample data at startup
    try:
        with app.app_context():
            init_sample_data()
    except Exception as e:
        logger.error(f"Error initializing sample data: {str(e)}")

    @app.route('/')
    def index():
        """Render the main dashboard page"""
        try:
            # Get recent sensor data
            sensor_data = get_recent_sensor_data(hours=24)
            
            # Get active alerts
            alerts = get_active_alerts()
            
            # Calculate current risk score if we have recent data
            current_risk = 0
            if sensor_data:
                latest = sensor_data[-1]
                current_risk = calculate_risk_score(
                    latest['rainfall'], 
                    latest['temperature'], 
                    latest['soil_moisture']
                )
            
            # Get risk assessments for different locations
            assessments = get_recent_risk_assessments(hours=24)
            
            # Render template with data
            return render_template(
                'index.html', 
                sensor_data=sensor_data,
                alerts=alerts,
                current_risk=current_risk,
                location_assessments=assessments
            )
            
        except Exception as e:
            logger.error(f"Error rendering index page: {str(e)}")
            return render_template('index.html', error=str(e))

    @app.route('/map')
    def map_view():
        """Render the map view page"""
        try:
            # Get risk zones
            risk_zones = get_uttar_pradesh_risk_zones()
            
            # Get emergency facilities by type
            all_facilities = get_emergency_facilities()
            hospitals = [f for f in all_facilities if f.get('facility_type') == 'hospital']
            rescue_centers = [f for f in all_facilities if f.get('facility_type') == 'rescue center']
            mitigation_centers = [f for f in all_facilities if f.get('facility_type') == 'mitigation center']
            
            # Get active alerts
            alerts = get_active_alerts()
            
            # Get monitored locations
            locations = get_monitored_locations()
            
            # Render template with data
            return render_template(
                'map.html', 
                risk_zones=risk_zones,
                facilities=all_facilities,
                hospitals=hospitals,
                rescue_centers=rescue_centers,
                mitigation_centers=mitigation_centers,
                alerts=alerts,
                locations=locations
            )
            
        except Exception as e:
            logger.error(f"Error rendering map page: {str(e)}")
            # Return error template without the problematic data
            return render_template('map.html', 
                                  risk_zones=[], 
                                  hospitals=[], 
                                  rescue_centers=[], 
                                  mitigation_centers=[], 
                                  alerts=[], 
                                  locations=[], 
                                  error=str(e))

    @app.route('/image-analysis')
    def image_analysis():
        """Render the image analysis page"""
        try:
            # Get historical landslide events
            events = LandslideEvent.query.order_by(LandslideEvent.timestamp.desc()).all()
            events_list = [event.to_dict() for event in events]
            
            # Render template with data
            return render_template('image_analysis.html', events=events_list)
            
        except Exception as e:
            logger.error(f"Error rendering image analysis page: {str(e)}")
            return render_template('image_analysis.html', error=str(e))

    @app.route('/alerts')
    def alerts():
        """Render the alerts page"""
        try:
            # Get all alerts (active and inactive)
            alerts_query = Alert.query.order_by(Alert.timestamp.desc()).all()
            alerts_list = [alert.to_dict() for alert in alerts_query]
            
            # Get risk zones for context
            risk_zones = get_uttar_pradesh_risk_zones()
            
            # Render template with data
            return render_template('alerts.html', alerts=alerts_list, risk_zones=risk_zones)
            
        except Exception as e:
            logger.error(f"Error rendering alerts page: {str(e)}")
            return render_template('alerts.html', error=str(e))

    @app.route('/api/sensor-data')
    def api_sensor_data():
        """API endpoint for recent sensor data"""
        try:
            # Get hours parameter (default to 24 if not provided)
            hours = request.args.get('hours', 24, type=int)
            
            # Get sensor data
            sensor_data = get_recent_sensor_data(hours=hours)
            
            return jsonify({
                'status': 'success',
                'data': sensor_data
            })
        except Exception as e:
            logger.error(f"Error in sensor data API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/risk-zones')
    def api_risk_zones():
        """API endpoint for landslide-prone areas"""
        try:
            # Get risk zones
            risk_zones = get_uttar_pradesh_risk_zones()
            
            return jsonify({
                'status': 'success',
                'data': risk_zones
            })
        except Exception as e:
            logger.error(f"Error in risk zones API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/emergency-facilities')
    def api_emergency_facilities():
        """API endpoint for emergency facilities"""
        try:
            # Get facility type filter
            facility_type = request.args.get('type')
            
            # Get emergency facilities
            facilities = get_emergency_facilities(facility_type=facility_type)
            
            return jsonify({
                'status': 'success',
                'data': facilities
            })
        except Exception as e:
            logger.error(f"Error in emergency facilities API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/alerts')
    def api_alerts():
        """API endpoint for active alerts"""
        try:
            # Get active alerts
            alerts = get_active_alerts()
            
            return jsonify({
                'status': 'success',
                'data': alerts
            })
        except Exception as e:
            logger.error(f"Error in alerts API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/risk-score')
    def api_risk_score():
        """API endpoint to calculate risk score"""
        try:
            # Get parameters from request
            rainfall = request.args.get('rainfall', type=float)
            temperature = request.args.get('temperature', type=float)
            soil_moisture = request.args.get('soil_moisture', type=float)
            
            if not all([rainfall is not None, temperature is not None, soil_moisture is not None]):
                return jsonify({
                    'status': 'error',
                    'message': 'Missing required parameters'
                }), 400
                
            # Calculate risk score
            risk_score = calculate_risk_score(rainfall, temperature, soil_moisture)
            
            return jsonify({
                'status': 'success',
                'risk_score': risk_score
            })
        except Exception as e:
            logger.error(f"Error in risk score API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/analyze-images', methods=['POST'])
    def api_analyze_images():
        """API endpoint to analyze before and after images"""
        try:
            # Check if both images were uploaded
            if 'before_image' not in request.files or 'after_image' not in request.files:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing image files'
                }), 400
                
            before_image = request.files['before_image']
            after_image = request.files['after_image']
            
            # Check if filenames are empty
            if before_image.filename == '' or after_image.filename == '':
                return jsonify({
                    'status': 'error',
                    'message': 'No selected files'
                }), 400
                
            # Create temp directory to store uploaded images
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save uploaded images
                before_path = os.path.join(temp_dir, secure_filename(before_image.filename))
                after_path = os.path.join(temp_dir, secure_filename(after_image.filename))
                
                before_image.save(before_path)
                after_image.save(after_path)
                
                # Analyze images
                results = landslide_model.analyze_images(before_path, after_path)
                
                return jsonify({
                    'status': 'success',
                    'data': results
                })
                
        except Exception as e:
            logger.error(f"Error in analyze images API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/update-sensor-data', methods=['POST'])
    def api_update_sensor_data():
        """API endpoint to update sensor data (from Raspberry Pi)"""
        try:
            # Check if request contains JSON data
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing JSON data in request'
                }), 400
                
            # Get data from request
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['rainfall', 'temperature', 'soil_moisture', 'location_lat', 'location_lng']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'status': 'error',
                        'message': f'Missing required field: {field}'
                    }), 400
            
            # Create sensor data record
            sensor_data = SensorData(
                rainfall=data['rainfall'],
                temperature=data['temperature'],
                soil_moisture=data['soil_moisture'],
                location_lat=data['location_lat'],
                location_lng=data['location_lng']
            )
            
            # Save to database
            db.session.add(sensor_data)
            db.session.commit()
            
            # Calculate risk score
            risk_score = calculate_risk_score(
                data['rainfall'],
                data['temperature'],
                data['soil_moisture']
            )
            
            # Generate alert if risk is high
            alert = None
            if risk_score >= 5.0:
                alert = generate_alert(risk_score, data['location_lat'], data['location_lng'])
                if alert:
                    db.session.add(alert)
                    db.session.commit()
            
            return jsonify({
                'status': 'success',
                'id': sensor_data.id,
                'risk_score': risk_score,
                'alert_generated': alert is not None
            })
            
        except Exception as e:
            logger.error(f"Error in update sensor data API: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/reset-demo-data', methods=['POST'])
    def api_reset_demo_data():
        """API endpoint to reset demo data"""
        try:
            # Initialize sample data
            init_sample_data()
            
            return jsonify({
                'status': 'success',
                'message': 'Demo data reset successfully'
            })
            
        except Exception as e:
            logger.error(f"Error in reset demo data API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/locations')
    def locations_view():
        """Render the monitored locations page"""
        try:
            # Get monitored locations
            locations = get_monitored_locations()
            
            # Render template with data
            return render_template('locations.html', locations=locations)
            
        except Exception as e:
            logger.error(f"Error rendering locations page: {str(e)}")
            return render_template('locations.html', error=str(e))

    @app.route('/api/locations')
    def api_locations():
        """API endpoint for monitored locations"""
        try:
            # Get monitored locations
            locations = get_monitored_locations()
            
            return jsonify({
                'status': 'success',
                'data': locations
            })
        except Exception as e:
            logger.error(f"Error in locations API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/risk-assessments')
    def api_risk_assessments():
        """API endpoint for risk assessments"""
        try:
            # Get hours parameter (default to 24 if not provided)
            hours = request.args.get('hours', 24, type=int)
            
            # Get risk assessments
            assessments = get_recent_risk_assessments(hours=hours)
            
            return jsonify({
                'status': 'success',
                'data': assessments
            })
        except Exception as e:
            logger.error(f"Error in risk assessments API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/assess-locations', methods=['POST'])
    def api_assess_locations():
        """API endpoint to assess all monitored locations"""
        try:
            # Assess all locations
            assessment_results = assess_multiple_locations()
            
            return jsonify({
                'status': 'success',
                'data': assessment_results
            })
        except Exception as e:
            logger.error(f"Error in assess locations API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/enhanced-risk-score')
    def api_enhanced_risk_score():
        """API endpoint to calculate enhanced risk score with detailed factors"""
        try:
            # Get parameters from request
            rainfall = request.args.get('rainfall', type=float)
            temperature = request.args.get('temperature', type=float)
            soil_moisture = request.args.get('soil_moisture', type=float)
            terrain_type = request.args.get('terrain_type')
            vegetation_density = request.args.get('vegetation_density', type=float)
            
            if not all([rainfall is not None, temperature is not None, soil_moisture is not None]):
                return jsonify({
                    'status': 'error',
                    'message': 'Missing required parameters'
                }), 400
                
            # Calculate enhanced risk score
            risk_data = calculate_enhanced_risk_score(
                rainfall=rainfall,
                temperature=temperature,
                soil_moisture=soil_moisture,
                terrain_type=terrain_type,
                vegetation_density=vegetation_density
            )
            
            return jsonify({
                'status': 'success',
                'data': risk_data
            })
        except Exception as e:
            logger.error(f"Error in enhanced risk score API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/infrastructure-resilience')
    def api_infrastructure_resilience():
        """API endpoint to calculate infrastructure resilience score"""
        try:
            # Get parameters from request
            location_name = request.args.get('location')
            risk_score = request.args.get('risk_score', type=float)
            
            if not location_name:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing location parameter'
                }), 400
                
            if not risk_score:
                # Try to get the latest risk score for this location
                locations = get_monitored_locations()
                matching_locations = [loc for loc in locations if location_name.lower() in loc['name'].lower()]
                
                if matching_locations:
                    loc = matching_locations[0]
                    # Get recent sensor data
                    sensor_data = get_recent_sensor_data(hours=3)
                    if sensor_data:
                        closest = find_closest_sensor_data(loc['location']['lat'], loc['location']['lng'], sensor_data)
                        if closest:
                            risk_score = calculate_risk_score(
                                closest['rainfall'],
                                closest['temperature'],
                                closest['soil_moisture']
                            )
                
                # If still no risk score, use a moderate default
                if not risk_score:
                    risk_score = 5.0
            
            # Calculate infrastructure resilience
            resilience_data = calculate_infrastructure_resilience(location_name, risk_score)
            
            return jsonify({
                'status': 'success',
                'data': resilience_data
            })
        except Exception as e:
            logger.error(f"Error in infrastructure resilience API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
            
    @app.route('/api/seismic-data')
    def api_seismic_data():
        """API endpoint for seismic data"""
        try:
            # Get parameters from request
            location = request.args.get('location')
            hours = request.args.get('hours', 24, type=int)
            
            # Get seismic data
            seismic_data = get_seismic_data(location_name=location, hours=hours)
            
            return jsonify({
                'status': 'success',
                'data': seismic_data
            })
        except Exception as e:
            logger.error(f"Error in seismic data API: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
            
    logger.debug("Routes registered successfully")