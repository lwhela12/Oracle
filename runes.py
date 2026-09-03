import requests
import random

url = "https://qrandom.io/api/random/ints"

class RuneCast:
    def __init__(self):
        # Elder Futhark runes (24 runes + blank/wyrd)
        self.runes = {
            'fehu': {'symbol': 'ᚠ', 'name': 'Fehu', 'meaning': 'Cattle, Wealth', 'keywords': 'Prosperity, abundance, success'},
            'uruz': {'symbol': 'ᚢ', 'name': 'Uruz', 'meaning': 'Aurochs, Strength', 'keywords': 'Power, vitality, determination'},
            'thurisaz': {'symbol': 'ᚦ', 'name': 'Thurisaz', 'meaning': 'Giant, Thorn', 'keywords': 'Protection, conflict, breakthrough'},
            'ansuz': {'symbol': 'ᚨ', 'name': 'Ansuz', 'meaning': 'Ancestral God', 'keywords': 'Communication, wisdom, inspiration'},
            'raidho': {'symbol': 'ᚱ', 'name': 'Raidho', 'meaning': 'Wagon, Journey', 'keywords': 'Travel, rhythm, progression'},
            'kenaz': {'symbol': 'ᚲ', 'name': 'Kenaz', 'meaning': 'Torch', 'keywords': 'Knowledge, creativity, illumination'},
            'gebo': {'symbol': 'ᚷ', 'name': 'Gebo', 'meaning': 'Gift', 'keywords': 'Partnership, generosity, balance'},
            'wunjo': {'symbol': 'ᚹ', 'name': 'Wunjo', 'meaning': 'Joy', 'keywords': 'Harmony, happiness, fellowship'},
            'hagalaz': {'symbol': 'ᚺ', 'name': 'Hagalaz', 'meaning': 'Hail', 'keywords': 'Disruption, transformation, natural forces'},
            'nauthiz': {'symbol': 'ᚾ', 'name': 'Nauthiz', 'meaning': 'Need', 'keywords': 'Necessity, constraint, endurance'},
            'isa': {'symbol': 'ᛁ', 'name': 'Isa', 'meaning': 'Ice', 'keywords': 'Stillness, clarity, focus'},
            'jera': {'symbol': 'ᛃ', 'name': 'Jera', 'meaning': 'Year, Harvest', 'keywords': 'Cycles, reward, fruition'},
            'eihwaz': {'symbol': 'ᛇ', 'name': 'Eihwaz', 'meaning': 'Yew Tree', 'keywords': 'Defense, perseverance, stability'},
            'perthro': {'symbol': 'ᛈ', 'name': 'Perthro', 'meaning': 'Dice Cup', 'keywords': 'Mystery, fate, chance'},
            'algiz': {'symbol': 'ᛉ', 'name': 'Algiz', 'meaning': 'Elk, Protection', 'keywords': 'Defense, sanctuary, intuition'},
            'sowilo': {'symbol': 'ᛊ', 'name': 'Sowilo', 'meaning': 'Sun', 'keywords': 'Success, vitality, wholeness'},
            'tiwaz': {'symbol': 'ᛏ', 'name': 'Tiwaz', 'meaning': 'Tyr, Warrior', 'keywords': 'Honor, justice, leadership'},
            'berkano': {'symbol': 'ᛒ', 'name': 'Berkano', 'meaning': 'Birch', 'keywords': 'Growth, renewal, nurturing'},
            'ehwaz': {'symbol': 'ᛖ', 'name': 'Ehwaz', 'meaning': 'Horse', 'keywords': 'Movement, progress, trust'},
            'mannaz': {'symbol': 'ᛗ', 'name': 'Mannaz', 'meaning': 'Man, Humanity', 'keywords': 'Self, community, cooperation'},
            'laguz': {'symbol': 'ᛚ', 'name': 'Laguz', 'meaning': 'Water, Lake', 'keywords': 'Flow, intuition, emotions'},
            'ingwaz': {'symbol': 'ᛜ', 'name': 'Ingwaz', 'meaning': 'Ing, Fertility', 'keywords': 'Completion, potential, gestation'},
            'dagaz': {'symbol': 'ᛞ', 'name': 'Dagaz', 'meaning': 'Day', 'keywords': 'Breakthrough, awakening, clarity'},
            'othala': {'symbol': 'ᛟ', 'name': 'Othala', 'meaning': 'Ancestral Property', 'keywords': 'Heritage, home, inheritance'},
            'wyrd': {'symbol': '⬚', 'name': 'Wyrd', 'meaning': 'Fate, Blank Rune', 'keywords': 'Unknown, destiny, karma'}
        }

        self.rune_list = list(self.runes.keys())

    def quantum_draw(self, num_runes=3):
        """Draw unique runes using quantum randomness without replacement."""
        num_runes = min(num_runes, len(self.rune_list))
        params = {'n': len(self.rune_list), 'min': 1, 'max': 10000}
        try:
            response = requests.get(url, params=params, timeout=2.5)
            if response.status_code == 200:
                numbers = response.json().get('numbers', [])
                if len(numbers) >= len(self.rune_list):
                    paired = list(zip(numbers, self.rune_list))
                    paired.sort(key=lambda x: x[0])
                    return [rune for _, rune in paired[:num_runes]]
        except Exception:
            pass
        # Fallback to cryptographically strong system random sampling without replacement
        return random.SystemRandom().sample(self.rune_list, num_runes)

    def cast_runes(self, num_runes=3):
        """Perform a rune casting."""
        drawn = self.quantum_draw(num_runes)
        rune_data = []

        for rune_key in drawn:
            rune_info = self.runes[rune_key].copy()
            rune_info['key'] = rune_key
            rune_data.append(rune_info)

        return rune_data

    def single_rune(self):
        """Draw a single rune for quick guidance."""
        return self.cast_runes(1)[0]

    def three_rune_spread(self):
        """Traditional 3-rune spread: Situation, Action, Outcome."""
        runes = self.cast_runes(3)
        return {
            'situation': runes[0],
            'action': runes[1],
            'outcome': runes[2],
            'positions': ['Situation', 'Action', 'Outcome']
        }

    def get_all_runes(self):
        """Return all rune information."""
        return self.runes
