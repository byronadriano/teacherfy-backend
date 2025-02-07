import os
from flask import Flask
from flask_cors import CORS

# Import necessary modules from config and blueprints
from src.config import logger
from src.auth_routes import auth_blueprint
from src.slides_routes import slides_blueprint
from src.presentation_routes import presentation_blueprint, load_example_outlines

# Create the Flask app
app = Flask(__name__)

# Configure CORS with the same settings as before
CORS(app, resources={r"/*": {
    "origins": [
        "https://teacherfy.ai",
        "http://localhost:3000",
        "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
    ],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    "supports_credentials": True,
    "expose_headers": ["Content-Type", "Authorization"],
    "max_age": 3600
}})

# Session configuration (same as before)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable is not set!")

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_HTTPONLY=True,
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    SESSION_COOKIE_DOMAIN=None
)

# Initialize example outlines on startup
@app.before_request
def init_example_outlines():
    if not hasattr(app, "has_run"):
        app.has_run = True
        logger.info("Initializing example outlines.")
        load_example_outlines()

# Register blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(slides_blueprint)
app.register_blueprint(presentation_blueprint)

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)