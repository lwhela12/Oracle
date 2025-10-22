import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from oracle_logic import GeminiOracle

app = Flask(__name__, static_folder='static')
CORS(app)

# Lazy initialization for serverless environments
_oracle = None

def get_oracle():
    """Get or create the Oracle instance (lazy initialization)."""
    global _oracle
    if _oracle is None:
        _oracle = GeminiOracle()
    return _oracle

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/init', methods=['GET'])
def init():
    try:
        oracle = get_oracle()
        return jsonify({
            'response': f"Welcome! I'm {oracle.name}. What do you seek?",
            'terminate': False
        })
    except ValueError as e:
        return jsonify({
            'response': f"Configuration Error: {str(e)}",
            'terminate': True,
            'error': True
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        oracle = get_oracle()
    except ValueError as e:
        return jsonify({
            'response': f"Configuration Error: {str(e)}",
            'terminate': True,
            'error': True
        }), 500

    data = request.json
    user_message = data['message']
    spread_type = data.get('spread_type', '3-card')

    # Check for exit keywords
    if user_message.lower() in ['quit', 'exit', 'bye']:
        oracle.clear_history()
        return jsonify({'response': f"{oracle.name}: Blessings", 'terminate': True})

    # Check if the message contains the word "tarot" or similar
    elif 'tarot' in user_message.lower():
        # Tarot reading
        tarot_data = oracle.tarot_response_structured(user_message, spread_type)
        return jsonify({
            'response': tarot_data['text'],
            'cards': tarot_data['cards'],
            'positions': tarot_data['positions'],
            'spread_type': tarot_data['spread_type'],
            'type': 'tarot',
            'terminate': False
        })

    # Check for I Ching
    elif any(word in user_message.lower() for word in ['i ching', 'iching', 'hexagram', 'changing lines']):
        # I Ching reading
        iching_data = oracle.iching_response(user_message)
        return jsonify({
            'response': iching_data['text'],
            'hexagram': iching_data['hexagram'],
            'type': 'iching',
            'terminate': False
        })

    # Check for Runes
    elif any(word in user_message.lower() for word in ['rune', 'runes', 'futhark', 'norse']):
        # Rune reading
        runes_data = oracle.runes_response(user_message)
        return jsonify({
            'response': runes_data['text'],
            'runes': runes_data['runes'],
            'positions': runes_data['positions'],
            'type': 'runes',
            'terminate': False
        })

    else:# General response
        response = oracle.respond(user_message)
        return jsonify({'response': response, 'terminate': False})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)





