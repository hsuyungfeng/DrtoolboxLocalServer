from flask import Flask
from flask_cors import CORS
import logging

logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Register Blueprints
    from src.api.routes.chat import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "ok", "service": "drtoolbox-local-server"}
        
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)