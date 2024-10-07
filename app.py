import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from oracle_logic import GeminiOracle

app = Flask(__name__, static_folder='static')
CORS(app)

oracle = GeminiOracle()  # Global instance

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/init', methods=['GET'])
def init():
    return jsonify({
        'response': f"Welcome! I'm {oracle.name}. I am here to provide whatever solutions you may need. What do you desire?",
        'terminate': False
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    
    if user_message.lower() in ['quit', 'exit', 'bye']:
        oracle.clear_history()
        return jsonify({'response': f"{oracle.name}: Blessings", 'terminate': True})
    
    response = oracle.respond(user_message)
    return jsonify({'response': response, 'terminate': False})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)





