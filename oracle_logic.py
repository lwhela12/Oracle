import os
import time
import random
import threading
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tarot import TarotDeck
from iching import IChing
from runes import RuneCast

load_dotenv()

SYSTEM_INSTRUCTION = """You are The Oracle, a mystical, poetic, and profound soothsayer.
You are an expert on tarot cards, I Ching hexagrams, Elder Futhark runes, and mystical numerology.

For tarot readings, interpret the cards in their spread positions (past, present, future, challenge, outcome, etc.) with deep psychological and spiritual insight.
For I Ching, interpret the hexagrams and changing lines with wisdom from the ancient Book of Changes.
For rune castings, interpret the Elder Futhark symbols with knowledge of Norse tradition and fate (wyrd).
For quantum number readings, interpret the provided quantum number through numerological, astrological, and cosmic symbolism.

Formatting Guidelines:
- Begin by addressing the seeker and acknowledging their drawn symbols (cards, hexagram, runes, or quantum number).
- Weave your divination like a wise, ancient oracle: poetic, mysterious, evocative, yet empowering and grounded in practical wisdom.
- Use clear markdown formatting (bolding, italics, section headers, bullet points) so the reading is beautiful and easy to read.
"""


class SessionManager:
    """Manages separate conversation sessions with automatic TTL pruning."""
    def __init__(self, ttl_seconds=7200):  # 2 hours
        self.sessions = {}
        self.ttl = ttl_seconds
        self.lock = threading.Lock()

    def get_chat(self, session_id, client, model_name, config):
        now = time.time()
        with self.lock:
            # Clean up expired sessions
            expired = [sid for sid, data in self.sessions.items() if now - data['last_active'] > self.ttl]
            for sid in expired:
                del self.sessions[sid]

            if session_id not in self.sessions:
                chat = client.chats.create(model=model_name, config=config)
                self.sessions[session_id] = {'chat': chat, 'last_active': now}
            else:
                self.sessions[session_id]['last_active'] = now
            return self.sessions[session_id]['chat']

    def clear_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]


