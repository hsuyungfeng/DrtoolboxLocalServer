import os
import sys

# Add the project root to the python path so absolute imports work when running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from flask import Flask, render_template
from flask_cors import CORS
import logging

logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    CORS(app)
    
    # Register Blueprints
    from src.api.routes.chat import chat_bp
    from src.api.routes.dashboard import dashboard_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    
    @app.route('/', methods=['GET'])
    def index():
        return render_template('dashboard.html')
    
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "ok", "service": "drtoolbox-local-server"}
        
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)