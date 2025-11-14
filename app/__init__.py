from flask import Flask
from flask_cors import CORS
from .extensions import db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    # Blueprint 등록
    from .routes.health_routes import health_bp
    #from .routes.defect_routes import defect_bp
    #from .routes.schedule_routes import schedule_bp

    app.register_blueprint(health_bp)
    #app.register_blueprint(defect_bp, url_prefix="/api/defects")
    #app.register_blueprint(schedule_bp, url_prefix="/api/schedule")

    return app
