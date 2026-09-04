import requests
import random

url = "https://qrandom.io/api/random/ints"

TRIGRAMS = {
    '☰': {'symbol': '☰', 'name': 'Heaven', 'chinese': '乾 (Qián)', 'element': 'Creative Sky / Celestial Yang', 'nature': 'Strong, Initiating'},
    '☱': {'symbol': '☱', 'name': 'Lake', 'chinese': '兌 (Duì)', 'element': 'Open Waters / Joyful Mist', 'nature': 'Joyous, Expressive'},
    '☲': {'symbol': '☲', 'name': 'Fire', 'chinese': '離 (Lí)', 'element': 'Radiant Sun / Flame', 'nature': 'Clinging, Illuminating'},
    '☳': {'symbol': '☳', 'name': 'Thunder', 'chinese': '震 (Zhèn)', 'element': 'Awakening Shock / Lightning', 'nature': 'Arousing, Dynamic Movement'},
    '☴': {'symbol': '☴', 'name': 'Wind', 'chinese': '巽 (Xùn)', 'element': 'Gentle Breeze / Tree Roots', 'nature': 'Penetrating, Flexible'},
    '☵': {'symbol': '☵', 'name': 'Water', 'chinese': '坎 (Kǎn)', 'element': 'Abyssal Chasm / River Current', 'nature': 'Dangerous, Flowing Depth'},
    '☶': {'symbol': '☶', 'name': 'Mountain', 'chinese': '艮 (Gèn)', 'element': 'Immovable Peak / Sacred Stone', 'nature': 'Still, Grounded Restraint'},
    '☷': {'symbol': '☷', 'name': 'Earth', 'chinese': '坤 (Kūn)', 'element': 'Nurturing Soil / Primordial Yin', 'nature': 'Receptive, Devoted Matrix'},
}

