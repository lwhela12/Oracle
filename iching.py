import requests
import random

url = "https://qrandom.io/api/random/ints"

class IChing:
    def __init__(self):
        # 64 hexagrams with names and meanings
        self.hexagrams = {
            1: {'name': 'The Creative', 'symbol': '☰☰', 'meaning': 'Heaven', 'keywords': 'Strength, creativity, initiative'},
            2: {'name': 'The Receptive', 'symbol': '☷☷', 'meaning': 'Earth', 'keywords': 'Devotion, receptivity, yielding'},
            3: {'name': 'Difficulty at the Beginning', 'symbol': '☵☳', 'meaning': 'Birth pangs', 'keywords': 'Initial difficulty, perseverance'},
            4: {'name': 'Youthful Folly', 'symbol': '☶☵', 'meaning': 'Inexperience', 'keywords': 'Seeking guidance, learning'},
            5: {'name': 'Waiting', 'symbol': '☵☰', 'meaning': 'Nourishment', 'keywords': 'Patience, trust, timing'},
            6: {'name': 'Conflict', 'symbol': '☰☵', 'meaning': 'Tension', 'keywords': 'Dispute, caution, compromise'},
            7: {'name': 'The Army', 'symbol': '☷☵', 'meaning': 'Collective force', 'keywords': 'Discipline, organization'},
            8: {'name': 'Holding Together', 'symbol': '☵☷', 'meaning': 'Union', 'keywords': 'Alliance, cooperation'},
            9: {'name': 'Small Accumulating', 'symbol': '☴☰', 'meaning': 'Restraint', 'keywords': 'Gentle persistence'},
            10: {'name': 'Treading', 'symbol': '☰☱', 'meaning': 'Conduct', 'keywords': 'Careful behavior, respect'},
            11: {'name': 'Peace', 'symbol': '☷☰', 'meaning': 'Harmony', 'keywords': 'Balance, prosperity'},
            12: {'name': 'Standstill', 'symbol': '☰☷', 'meaning': 'Stagnation', 'keywords': 'Blocked, retreat'},
            13: {'name': 'Fellowship', 'symbol': '☰☲', 'meaning': 'Community', 'keywords': 'Companionship, unity'},
            14: {'name': 'Great Possessing', 'symbol': '☲☰', 'meaning': 'Abundance', 'keywords': 'Success, sovereignty'},
            15: {'name': 'Modesty', 'symbol': '☷☶', 'meaning': 'Humility', 'keywords': 'Balance, moderation'},
            16: {'name': 'Enthusiasm', 'symbol': '☳☷', 'meaning': 'Harmony', 'keywords': 'Joy, motivation'},
            17: {'name': 'Following', 'symbol': '☱☳', 'meaning': 'Adaptation', 'keywords': 'Flexibility, alignment'},
            18: {'name': 'Work on the Decayed', 'symbol': '☶☴', 'meaning': 'Repair', 'keywords': 'Correction, renewal'},
            19: {'name': 'Approach', 'symbol': '☷☱', 'meaning': 'Advance', 'keywords': 'Progress, opportunity'},
            20: {'name': 'Contemplation', 'symbol': '☴☷', 'meaning': 'View', 'keywords': 'Observation, reflection'},
            21: {'name': 'Biting Through', 'symbol': '☲☳', 'meaning': 'Decisiveness', 'keywords': 'Justice, determination'},
            22: {'name': 'Grace', 'symbol': '☶☲', 'meaning': 'Beauty', 'keywords': 'Elegance, form'},
            23: {'name': 'Splitting Apart', 'symbol': '☶☷', 'meaning': 'Deterioration', 'keywords': 'Decline, patience'},
            24: {'name': 'Return', 'symbol': '☷☳', 'meaning': 'Turning point', 'keywords': 'Revival, renewal'},
            25: {'name': 'Innocence', 'symbol': '☰☳', 'meaning': 'Unexpected', 'keywords': 'Spontaneity, naturalness'},
            26: {'name': 'Great Accumulating', 'symbol': '☶☰', 'meaning': 'Potential', 'keywords': 'Restraint, power'},
            27: {'name': 'Nourishment', 'symbol': '☶☳', 'meaning': 'Sustenance', 'keywords': 'Care, nurturing'},
            28: {'name': 'Great Preponderance', 'symbol': '☱☴', 'meaning': 'Excess', 'keywords': 'Pressure, extraordinary'},
            29: {'name': 'The Abysmal', 'symbol': '☵☵', 'meaning': 'Danger', 'keywords': 'Risk, courage'},
            30: {'name': 'The Clinging Fire', 'symbol': '☲☲', 'meaning': 'Clarity', 'keywords': 'Illumination, awareness'},
            31: {'name': 'Influence', 'symbol': '☱☶', 'meaning': 'Attraction', 'keywords': 'Courtship, receptivity'},
            32: {'name': 'Duration', 'symbol': '☳☴', 'meaning': 'Perseverance', 'keywords': 'Continuity, stability'},
            33: {'name': 'Retreat', 'symbol': '☰☶', 'meaning': 'Withdrawal', 'keywords': 'Strategic retreat'},
            34: {'name': 'Great Power', 'symbol': '☳☰', 'meaning': 'Vigor', 'keywords': 'Strength, action'},
            35: {'name': 'Progress', 'symbol': '☲☷', 'meaning': 'Advancement', 'keywords': 'Growth, clarity'},
            36: {'name': 'Darkening of the Light', 'symbol': '☷☲', 'meaning': 'Censorship', 'keywords': 'Adversity, inner light'},
            37: {'name': 'The Family', 'symbol': '☴☲', 'meaning': 'Clan', 'keywords': 'Relationships, foundation'},
            38: {'name': 'Opposition', 'symbol': '☲☱', 'meaning': 'Contradiction', 'keywords': 'Diversity, polarity'},
            39: {'name': 'Obstruction', 'symbol': '☵☶', 'meaning': 'Difficulty', 'keywords': 'Obstacle, turning inward'},
            40: {'name': 'Deliverance', 'symbol': '☳☵', 'meaning': 'Release', 'keywords': 'Liberation, relief'},
            41: {'name': 'Decrease', 'symbol': '☶☱', 'meaning': 'Simplicity', 'keywords': 'Sacrifice, reduction'},
            42: {'name': 'Increase', 'symbol': '☴☳', 'meaning': 'Growth', 'keywords': 'Expansion, blessing'},
            43: {'name': 'Breakthrough', 'symbol': '☱☰', 'meaning': 'Resolution', 'keywords': 'Decisiveness, clarity'},
            44: {'name': 'Coming to Meet', 'symbol': '☰☴', 'meaning': 'Encounter', 'keywords': 'Temptation, awareness'},
            45: {'name': 'Gathering Together', 'symbol': '☱☷', 'meaning': 'Assembly', 'keywords': 'Union, congregation'},
            46: {'name': 'Pushing Upward', 'symbol': '☷☴', 'meaning': 'Ascending', 'keywords': 'Progress, effort'},
            47: {'name': 'Oppression', 'symbol': '☱☵', 'meaning': 'Exhaustion', 'keywords': 'Adversity, endurance'},
            48: {'name': 'The Well', 'symbol': '☵☴', 'meaning': 'Source', 'keywords': 'Resources, nourishment'},
            49: {'name': 'Revolution', 'symbol': '☱☲', 'meaning': 'Change', 'keywords': 'Transformation, renewal'},
            50: {'name': 'The Cauldron', 'symbol': '☲☴', 'meaning': 'Transformation', 'keywords': 'Refinement, nourishment'},
            51: {'name': 'The Arousing', 'symbol': '☳☳', 'meaning': 'Thunder', 'keywords': 'Shock, awakening'},
            52: {'name': 'Keeping Still', 'symbol': '☶☶', 'meaning': 'Mountain', 'keywords': 'Stillness, meditation'},
            53: {'name': 'Development', 'symbol': '☴☶', 'meaning': 'Gradual progress', 'keywords': 'Step by step'},
            54: {'name': 'The Marrying Maiden', 'symbol': '☳☱', 'meaning': 'Relationships', 'keywords': 'Transition, propriety'},
            55: {'name': 'Abundance', 'symbol': '☳☲', 'meaning': 'Fullness', 'keywords': 'Peak, prosperity'},
            56: {'name': 'The Wanderer', 'symbol': '☲☶', 'meaning': 'Travel', 'keywords': 'Transition, adaptability'},
            57: {'name': 'The Gentle', 'symbol': '☴☴', 'meaning': 'Wind', 'keywords': 'Penetration, flexibility'},
            58: {'name': 'The Joyous', 'symbol': '☱☱', 'meaning': 'Lake', 'keywords': 'Joy, pleasure'},
            59: {'name': 'Dispersion', 'symbol': '☴☵', 'meaning': 'Dissolution', 'keywords': 'Separation, regrouping'},
            60: {'name': 'Limitation', 'symbol': '☵☱', 'meaning': 'Restriction', 'keywords': 'Boundaries, discipline'},
            61: {'name': 'Inner Truth', 'symbol': '☴☱', 'meaning': 'Sincerity', 'keywords': 'Understanding, insight'},
            62: {'name': 'Small Preponderance', 'symbol': '☳☶', 'meaning': 'Small exceeding', 'keywords': 'Details, humility'},
            63: {'name': 'After Completion', 'symbol': '☵☲', 'meaning': 'Order', 'keywords': 'Culmination, vigilance'},
            64: {'name': 'Before Completion', 'symbol': '☲☵', 'meaning': 'Transition', 'keywords': 'Potential, caution'}
        }

    def quantum_coin_toss(self):
        """Use quantum random numbers with timeout and cryptographic fallback for coin tosses."""
        params = {'n': 18, 'min': 0, 'max': 1}
        try:
            response = requests.get(url, params=params, timeout=2.5)
            if response.status_code == 200:
                tosses = response.json().get('numbers', [])
                if len(tosses) == 18:
                    return tosses
        except Exception:
            pass
        # Fallback to cryptographically strong system random
        rng = random.SystemRandom()
        return [rng.randint(0, 1) for _ in range(18)]

    def calculate_hexagram(self):
        """Calculate hexagram using coin toss method (3 coins, 6 times)."""
        tosses = self.quantum_coin_toss()
        lines = []

        # Process 3 tosses at a time to generate 6 lines (bottom to top)
        for i in range(0, 18, 3):
            three_tosses = tosses[i:i+3]
            heads = sum(three_tosses)

            # Traditional I Ching coin method:
            # 3 heads = old yang (9) - changing
            # 2 heads, 1 tail = young yang (7)
            # 1 head, 2 tails = young yin (8)
            # 3 tails = old yin (6) - changing
            if heads == 3:
                lines.append(9)  # Old yang
            elif heads == 2:
                lines.append(7)  # Young yang
            elif heads == 1:
                lines.append(8)  # Young yin
            else:
                lines.append(6)  # Old yin

        # Trigram mapping from 3 lines (bottom to top): 1 for yang (7, 9), 0 for yin (6, 8)
        trigram_map = {
            (1, 1, 1): '☰',  # Heaven / Qian
            (1, 1, 0): '☱',  # Lake / Dui
            (1, 0, 1): '☲',  # Fire / Li
            (1, 0, 0): '☳',  # Thunder / Zhen
            (0, 1, 1): '☴',  # Wind / Xun
            (0, 1, 0): '☵',  # Water / Kan
            (0, 0, 1): '☶',  # Mountain / Gen
            (0, 0, 0): '☷',  # Earth / Kun
        }

        # Lower trigram: lines 1-3 (indices 0, 1, 2)
        lower_tuple = tuple(1 if line in [7, 9] else 0 for line in lines[0:3])
        lower_symbol = trigram_map.get(lower_tuple, '☰')

        # Upper trigram: lines 4-6 (indices 3, 4, 5)
        upper_tuple = tuple(1 if line in [7, 9] else 0 for line in lines[3:6])
        upper_symbol = trigram_map.get(upper_tuple, '☰')

        combined_symbol = f"{upper_symbol}{lower_symbol}"

        # Find matching hexagram number from hexagrams dictionary
        hexagram_num = 1
        for num, data in self.hexagrams.items():
            if data['symbol'] == combined_symbol:
                hexagram_num = num
                break

        changing_lines = [i + 1 for i, line in enumerate(lines) if line in [6, 9]]

        return {
            'number': hexagram_num,
            'lines': lines,
            'changing_lines': changing_lines
        }

    def cast_hexagram(self):
        """Perform a complete I Ching reading."""
        result = self.calculate_hexagram()
        hexagram_data = self.hexagrams[result['number']]

        return {
            'number': result['number'],
            'name': hexagram_data['name'],
            'symbol': hexagram_data['symbol'],
            'meaning': hexagram_data['meaning'],
            'keywords': hexagram_data['keywords'],
            'changing_lines': result['changing_lines'],
            'lines': result['lines']
        }

    def get_hexagram_info(self, number):
        """Get information about a specific hexagram."""
        return self.hexagrams.get(number, {})
