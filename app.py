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
    spread_type = data.get('spread_type', '3-card')

    # Check for exit keywords
    if user_message.lower() in ['quit', 'exit', 'bye']:
        oracle.clear_history()
        return jsonify({'response': f"{oracle.name}: Blessings", 'terminate': True})

    # Check if the message contains the word "tarot" or similar
    elif 'tarot' in user_message.lower():
        # Customize response if tarot-related
        tarot_data = oracle.tarot_response_structured(user_message, spread_type)
        return jsonify({
            'response': tarot_data['text'],
            'cards': tarot_data['cards'],
            'positions': tarot_data['positions'],
            'spread_type': tarot_data['spread_type'],
            'type': 'tarot',
            'terminate': False
        })


    else:# General response
        response = oracle.respond(user_message)
        return jsonify({'response': response, 'terminate': False})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)





