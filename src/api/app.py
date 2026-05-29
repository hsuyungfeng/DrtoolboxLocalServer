import os
import sys

# Add the project root to the python path so absolute imports work when running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from flask import Flask, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB limit
    app.config['MAX_FORM_MEMORY_SIZE'] = 2 * 1024 * 1024 * 1024 
    app.config['MAX_FORM_PARTS'] = 20000 
    # Use a longer timeout for requests
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    CORS(app)
    
    @app.after_request
    def add_cors_headers(response):
        response.headers.add('Access-Control-Allow-Private-Network', 'true')
        return response
    
    # Register Blueprints
    from src.api.routes.chat import chat_bp
    from src.api.routes.dashboard import dashboard_bp
    from src.api.routes.staff_actions import staff_actions_bp
    from src.api.routes.webhook import webhook_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(staff_actions_bp)
    app.register_blueprint(webhook_bp)
    
    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            return {
                "error": "Method Not Allowed on Root",
                "message": "Please use /webhook/line or /webhook/messenger for your messaging platforms.",
                "status": "error"
            }, 405
        return render_template('dashboard.html')
    
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "ok", "service": "drtoolbox-local-server"}
        
    @app.route('/privacy', methods=['GET'])
    def privacy_policy():
        return render_template('privacy.html')
        
    @app.route('/。')
    def typo_handler():
        # Redirect common Chinese typo to root
        from flask import redirect
        return redirect('/')
        
    @app.route('/favicon.ico')
    def favicon():
        return "", 204
        
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)