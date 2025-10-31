import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "landslide_prediction_default_key")

# Configure the database - Force SQLite for stability
database_url = None  # Force SQLite usage

# Make sure instance directory exists for SQLite
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
database_url = "sqlite:///" + os.path.join(instance_path, "landslide.db")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Log database connection
logger.info(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[0].split('://')[0]}")

# Initialize the app with the extension
db.init_app(app)

# Import routes after app is created to avoid circular imports
with app.app_context():
    # Create database tables
    import models
    db.create_all()
    
    # Import and register routes
    from routes import register_routes
    register_routes(app)

logger.debug("Application initialized")
