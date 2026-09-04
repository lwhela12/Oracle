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

Crucial Presentation Guidelines:
- The seeker is ALREADY viewing the physical cards, hexagrams, or runic stones beautifully arranged in their sacred geometric pattern on their visual altar.
- NEVER print a mechanical list, itemized inventory, bulleted recap, or raw text summary of the drawn symbols at the beginning or anywhere in your response. Doing so clutters the divination.
- Begin IMMEDIATELY with an evocative address to the seeker and dive straight into the poetic narrative divination.
- Weave the drawn symbols and their positions organically into your prose, using elegant headers (e.g. `### ✦ The Well of Urðr: Roots of Becoming` or `### ✦ Asgard: The Divine Calling`) and bold highlights rather than a raw text listing of the cast.
- Use clear markdown formatting (bolding, italics, section headers, bullet points for key takeaways) so the reading is beautiful, poetic, and empowering.
- For synthesis, summaries, or verdicts, avoid raw markdown tables as narrative prose gets cramped in narrow grid columns; instead, present card-by-card takeaways and overarching syntheses using elegant headings, bullet points (such as ✦), bold titles, and flowing prose.
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
            prompt = f"The seeker drew the card: {spread[0]}. Using this card, provide a clear Yes or No answer to: '{user_input}'. Explain your reasoning based on the card's symbolism. DO NOT output a mechanical recap or bulleted inventory of the card at the beginning; dive directly into your answer."
        elif spread_type == 'celtic':
            drawn_str = ', '.join([f"{pos}: {card}" for pos, card in zip(positions, spread)])
            prompt = f"The seeker has drawn an authentic Celtic Cross spread: {drawn_str}. Provide a comprehensive divination answering their question: '{user_input}'. CRITICAL: DO NOT output an inventory list, bulleted recap, or text enumeration of the cards at the beginning of your reading, as the seeker already sees all cards visually arranged in the Celtic Cross pattern on their screen. Dive immediately into your poetic, insightful narrative interpretation."
        else:
            drawn_str = ', '.join([f"{pos}: {card}" for pos, card in zip(positions, spread)])
            prompt = f"The seeker has drawn the cards: {drawn_str}. Provide a profound reading answering their request: '{user_input}'. CRITICAL: DO NOT output an inventory list, bulleted recap, or text enumeration of the cards at the beginning of your reading, as the seeker already sees the cards visually displayed above. Dive immediately into your poetic, insightful narrative interpretation."

        return {
            'cards': card_data,
            'positions': positions,
            'spread_type': spread_type,
            'prompt': prompt
        }

    def prepare_iching_reading(self, user_input):
        """Casts hexagram and builds the prompt without calling Gemini yet."""
        hexagram = self.iching.cast_hexagram()
        primary_name = f"Hexagram {hexagram['number']}: {hexagram['name']} {hexagram.get('chinese', '')}"
        upper = hexagram.get('upper_trigram', {})
        lower = hexagram.get('lower_trigram', {})
        trigram_desc = f"{upper.get('name', 'Upper')} ({upper.get('element', '')}) above {lower.get('name', 'Lower')} ({lower.get('element', '')})"
        
        transformed = hexagram.get('transformed')
        if transformed:
            trans_upper = transformed.get('upper_trigram', {})
            trans_lower = transformed.get('lower_trigram', {})
            trans_trigram_desc = f"{trans_upper.get('name', 'Upper')} ({trans_upper.get('element', '')}) above {trans_lower.get('name', 'Lower')} ({trans_lower.get('element', '')})"
            changing_lines_str = ', '.join(map(str, hexagram['changing_lines']))
            
            prompt = f"""You have cast the ancient I Ching (Book of Changes) using the traditional three-coin oracle method and received:

1. PRIMARY HEXAGRAM (Present Situation):
   - {primary_name} ({hexagram['symbol']})
   - Trigram Architecture: {trigram_desc}
   - Meaning: {hexagram['meaning']}
   - Core Essence: {hexagram['keywords']}

2. MOVING / CHANGING LINES (Active Forces in Motion):
   - Active Line(s): {changing_lines_str} (counting from bottom Line 1 to top Line 6)
   - These dynamic lines represent the specific tensions, critical choices, and emerging shifts in the seeker's circumstance.

3. TRANSFORMED HEXAGRAM (Zhi Gua — Emerging Trajectory / Future Outcome):
   - Hexagram {transformed['number']}: {transformed['name']} {transformed.get('chinese', '')} ({transformed['symbol']})
   - Trigram Architecture: {trans_trigram_desc}
   - Meaning: {transformed['meaning']}
   - Core Essence: {transformed['keywords']}

Seeker's Inquiry: '{user_input}'

Provide a profound classical I Ching divination. In your counsel:
- Open with the poetic archetypal wisdom of the Primary Hexagram (The Judgment & The Image).
- Elucidate the specific counsel and warnings of the Moving Line(s).
- Reveal the destination and trajectory shown by the Transformed Hexagram.
- Offer actionable philosophical guidance for walking this path in harmony with the Tao."""
        else:
            prompt = f"""You have cast the ancient I Ching (Book of Changes) using the traditional three-coin oracle method and received a steadfast, unchanging hexagram:

PRIMARY HEXAGRAM (Enduring Reality):
- {primary_name} ({hexagram['symbol']})
- Trigram Architecture: {trigram_desc}
- Meaning: {hexagram['meaning']}
- Core Essence: {hexagram['keywords']}
- Stability: No changing lines are present, signifying an immutable, steady-state condition where the primary archetype must be deeply integrated rather than rushed.

Seeker's Inquiry: '{user_input}'

Provide a profound classical I Ching divination. Explain the Judgment and the Image of this hexagram, revealing how its elemental energies guide the seeker's inquiry in alignment with the Tao."""

        return {
            'hexagram': hexagram,
            'prompt': prompt
        }

    def prepare_runes_reading(self, user_input, spread_type='norns', allow_reversals=True, include_wyrd=False, **kwargs):
        """Casts runes and builds a rich Norse ceremonial divination prompt."""
        # Handle legacy or positional num_runes argument
        if isinstance(spread_type, int):
            spread_type = 'single' if spread_type == 1 else 'norns'
        elif 'num_runes' in kwargs:
            num = kwargs['num_runes']
            spread_type = 'single' if num == 1 else 'norns'

        cast = self.runes.cast_spread(
            spread_type=spread_type,
            allow_reversals=allow_reversals,
            include_wyrd=include_wyrd
        )
        rune_spread = cast['runes']
        positions = cast['positions']
        spread_name = cast['spread_name']
        spread_key = cast['spread_key']

        rune_lines = []
        for i, rune in enumerate(rune_spread):
            pos_label = positions[i] if i < len(positions) else f"Rune {i+1}"
            rev_label = f"[{rune['orientation']}]" if rune.get('is_reversed') else "[Upright]"
            meaning = rune.get('active_meaning', rune['meaning'])
            keywords = rune.get('active_keywords', rune['keywords'])
            aett_info = f"({rune.get('aett', '')})" if rune.get('aett') else ""
            rune_lines.append(
                f"- {pos_label}: {rune['symbol']} {rune['name']} {rev_label} {aett_info}\n"
                f"  Meaning: {meaning}\n"
                f"  Keywords: {keywords}"
            )

        rune_text = "\n\n".join(rune_lines)

        # Specialized thematic instructions per spread
        if spread_key == 'norns':
            spread_context = (
                "You are interpreting the threads of the Three Norns at the sacred Well of Urðr:\n"
                "1. Urðr: The ancestral root, past deeds, and karmic origins.\n"
                "2. Verðandi: The living present, active momentum, and emerging truth.\n"
                "3. Skuld: The future necessity, debt of actions, and potential culmination."
            )
        elif spread_key == 'nine-worlds':
            spread_context = (
                "You are casting across the Nine Worlds of Yggdrasil, the Cosmic Tree:\n"
                "- Upper Realms: Asgard (Divine Will/Spiritual Calling), Alfheim (Light/Intellect), Vanaheim (Heart/Fertility/Love).\n"
                "- Midgard & The Horizon: Midgard (Mundane Reality/The Seeker), Jotunheim (Shadow Forces/Chaos), Svartalfheim (Subconscious Power/Hidden Craft).\n"
                "- Lower Roots & Primal Elements: Muspelheim (Primal Fire/Drive), Niflheim (Primal Ice/Karmic Stagnation), Helheim (Underworld/Ancestral Rebirth)."
            )
        elif spread_key == 'thor-hammer':
            spread_context = (
                "You are invoking the Hammer of Thor (Mjölnir) for breakthrough, courage, and clearing obstacles:\n"
                "- The Striking Point: The central conflict, deadlock, or test of resolve.\n"
                "- The Wings: Left Wing (Inner doubt/vulnerability) vs Right Wing (Outer opposition).\n"
                "- The Shaft & Grip: The divine wellspring of strength and the decisive action needed to strike through."
            )
        elif spread_key == 'five-cross':
            spread_context = (
                "You are laying the Five-Rune Wyrd Cross upon the sacred white linen:\n"
                "- Center: The core essence of the seeker and situation.\n"
                "- West & East: The fading past vs the emerging horizon.\n"
                "- North & South: The higher spiritual lesson/aid vs the ultimate resulting wyrd."
            )
        else:
            spread_context = "You are drawing Odin's Rune: an unvarnished, direct omen of wisdom from the All-Father."

        prompt = f"""You have performed an authentic Elder Futhark rune casting: {spread_name}.
{spread_context}

Drawn Sacred Runes:
{rune_text}

Seeker's Inquiry: '{user_input}'

Divination Guidelines:
- CRITICAL: DO NOT output an inventory list, bulleted recap, or text enumeration of the drawn runes at the beginning of your reading. The seeker already sees the physical stones cast in their exact geometric layout on the altar cloth above.
- Begin immediately with your evocative, poetic address and flow directly into the narrative divination, addressing the realms/positions organically in your prose.
- If any runes are marked [Merkstave (Reversed)], do NOT interpret them as generic evil omens; interpret them with psychological and spiritual depth as blocked energy, internal friction, warnings of excess, or shadow aspects that require conscious awareness.
- Symmetrical runes (such as Gebo, Isa, Hagalaz, Jera, Sowilo, Dagaz) always remain upright and represent unalterable cosmic principles.
- Offer actionable, courageous counsel fitting for someone walking their path with honor."""

        return {
            'runes': rune_spread,
            'positions': positions,
            'spread_type': spread_key,
            'spread_name': spread_name,
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

    def runes_response(self, user_input, spread_type='norns', allow_reversals=True, include_wyrd=False, session_id="default", **kwargs):
        prep = self.prepare_runes_reading(
            user_input,
            spread_type=spread_type,
            allow_reversals=allow_reversals,
            include_wyrd=include_wyrd,
            **kwargs
        )
        text = self.send_chat(prep['prompt'], session_id)
        return {
            'text': text,
            'runes': prep['runes'],
            'positions': prep['positions'],
            'spread_type': prep['spread_type'],
            'spread_name': prep['spread_name'],
            'type': 'runes'
        }

    def respond(self, user_input, session_id="default"):
        prep = self.prepare_number_reading(user_input)
        return self.send_chat(prep['prompt'], session_id)