class IChing:
    def __init__(self):
        # 64 hexagrams with names and meanings
        self.hexagrams = {
            1: {'name': 'The Creative', 'chinese': '乾 (Qián)', 'symbol': '☰☰', 'meaning': 'Heaven over Heaven', 'keywords': 'Strength, primal creativity, active initiative'},
            2: {'name': 'The Receptive', 'chinese': '坤 (Kūn)', 'symbol': '☷☷', 'meaning': 'Earth over Earth', 'keywords': 'Devotion, yielding, spacious receptivity'},
            3: {'name': 'Difficulty at the Beginning', 'chinese': '屯 (Zhūn)', 'symbol': '☵☳', 'meaning': 'Water over Thunder', 'keywords': 'Birth pangs, chaos, perseverance in planting seeds'},
            4: {'name': 'Youthful Folly', 'chinese': '蒙 (Méng)', 'symbol': '☶☵', 'meaning': 'Mountain over Water', 'keywords': 'Inexperience, humility, seeking sage guidance'},
            5: {'name': 'Waiting', 'chinese': '需 (Xū)', 'symbol': '☵☰', 'meaning': 'Water over Heaven', 'keywords': 'Patience, inner nourishment, divine timing'},
            6: {'name': 'Conflict', 'chinese': '訟 (Sòng)', 'symbol': '☰☵', 'meaning': 'Heaven over Water', 'keywords': 'Tension, halting contention, seeking mediation'},
            7: {'name': 'The Army', 'chinese': '師 (Shī)', 'symbol': '☷☵', 'meaning': 'Earth over Water', 'keywords': 'Discipline, collective leadership, rightful purpose'},
            8: {'name': 'Holding Together', 'chinese': '比 (Bǐ)', 'symbol': '☵☷', 'meaning': 'Water over Earth', 'keywords': 'Sacred union, mutual alliance, genuine devotion'},
            9: {'name': 'Small Accumulating', 'chinese': '小畜 (Xiǎo Xù)', 'symbol': '☴☰', 'meaning': 'Wind over Heaven', 'keywords': 'Gentle restraint, small steps, gathering quiet force'},
            10: {'name': 'Treading', 'chinese': '履 (Lǚ)', 'symbol': '☰☱', 'meaning': 'Heaven over Lake', 'keywords': 'Careful conduct, stepping on tiger tail without bite, etiquette'},
            11: {'name': 'Peace', 'chinese': '泰 (Tài)', 'symbol': '☷☰', 'meaning': 'Earth over Heaven', 'keywords': 'Cosmic harmony, golden age, heaven and earth intermingling'},
            12: {'name': 'Standstill', 'chinese': '否 (Pǐ)', 'symbol': '☰☷', 'meaning': 'Heaven over Earth', 'keywords': 'Stagnation, retreat of the wise, division between realms'},
            13: {'name': 'Fellowship', 'chinese': '同人 (Tóng Rén)', 'symbol': '☰☲', 'meaning': 'Heaven over Fire', 'keywords': 'Community in the open, universal brotherhood, shared vision'},
            14: {'name': 'Great Possessing', 'chinese': '大有 (Dà Yǒu)', 'symbol': '☲☰', 'meaning': 'Fire over Heaven', 'keywords': 'Radiant abundance, supreme clarity, stewardship of wealth'},
            15: {'name': 'Modesty', 'chinese': '謙 (Qiān)', 'symbol': '☷☶', 'meaning': 'Earth over Mountain', 'keywords': 'Humility, mountain hidden beneath earth, balance of peaks'},
            16: {'name': 'Enthusiasm', 'chinese': '豫 (Yù)', 'symbol': '☳☷', 'meaning': 'Thunder over Earth', 'keywords': 'Inspiration, music, mobilizing collective joy'},
            17: {'name': 'Following', 'chinese': '隨 (Suí)', 'symbol': '☱☳', 'meaning': 'Lake over Thunder', 'keywords': 'Graceful adaptation, following natural law, resting in cycle'},
            18: {'name': 'Work on the Decayed', 'chinese': '蠱 (Gǔ)', 'symbol': '☶☴', 'meaning': 'Mountain over Wind', 'keywords': 'Remedying what was spoiled, healing ancestral wounds, restoration'},
            19: {'name': 'Approach', 'chinese': '臨 (Lín)', 'symbol': '☷☱', 'meaning': 'Earth over Lake', 'keywords': 'Spring awakening, auspicious arrival, vigilance before winter'},
            20: {'name': 'Contemplation', 'chinese': '觀 (Guān)', 'symbol': '☴☷', 'meaning': 'Wind over Earth', 'keywords': 'Sacred observation, tower view, looking with deep awareness'},
            21: {'name': 'Biting Through', 'chinese': '噬嗑 (Shì Kè)', 'symbol': '☲☳', 'meaning': 'Fire over Thunder', 'keywords': 'Piercing obstacle, enforcing justice, removing delusion'},
            22: {'name': 'Grace', 'chinese': '賁 (Bì)', 'symbol': '☶☲', 'meaning': 'Mountain over Fire', 'keywords': 'Beauty of form, cultural elegance, remembering essential substance'},
            23: {'name': 'Splitting Apart', 'chinese': '剝 (Bō)', 'symbol': '☶☷', 'meaning': 'Mountain over Earth', 'keywords': 'Deterioration, shedding old husk, generous giving before fall'},
            24: {'name': 'Return', 'chinese': '復 (Fù)', 'symbol': '☷☳', 'meaning': 'Earth over Thunder', 'keywords': 'Winter solstice, turning point of light, return of original spirit'},
            25: {'name': 'Innocence', 'chinese': '無妄 (Wú Wàng)', 'symbol': '☰☳', 'meaning': 'Heaven over Thunder', 'keywords': 'The unexpected, free from calculating intent, natural truth'},
            26: {'name': 'Great Accumulating', 'chinese': '大畜 (Dà Xù)', 'symbol': '☶☰', 'meaning': 'Mountain over Heaven', 'keywords': 'Storing immense power, deep character, ready for great crossing'},
            27: {'name': 'Nourishment', 'chinese': '頤 (Yí)', 'symbol': '☶☳', 'meaning': 'Mountain over Thunder', 'keywords': 'Open jaws, what enters and leaves the mouth, self-care'},
            28: {'name': 'Great Preponderance', 'chinese': '大過 (Dà Guò)', 'symbol': '☱☴', 'meaning': 'Lake over Wind', 'keywords': 'Ridgepole sagging, extraordinary burden, heroic action'},
            29: {'name': 'The Abysmal', 'chinese': '坎 (Kǎn)', 'symbol': '☵☵', 'meaning': 'Water over Water', 'keywords': 'Repeated chasm, flowing through danger without losing nature'},
            30: {'name': 'The Clinging Fire', 'chinese': '離 (Lí)', 'symbol': '☲☲', 'meaning': 'Fire over Fire', 'keywords': 'Illumination, clinging to goodness, clarity of vision'},
            31: {'name': 'Influence', 'chinese': '咸 (Xián)', 'symbol': '☱☶', 'meaning': 'Lake over Mountain', 'keywords': 'Mutual attraction, heart resonance, quiet receptive courtship'},
            32: {'name': 'Duration', 'chinese': '恆 (Héng)', 'symbol': '☳☴', 'meaning': 'Thunder over Wind', 'keywords': 'Enduring rhythm, steadfast movement, eternal constancy'},
            33: {'name': 'Retreat', 'chinese': '遯 (Dùn)', 'symbol': '☰☶', 'meaning': 'Heaven over Mountain', 'keywords': 'Strategic withdrawal, preserving dignity, timing one\'s step back'},
            34: {'name': 'Great Power', 'chinese': '大壯 (Dà Zhuàng)', 'symbol': '☳☰', 'meaning': 'Thunder over Heaven', 'keywords': 'Thunder in the sky, righteous vigor, avoiding brute force'},
            35: {'name': 'Progress', 'chinese': '晉 (Jìn)', 'symbol': '☲☷', 'meaning': 'Fire over Earth', 'keywords': 'Sun rising over horizon, expansion, recognized virtue'},
            36: {'name': 'Darkening of the Light', 'chinese': '明夷 (Míng Yí)', 'symbol': '☷☲', 'meaning': 'Earth over Fire', 'keywords': 'Sun sinking below earth, cloaking brilliance in adversity'},
            37: {'name': 'The Family', 'chinese': '家人 (Jiā Rén)', 'symbol': '☴☲', 'meaning': 'Wind over Fire', 'keywords': 'Inner household, authentic roles, warmth and order in clan'},
            38: {'name': 'Opposition', 'chinese': '睽 (Kuí)', 'symbol': '☲☱', 'meaning': 'Fire over Lake', 'keywords': 'Polarity, divergent paths, finding creative unity in difference'},
            39: {'name': 'Obstruction', 'chinese': '蹇 (Jiǎn)', 'symbol': '☵☶', 'meaning': 'Water over Mountain', 'keywords': 'Lame foot, halting before danger, turning inward to cultivate virtue'},
            40: {'name': 'Deliverance', 'chinese': '解 (Xiè)', 'symbol': '☳☵', 'meaning': 'Thunder over Water', 'keywords': 'Release from tension, spring thaw, forgiveness and return'},
            41: {'name': 'Decrease', 'chinese': '損 (Sǔn)', 'symbol': '☶☱', 'meaning': 'Mountain over Lake', 'keywords': 'Simplification, curbing anger and desire, offering sincere vessel'},
            42: {'name': 'Increase', 'chinese': '益 (Yì)', 'symbol': '☴☳', 'meaning': 'Wind over Thunder', 'keywords': 'Generous blessing, imitating excellence, pouring outward'},
            43: {'name': 'Breakthrough', 'chinese': '夬 (Guài)', 'symbol': '☱☰', 'meaning': 'Lake over Heaven', 'keywords': 'Decisive resolution, public truth without malice, breakthrough'},
            44: {'name': 'Coming to Meet', 'chinese': '姤 (Gòu)', 'symbol': '☰☴', 'meaning': 'Heaven over Wind', 'keywords': 'Encounter with shadow, seductive force, clear boundaries'},
            45: {'name': 'Gathering Together', 'chinese': '萃 (Cuì)', 'symbol': '☱☷', 'meaning': 'Lake over Earth', 'keywords': 'Assembly at altar, collective reverence, strength in unity'},
            46: {'name': 'Pushing Upward', 'chinese': '升 (Shēng)', 'symbol': '☷☴', 'meaning': 'Earth over Wind', 'keywords': 'Tree rising from earth, steady ascent, auspicious upward path'},
            47: {'name': 'Oppression', 'chinese': '困 (Kùn)', 'symbol': '☱☵', 'meaning': 'Lake over Water', 'keywords': 'Lake exhausted into abyss, dry well, testing inner integrity'},
            48: {'name': 'The Well', 'chinese': '井 (Jǐng)', 'symbol': '☵☴', 'meaning': 'Water over Wind', 'keywords': 'Inexhaustible fountain, communal nourishment, maintaining the vessel'},
            49: {'name': 'Revolution', 'chinese': '革 (Gé)', 'symbol': '☱☲', 'meaning': 'Lake over Fire', 'keywords': 'Molting season, radical transformation, timing sacred shift'},
            50: {'name': 'The Cauldron', 'chinese': '鼎 (Dǐng)', 'symbol': '☲☴', 'meaning': 'Fire over Wind', 'keywords': 'Sacred vessel of transformation, alchemical refinement, divine sustenance'},
            51: {'name': 'The Arousing', 'chinese': '震 (Zhèn)', 'symbol': '☳☳', 'meaning': 'Thunder over Thunder', 'keywords': 'Shock that brings reverence, laughter after thunder, awakening'},
            52: {'name': 'Keeping Still', 'chinese': '艮 (Gèn)', 'symbol': '☶☶', 'meaning': 'Mountain over Mountain', 'keywords': 'Meditation, resting the spine, stillness of mind and senses'},
            53: {'name': 'Development', 'chinese': '漸 (Jiàn)', 'symbol': '☴☶', 'meaning': 'Wind over Mountain', 'keywords': 'Gradual flight of wild geese, step-by-step progress, propriety'},
            54: {'name': 'The Marrying Maiden', 'chinese': '歸妹 (Guī Mèi)', 'symbol': '☳☱', 'meaning': 'Thunder over Lake', 'keywords': 'Secondary role, volatile desire, patience in secondary place'},
            55: {'name': 'Abundance', 'chinese': '豐 (Fēng)', 'symbol': '☳☲', 'meaning': 'Thunder over Fire', 'keywords': 'Zenith of brightness, noon sun, eclipses, carrying grandeur'},
            56: {'name': 'The Wanderer', 'chinese': '旅 (Lǚ)', 'symbol': '☲☶', 'meaning': 'Fire over Mountain', 'keywords': 'Traveling stranger, humble discretion, non-attachment'},
            57: {'name': 'The Gentle', 'chinese': '巽 (Xùn)', 'symbol': '☴☴', 'meaning': 'Wind over Wind', 'keywords': 'Continuous gentle penetration, clarity of intent, flexibility'},
            58: {'name': 'The Joyous', 'chinese': '兌 (Duì)', 'symbol': '☱☱', 'meaning': 'Lake over Lake', 'keywords': 'Contagious delight, honest dialogue, shared celebration'},
            59: {'name': 'Dispersion', 'chinese': '渙 (Huàn)', 'symbol': '☴☵', 'meaning': 'Wind over Water', 'keywords': 'Dissolving rigid ice, blowing away barriers, crossing broad river'},
            60: {'name': 'Limitation', 'chinese': '節 (Jié)', 'symbol': '☵☱', 'meaning': 'Water over Lake', 'keywords': 'Bamboo joints, rhythmic boundaries, moderation that enables music'},
            61: {'name': 'Inner Truth', 'chinese': '中孚 (Zhōng Fú)', 'symbol': '☴☱', 'meaning': 'Wind over Lake', 'keywords': 'Heart of sincerity, hatching bird, trust that moves water and pigs'},
            62: {'name': 'Small Preponderance', 'chinese': '小過 (Xiǎo Guò)', 'symbol': '☳☶', 'meaning': 'Thunder over Mountain', 'keywords': 'Flying bird, attention to minute detail, exceeding in humility'},
            63: {'name': 'After Completion', 'chinese': '既濟 (Jì Jì)', 'symbol': '☵☲', 'meaning': 'Water over Fire', 'keywords': 'Kettle boiling, all lines in place, vigilance against entropy'},
            64: {'name': 'Before Completion', 'chinese': '未濟 (Wèi Jì)', 'symbol': '☲☵', 'meaning': 'Fire over Water', 'keywords': 'Fox wetting its tail, eternal cycle, infinite potential to begin anew'}
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
        """Calculate hexagram using the ancient 3-coin toss method (3 coins, 6 throws from bottom to top)."""
        tosses = self.quantum_coin_toss()
        lines = []
        coin_tosses = []

        # Process 3 tosses at a time to generate 6 lines (bottom Line 1 to top Line 6)
        for i in range(0, 18, 3):
            three_tosses = tosses[i:i+3]
            coin_tosses.append(three_tosses)
            heads = sum(three_tosses)

            # Traditional I Ching coin values:
            # 3 heads = Old Yang (9) - moving / changing
            # 2 heads = Young Yang (7) - stable
            # 1 head  = Young Yin (8) - stable
            # 0 heads = Old Yin (6) - moving / changing
            if heads == 3:
                lines.append(9)
            elif heads == 2:
                lines.append(7)
            elif heads == 1:
                lines.append(8)
            else:
                lines.append(6)

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

        # Primary Hexagram: lines 1-3 (lower) and 4-6 (upper)
        lower_tuple = tuple(1 if line in [7, 9] else 0 for line in lines[0:3])
        upper_tuple = tuple(1 if line in [7, 9] else 0 for line in lines[3:6])
        lower_symbol = trigram_map.get(lower_tuple, '☰')
        upper_symbol = trigram_map.get(upper_tuple, '☰')
        combined_symbol = f"{upper_symbol}{lower_symbol}"

        primary_num = 1
        for num, data in self.hexagrams.items():
            if data['symbol'] == combined_symbol:
                primary_num = num
                break

        # Changing Lines (1-indexed from bottom Line 1 to top Line 6)
        changing_lines = [i + 1 for i, line in enumerate(lines) if line in [6, 9]]

        # Transformed Hexagram (Zhi Gua) calculation if changing lines exist
        transformed_num = None
        transformed_lines = None
        if changing_lines:
            # 9 (Old Yang) inverts to 8 (Young Yin); 6 (Old Yin) inverts to 7 (Young Yang)
            transformed_lines = [8 if l == 9 else 7 if l == 6 else l for l in lines]
            trans_lower_tuple = tuple(1 if l in [7, 9] else 0 for l in transformed_lines[0:3])
            trans_upper_tuple = tuple(1 if l in [7, 9] else 0 for l in transformed_lines[3:6])
            trans_lower_symbol = trigram_map.get(trans_lower_tuple, '☰')
            trans_upper_symbol = trigram_map.get(trans_upper_tuple, '☰')
            trans_combined_symbol = f"{trans_upper_symbol}{trans_lower_symbol}"

            for num, data in self.hexagrams.items():
                if data['symbol'] == trans_combined_symbol:
                    transformed_num = num
                    break

        return {
            'number': primary_num,
            'lines': lines,
            'changing_lines': changing_lines,
            'coin_tosses': coin_tosses,
            'upper_symbol': upper_symbol,
            'lower_symbol': lower_symbol,
            'transformed_number': transformed_num,
            'transformed_lines': transformed_lines
        }

    def _assemble_hex_data(self, number, lines):
        """Assembles rich metadata for a given hexagram number and its 6 lines."""
        data = self.hexagrams[number]
        upper_sym = data['symbol'][0]
        lower_sym = data['symbol'][1]
        return {
            'number': number,
            'name': data['name'],
            'chinese': data['chinese'],
            'symbol': data['symbol'],
            'meaning': data['meaning'],
            'keywords': data['keywords'],
            'upper_trigram': TRIGRAMS.get(upper_sym, {}),
            'lower_trigram': TRIGRAMS.get(lower_sym, {}),
            'lines': lines
        }

    def cast_hexagram(self):
        """Perform a complete I Ching casting with primary & transformed hexagrams."""
        calc = self.calculate_hexagram()
        primary_data = self._assemble_hex_data(calc['number'], calc['lines'])

        transformed_data = None
        if calc['transformed_number']:
            transformed_data = self._assemble_hex_data(calc['transformed_number'], calc['transformed_lines'])

        return {
            'number': primary_data['number'],
            'name': primary_data['name'],
            'chinese': primary_data['chinese'],
            'symbol': primary_data['symbol'],
            'meaning': primary_data['meaning'],
            'keywords': primary_data['keywords'],
            'upper_trigram': primary_data['upper_trigram'],
            'lower_trigram': primary_data['lower_trigram'],
            'changing_lines': calc['changing_lines'],
            'lines': calc['lines'],
            'coin_tosses': calc['coin_tosses'],
            'transformed': transformed_data
        }

    def get_hexagram_info(self, number):
        """Get information about a specific hexagram."""
        if number in self.hexagrams:
            data = self.hexagrams[number].copy()
            data['upper_trigram'] = TRIGRAMS.get(data['symbol'][0], {})
            data['lower_trigram'] = TRIGRAMS.get(data['symbol'][1], {})
            return data
        return {}
