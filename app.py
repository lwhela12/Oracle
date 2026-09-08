import os
import re
import json
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from oracle_logic import GeminiOracle

app = Flask(__name__, static_folder='static')
CORS(app)

# Lazy initialization for serverless environments
_oracle = None

def format_api_error(err):
    """Sanitizes sensitive API keys and provides actionable diagnostic guidance."""
    err_str = str(err)
    err_str = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_KEY]', err_str)
    if 'CONSUMER_SUSPENDED' in err_str or 'has been suspended' in err_str:
        return (
            "Google Gemini API Key Suspended: The configured GEMINI_API_KEY was suspended/revoked by Google. "
            "Please generate a fresh key at https://aistudio.google.com/apikey and update GEMINI_API_KEY in your Vercel Project Settings."
        )
    elif 'API_KEY_INVALID' in err_str or 'API key not valid' in err_str:
        return (
            "Invalid Google Gemini API Key: Please check GEMINI_API_KEY in your Vercel Project Settings."
        )
    return err_str

def get_oracle():
    """Get or create the Oracle instance (lazy initialization)."""
    global _oracle
    if _oracle is None:
        _oracle = GeminiOracle()
    return _oracle


def determine_mode(message, explicit_mode=None):
    """Determines divination mode from explicit param or intelligent keyword parsing."""
    if explicit_mode and explicit_mode in ['tarot', 'iching', 'runes', 'number', 'oracle']:
        return explicit_mode

    msg = (message or '').lower().strip()
    if any(k in msg for k in ['tarot', 'card', 'cards', 'spread', 'celtic']):
        return 'tarot'
    elif any(k in msg for k in ['i ching', 'iching', 'hexagram', 'changing lines', 'book of changes']):
        return 'iching'
    elif any(k in msg for k in ['rune', 'runes', 'futhark', 'norse']):
        return 'runes'
    elif any(k in msg for k in ['number', 'numerology', 'quantum number']):
        return 'number'
    return 'oracle'


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/init', methods=['GET', 'POST'])
def init():
    try:
        oracle = get_oracle()
        return jsonify({
            'response': f"Welcome, seeker. I am {oracle.name}. What mysteries do you wish to unravel?",
            'terminate': False
        })
    except ValueError as e:
        return jsonify({
            'response': f"Configuration Error: {str(e)}",
            'terminate': True,
            'error': True
        }), 500
    except Exception as e:
        return jsonify({
            'response': f"Initialization error: {str(e)}",
            'terminate': True,
            'error': True
        }), 500


@app.route('/session/clear', methods=['POST'])
def session_clear():
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id', 'default')
    try:
        oracle = get_oracle()
        oracle.clear_history(session_id)
        return jsonify({'status': 'cleared', 'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')
    spread_type = data.get('spread_type', '3-card')
    explicit_mode = data.get('mode')

    # Exit keywords
    if user_message.lower() in ['quit', 'exit', 'bye']:
        oracle.clear_history(session_id)
        return jsonify({'response': f"{oracle.name}: Blessings on your path.", 'terminate': True})

    allow_reversals = data.get('allow_reversals', True)
    include_wyrd = data.get('include_wyrd', False)

    mode = determine_mode(user_message, explicit_mode)

    try:
        if mode == 'tarot':
            tarot_data = oracle.tarot_response_structured(user_message, spread_type or '3-card', session_id=session_id)
            return jsonify({
                'response': tarot_data['text'],
                'cards': tarot_data['cards'],
                'positions': tarot_data['positions'],
                'spread_type': tarot_data['spread_type'],
                'type': 'tarot',
                'terminate': False
            })

        elif mode == 'iching':
            iching_data = oracle.iching_response(user_message, session_id=session_id)
            return jsonify({
                'response': iching_data['text'],
                'hexagram': iching_data['hexagram'],
                'type': 'iching',
                'terminate': False
            })

        elif mode == 'runes':
            rune_spread = spread_type if spread_type else 'norns'
            runes_data = oracle.runes_response(
                user_message,
                spread_type=rune_spread,
                allow_reversals=allow_reversals,
                include_wyrd=include_wyrd,
                session_id=session_id
            )
            return jsonify({
                'response': runes_data['text'],
                'runes': runes_data['runes'],
                'positions': runes_data['positions'],
                'spread_type': runes_data['spread_type'],
                'spread_name': runes_data['spread_name'],
                'type': 'runes',
                'terminate': False
            })

        else:
            response = oracle.respond(user_message, session_id=session_id)
            return jsonify({'response': response, 'type': 'oracle', 'terminate': False})

    except Exception as e:
        clean_err = format_api_error(e)
        return jsonify({
            'response': f"The mists cloud the vision: {clean_err}",
            'terminate': False,
            'error': True
        }), 500


@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    try:
        oracle = get_oracle()
    except ValueError as e:
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')

    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')
    spread_type = data.get('spread_type')
    explicit_mode = data.get('mode')
    allow_reversals = data.get('allow_reversals', True)
    include_wyrd = data.get('include_wyrd', False)

    # Exit check
    if user_message.lower() in ['quit', 'exit', 'bye']:
        oracle.clear_history(session_id)
        def exit_gen():
            yield f"event: metadata\ndata: {json.dumps({'type': 'oracle', 'terminate': True})}\n\n"
            yield f"event: token\ndata: {json.dumps({'token': f'{oracle.name}: Blessings on your path.'})}\n\n"
            yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"
        return Response(exit_gen(), mimetype='text/event-stream')

    mode = determine_mode(user_message, explicit_mode)

    # Prepare reading symbols & prompt
    if mode == 'tarot':
        prep = oracle.prepare_tarot_reading(user_message, spread_type or '3-card')
        metadata = {
            'type': 'tarot',
            'cards': prep['cards'],
            'positions': prep['positions'],
            'spread_type': prep['spread_type']
        }
        prompt = prep['prompt']
    elif mode == 'iching':
        prep = oracle.prepare_iching_reading(user_input=user_message)
        metadata = {
            'type': 'iching',
            'hexagram': prep['hexagram']
        }
        prompt = prep['prompt']
    elif mode == 'runes':
        rune_spread = spread_type if spread_type else 'norns'
        prep = oracle.prepare_runes_reading(
            user_message,
            spread_type=rune_spread,
            allow_reversals=allow_reversals,
            include_wyrd=include_wyrd
        )
        metadata = {
            'type': 'runes',
            'runes': prep['runes'],
            'positions': prep['positions'],
            'spread_type': prep['spread_type'],
            'spread_name': prep['spread_name']
        }
        prompt = prep['prompt']
    else:
        prep = oracle.prepare_number_reading(user_message)
        metadata = {
            'type': 'oracle',
            'quantum_number': prep['quantum_number']
        }
        prompt = prep['prompt']

    def generate():
        try:
            # 1. Send metadata first so UI immediately updates visuals (cards/hexagram/runes)
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

            # 2. Stream tokens as they are produced by Gemini 3.8 Flash
            for token in oracle.stream_chat(prompt, session_id=session_id):
                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

            # 3. Done signal
            yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"
        except Exception as err:
            clean_err = format_api_error(err)
            yield f"event: error\ndata: {json.dumps({'error': clean_err})}\n\n"

    # No explicit Connection header: it is invalid on HTTP/2 and kept Vercel from closing the response after the done event.
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)





