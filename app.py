import os
import logging

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, login_manager
from dotenv import load_dotenv, find_dotenv
from flask_wtf.csrf import CSRFProtect
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
 
# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
csrf = CSRFProtect(app)

# Configure PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models to ensure tables are created
with app.app_context():
    from models import User, Student, Course, Attendance, Fingerprint
    db.create_all()
    logger.info("Database tables created")

# Import and register routes
from routes import register_routes
register_routes(app)

# Import and register API routes
from api import register_api_routes
register_api_routes(app)

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
