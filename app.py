from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from utils.conversation import chatbot_response
from dotenv import load_dotenv
import os

load_dotenv()


app = Flask(__name__)
CORS(app) 


user_sessions = {}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Medical Symptom Analyzer API is running"})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat messages"""
    data = request.json
    
  
    session_id = data.get('sessionId')
    if not session_id or session_id not in user_sessions:
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            "user_id": f"user_{session_id[:8]}",
            "created_at": os.path.basename(__file__)
        }
    
   
    message = data.get('message', '')
    location = data.get('location', None)
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
 
    user_id = user_sessions[session_id]["user_id"]
    response = chatbot_response(user_id, message, location)
    
    return jsonify({
        "sessionId": session_id,
        "response": response["response"],
        "data": response["result"],
        "type": response["query_type"]
    })

@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new session"""
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = {
        "user_id": f"user_{session_id[:8]}",
        "created_at": os.path.basename(__file__)
    }
    
    return jsonify({
        "sessionId": session_id,
        "message": "New session created"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
