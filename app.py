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
        'response': f"Welcome! I'm {oracle.name}. What do you seek?",
        'terminate': False
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    
    # Check for exit keywords
    if user_message.lower() in ['quit', 'exit', 'bye']:
        oracle.clear_history()
        return jsonify({'response': f"{oracle.name}: Blessings", 'terminate': True})
    
    # Check if the message contains the word "tarot" or similar
    if 'tarot' in user_message.lower():
        # Customize response if tarot-related
        tarot_response = oracle.tarot_response(user_message)  # Assuming you have a separate tarot response method
        return jsonify({'response': tarot_response, 'terminate': False})

    else:# General response
        response = oracle.respond(user_message)
        eturn jsonify({'response': response, 'terminate': False})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)