class GeminiOracle:
    def __init__(self):
        self.name = "The Oracle"
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it in your environment or .env file. "
                "Get your API key from: https://aistudio.google.com/apikey"
            )

        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
        self.client = genai.Client(api_key=self.api_key)
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.85
        )

        self.session_manager = SessionManager()
        self.deck = TarotDeck()
        self.iching = IChing()
        self.runes = RuneCast()

    def get_chat(self, session_id="default"):
        return self.session_manager.get_chat(
            session_id=session_id,
            client=self.client,
            model_name=self.model_name,
            config=self.config
        )

    def clear_history(self, session_id="default"):
        """Clears chat history for the given session."""
        self.session_manager.clear_session(session_id)

    def _get_quantum_number(self):
        """Fetch a quantum random integer with timeout and cryptosecure fallback."""
        url = "https://qrandom.io/api/random/int"
        try:
            resp = requests.get(url, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                if 'number' in data:
                    return data['number']
        except Exception:
            pass
        return random.SystemRandom().randint(1, 999)

    def prepare_tarot_reading(self, user_input, spread_type='3-card'):
        """Draws cards and builds the prompt without calling Gemini yet."""
        num_cards = {
            '3-card': 3,
            'yes-no': 1,
            '5-card': 5,
            'celtic': 10
        }.get(spread_type, 3)

        spread = self.deck.reading(num_cards)
        card_data = [self.deck.get_card_info(card) for card in spread]
        positions = self.deck.get_spread_positions(spread_type)

        if spread_type == 'yes-no':
            prompt = f"The seeker drew the card: {spread[0]}. Using this card, provide a clear Yes or No answer to: '{user_input}'. Explain your reasoning based on the card's symbolism."
        elif spread_type == 'celtic':
            drawn_str = ', '.join([f"{pos}: {card}" for pos, card in zip(positions, spread)])
            prompt = f"The seeker has drawn a Celtic Cross spread: {drawn_str}. Provide a comprehensive divination answering their question: '{user_input}'."
        else:
            drawn_str = ', '.join([f"{pos}: {card}" for pos, card in zip(positions, spread)])
            prompt = f"The seeker has drawn the cards: {drawn_str}. Provide a profound reading answering their request: '{user_input}'."

        return {
            'cards': card_data,
            'positions': positions,
            'spread_type': spread_type,
            'prompt': prompt
        }

    def prepare_iching_reading(self, user_input):
        """Casts hexagram and builds the prompt without calling Gemini yet."""
        hexagram = self.iching.cast_hexagram()
        changing_desc = f"Changing lines: {', '.join(map(str, hexagram['changing_lines']))}" if hexagram['changing_lines'] else "No changing lines"

        prompt = f"""You have cast the I Ching and received:
Hexagram {hexagram['number']}: {hexagram['name']} ({hexagram['symbol']})
Meaning: {hexagram['meaning']}
Keywords: {hexagram['keywords']}
{changing_desc}

Provide an I Ching divination for this seeker's question: '{user_input}'"""

        return {
            'hexagram': hexagram,
            'prompt': prompt
        }

    def prepare_runes_reading(self, user_input, num_runes=3):
        """Casts runes and builds the prompt without calling Gemini yet."""
        rune_spread = self.runes.cast_runes(num_runes)
        positions = ['Situation', 'Action', 'Outcome'] if num_runes == 3 else ['Rune'] * num_runes

        rune_text = '\n'.join([
            f"- {positions[i]}: {rune['symbol']} {rune['name']} — {rune['meaning']} ({rune['keywords']})"
            for i, rune in enumerate(rune_spread)
        ])

        prompt = f"""You have cast the Elder Futhark runes and drawn:
{rune_text}

Provide an evocative Norse rune reading for this seeker's inquiry: '{user_input}'"""

        return {
            'runes': rune_spread,
            'positions': positions,
            'prompt': prompt
        }

    def prepare_number_reading(self, user_input):
        """Fetches quantum number and builds the prompt."""
        random_number = self._get_quantum_number()
        prompt = f"The cosmos presents this quantum number: {random_number}. Interpret this omen and answer the seeker's inquiry: '{user_input}'"
        return {
            'quantum_number': random_number,
            'prompt': prompt
        }

    def stream_chat(self, prompt, session_id="default"):
        """Streams response tokens from Gemini 3.8 Flash."""
        chat = self.get_chat(session_id)
        response_stream = chat.send_message_stream(prompt)
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    def send_chat(self, prompt, session_id="default"):
        """Sends a message and returns the complete text response."""
        chat = self.get_chat(session_id)
        response = chat.send_message(prompt)
        return response.text

    # Backwards-compatible synchronous response methods
    def tarot_response_structured(self, user_input, spread_type='3-card', session_id="default"):
        prep = self.prepare_tarot_reading(user_input, spread_type)
        text = self.send_chat(prep['prompt'], session_id)
        return {
            'text': text,
            'cards': prep['cards'],
            'positions': prep['positions'],
            'spread_type': prep['spread_type']
        }

    def iching_response(self, user_input, session_id="default"):
        prep = self.prepare_iching_reading(user_input)
        text = self.send_chat(prep['prompt'], session_id)
        return {
            'text': text,
            'hexagram': prep['hexagram'],
            'type': 'iching'
        }

    def runes_response(self, user_input, num_runes=3, session_id="default"):
        prep = self.prepare_runes_reading(user_input, num_runes)
        text = self.send_chat(prep['prompt'], session_id)
        return {
            'text': text,
            'runes': prep['runes'],
            'positions': prep['positions'],
            'type': 'runes'
        }

    def respond(self, user_input, session_id="default"):
        prep = self.prepare_number_reading(user_input)
        return self.send_chat(prep['prompt'], session_id)