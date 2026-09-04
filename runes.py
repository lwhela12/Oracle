import requests
import random

url = "https://qrandom.io/api/random/ints"

class RuneCast:
    def __init__(self):
        # Elder Futhark runes (24 runes + blank/wyrd)
        # Symmetrical runes have reversible=False (no inverted / merkstave form)
        self.runes = {
            # Freyr's Ætt (Creation, Beginnings, Vital Energy)
            'fehu': {
                'symbol': 'ᚠ', 'name': 'Fehu', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Cattle, Wealth', 'keywords': 'Prosperity, abundance, creative energy, financial gain',
                'merkstave': 'Loss of Wealth, Greed, Burnout', 'merkstave_keywords': 'Discontent, material loss, squandered resources, exhaustion'
            },
            'uruz': {
                'symbol': 'ᚢ', 'name': 'Uruz', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Aurochs, Primal Strength', 'keywords': 'Vitality, raw power, untamed endurance, health',
                'merkstave': 'Weakness, Misdirected Force, Illness', 'merkstave_keywords': 'Physical drain, blunt aggression, missed opportunity, stubbornness'
            },
            'thurisaz': {
                'symbol': 'ᚦ', 'name': 'Thurisaz', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Giant, Thorn, Gateway', 'keywords': 'Protection, breakthrough, reactive force, catalysts',
                'merkstave': 'Compulsion, Vulnerability, Rash Anger', 'merkstave_keywords': 'Danger, defenselessness, hasty temper, betrayal, self-sabotage'
            },
            'ansuz': {
                'symbol': 'ᚨ', 'name': 'Ansuz', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Ancestral God, Divine Breath', 'keywords': 'Communication, divine inspiration, wisdom, truthful counsel',
                'merkstave': 'Misunderstanding, Deceit, Manipulation', 'merkstave_keywords': 'Distorted truth, bad advice, vanity, blocked communication'
            },
            'raidho': {
                'symbol': 'ᚱ', 'name': 'Raidho', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Wagon, Journey, Cosmic Order', 'keywords': 'Travel, life rhythm, righteous action, momentum',
                'merkstave': 'Disruption, Stagnation, Injustice', 'merkstave_keywords': 'Broken journey, delays, rigid dogmatism, moral crisis'
            },
            'kenaz': {
                'symbol': 'ᚲ', 'name': 'Kenaz', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Torch, Illumination', 'keywords': 'Knowledge, creative spark, revelation, keen clarity',
                'merkstave': 'Darkness, Extinguished Spark, Blindness', 'merkstave_keywords': 'Loss of insight, confusion, false hope, lack of purpose'
            },
            'gebo': {
                'symbol': 'ᚷ', 'name': 'Gebo', 'aett': "Freyr's Ætt", 'reversible': False,
                'meaning': 'Gift, Exchange, Sacred Bond', 'keywords': 'Partnership, generosity, sacred reciprocity, balance',
                'merkstave': 'Gift, Exchange, Sacred Bond', 'merkstave_keywords': 'Partnership, generosity, sacred reciprocity, balance'
            },
            'wunjo': {
                'symbol': 'ᚹ', 'name': 'Wunjo', 'aett': "Freyr's Ætt", 'reversible': True,
                'meaning': 'Joy, Harmony, Fellowship', 'keywords': 'Happiness, triumph, emotional blessing, kinship',
                'merkstave': 'Sorrow, Alienation, Discord', 'merkstave_keywords': 'Strife, emotional grief, unfulfilled longing, frenzied conflict'
            },

            # Heimdall's / Hagal's Ætt (Trials, Nature, Transformation)
            'hagalaz': {
                'symbol': 'ᚺ', 'name': 'Hagalaz', 'aett': "Heimdall's Ætt", 'reversible': False,
                'meaning': 'Hail, Cosmic Disruption', 'keywords': 'Radical transformation, natural storms, breakdown of the obsolete',
                'merkstave': 'Hail, Cosmic Disruption', 'merkstave_keywords': 'Radical transformation, natural storms, breakdown of the obsolete'
            },
            'nauthiz': {
                'symbol': 'ᚾ', 'name': 'Nauthiz', 'aett': "Heimdall's Ætt", 'reversible': True,
                'meaning': 'Need, Friction, Sacred Constraint', 'keywords': 'Endurance, necessity as teacher, resilience, self-discipline',
                'merkstave': 'Despair, Enslavement to Craving, Distress', 'merkstave_keywords': 'Severe deprivation, resisting fate, self-pity, constriction'
            },
            'isa': {
                'symbol': 'ᛁ', 'name': 'Isa', 'aett': "Heimdall's Ætt", 'reversible': False,
                'meaning': 'Ice, Stillness, Absolute Clarity', 'keywords': 'Patience, deep focus, winter preservation, frozen momentum',
                'merkstave': 'Ice, Stillness, Absolute Clarity', 'merkstave_keywords': 'Patience, deep focus, winter preservation, frozen momentum'
            },
            'jera': {
                'symbol': 'ᛃ', 'name': 'Jera', 'aett': "Heimdall's Ætt", 'reversible': False,
                'meaning': 'Year, Harvest, Natural Cycles', 'keywords': 'Fruition, karmic return, lawful growth, earned reward',
                'merkstave': 'Year, Harvest, Natural Cycles', 'merkstave_keywords': 'Fruition, karmic return, lawful growth, earned reward'
            },
            'eihwaz': {
                'symbol': 'ᛇ', 'name': 'Eihwaz', 'aett': "Heimdall's Ætt", 'reversible': False,
                'meaning': 'Yew Tree, Spine of the World', 'keywords': 'Spiritual endurance, life-death transition, defense, immortality',
                'merkstave': 'Yew Tree, Spine of the World', 'merkstave_keywords': 'Spiritual endurance, life-death transition, defense, immortality'
            },
            'perthro': {
                'symbol': 'ᛈ', 'name': 'Perthro', 'aett': "Heimdall's Ætt", 'reversible': True,
                'meaning': 'Dice Cup, Mystery, Fate', 'keywords': 'The occult, chance, hidden wyrd, evolutionary secret',
                'merkstave': 'Stagnation, Bitter Fate, Unwelcome Secrets', 'merkstave_keywords': 'Unpleasant revelations, despair, betrayal of confidence, entrapment'
            },
            'algiz': {
                'symbol': 'ᛉ', 'name': 'Algiz', 'aett': "Heimdall's Ætt", 'reversible': True,
                'meaning': 'Elk, Divine Sanctuary, Protection', 'keywords': 'Spiritual shield, awakening intuition, guardian forces',
                'merkstave': 'Vulnerability, Hidden Danger, Misplaced Trust', 'merkstave_keywords': 'Breached defenses, warnings ignored, psychic exhaustion, deception'
            },
            'sowilo': {
                'symbol': 'ᛊ', 'name': 'Sowilo', 'aett': "Heimdall's Ætt", 'reversible': False,
                'meaning': 'Sun, Sacred Victory, Wholeness', 'keywords': 'Illumination, life force, undeniable success, solar clarity',
                'merkstave': 'Sun, Sacred Victory, Wholeness', 'merkstave_keywords': 'Sun, Sacred Victory, Wholeness'
            },

            # Týr's Ætt (Spirit, Mastery, Human Destiny)
            'tiwaz': {
                'symbol': 'ᛏ', 'name': 'Tiwaz', 'aett': "Týr's Ætt", 'reversible': True,
                'meaning': 'Tyr, Moral Justice, Victory', 'keywords': 'Spiritual warrior, honorable sacrifice, leadership, divine order',
                'merkstave': 'Injustice, Diminished Resolve, Dishonor', 'merkstave_keywords': 'Defeat, impatience, conflict without honor, surrendered willpower'
            },
            'berkano': {
                'symbol': 'ᛒ', 'name': 'Berkano', 'aett': "Týr's Ætt", 'reversible': True,
                'meaning': 'Birch Goddess, Rebirth, Fertility', 'keywords': 'Nurturing, new beginnings, sanctuary, organic emergence',
                'merkstave': 'Stunted Growth, Domestic Strife, Friction', 'merkstave_keywords': 'Barren efforts, anxiety, family discord, suppressed potential'
            },
            'ehwaz': {
                'symbol': 'ᛖ', 'name': 'Ehwaz', 'aett': "Týr's Ætt", 'reversible': True,
                'meaning': 'Sacred Horse, Partnership, Movement', 'keywords': 'Mutual loyalty, steady advancement, sacred vehicle, trust',
                'merkstave': 'Restlessness, Betrayal of Trust, Stalled Momentum', 'merkstave_keywords': 'Fractured alliance, mistrust, erratic motion, indecision'
            },
            'mannaz': {
                'symbol': 'ᛗ', 'name': 'Mannaz', 'aett': "Týr's Ætt", 'reversible': True,
                'meaning': 'Humanity, Self, Higher Mind', 'keywords': 'Self-realization, human solidarity, intellect, divine reflection',
                'merkstave': 'Isolation, Self-Delusion, Alienation', 'merkstave_keywords': 'Alienation from tribe, arrogance, self-sabotage, hostility'
            },
            'laguz': {
                'symbol': 'ᛚ', 'name': 'Laguz', 'aett': "Týr's Ætt", 'reversible': True,
                'meaning': 'Water, Deep Intuition, The Unconscious', 'keywords': 'Flow, dreams, emotional vitality, psychic tide',
                'merkstave': 'Confusion, Emotional Deluge, Toxic Flow', 'merkstave_keywords': 'Drowning in emotion, poor instincts, panic, self-deceit'
            },
            'ingwaz': {
                'symbol': 'ᛜ', 'name': 'Ingwaz', 'aett': "Týr's Ætt", 'reversible': False,
                'meaning': 'Ing, Earth God, Sacred Gestation', 'keywords': 'Completion, internal containment, seed potential, quiet rest',
                'merkstave': 'Ing, Earth God, Sacred Gestation', 'merkstave_keywords': 'Completion, internal containment, seed potential, quiet rest'
            },
            'dagaz': {
                'symbol': 'ᛞ', 'name': 'Dagaz', 'aett': "Týr's Ætt", 'reversible': False,
                'meaning': 'Day, Dawn, Paradoxical Awakening', 'keywords': 'Breakthrough, enlightenment, balance of light and dark, transformation',
                'merkstave': 'Day, Dawn, Paradoxical Awakening', 'merkstave_keywords': 'Breakthrough, enlightenment, balance of light and dark, transformation'
            },
            'othala': {
                'symbol': 'ᛟ', 'name': 'Othala', 'aett': "Týr's Ætt", 'reversible': True,
                'meaning': 'Ancestral Estate, Spiritual Heritage', 'keywords': 'Sacred enclosure, inherited wisdom, home, lineage',
                'merkstave': 'Rootlessness, Ancestral Rift, Loss of Heritage', 'merkstave_keywords': 'Homelessness, family disputes, obsolete dogma, alienation'
            },

            # Modern Addition (Blank Rune / Wyrd)
            'wyrd': {
                'symbol': '⬚', 'name': 'Wyrd', 'aett': "The Void", 'reversible': False,
                'meaning': 'The Blank Rune, Absolute Unwritten Fate', 'keywords': 'The unknown, cosmic karma, divine mystery, total surrender',
                'merkstave': 'The Blank Rune, Absolute Unwritten Fate', 'merkstave_keywords': 'The unknown, cosmic karma, divine mystery, total surrender'
            }
        }

        self.spread_configs = {
            'single': {
                'name': "Odin's Rune",
                'description': "Immediate insight and prevailing guidance from the All-Father.",
                'count': 1,
                'positions': ["Odin's Rune / Immediate Insight"]
            },
            'norns': {
                'name': "The Three Norns",
                'description': "Sacred three-rune casting at the Well of Urðr.",
                'count': 3,
                'positions': [
                    "Urðr (Past Origin & Karmic Roots)",
                    "Verðandi (Present Becoming & Current Flow)",
                    "Skuld (Future Debt & Inevitable Necessity)"
                ]
            },
            'five-cross': {
                'name': "The Five-Rune Wyrd Cross",
                'description': "Compass of fate examining core issue, roots, horizon, guidance, and outcome.",
                'count': 5,
                'positions': [
                    "The Core (Center / Heart of the Matter)",
                    "The West (Fading Past & Roots)",
                    "The East (Arriving Horizon & Emerging Force)",
                    "The North (Guiding Lesson & Divine Aid)",
                    "The South (Resulting Wyrd & Final Resolution)"
                ]
            },
            'thor-hammer': {
                'name': "The Hammer of Thor",
                'description': "Mjölnir casting for conflict resolution, courage, and breaking impasses.",
                'count': 5,
                'positions': [
                    "The Striking Point (The Core Conflict & Impasse)",
                    "The Left Wing (Inner Doubt & Vulnerability)",
                    "The Right Wing (External Opposition & Adversaries)",
                    "The Shaft (Divine Source of Strength)",
                    "The Grip (Decisive Action & Empowered Strike)"
                ]
            },
            'nine-worlds': {
                'name': "The Nine Worlds of Yggdrasil",
                'description': "Grand 9-realm cosmic casting across the branches and roots of the World Tree.",
                'count': 9,
                'positions': [
                    "Asgard (Upper Realm / Divine Will & Spiritual Calling)",
                    "Alfheim (Upper Mind / Intellect, Clarity & Light)",
                    "Vanaheim (Middle Flow / Heart, Relationships & Growth)",
                    "Midgard (Center / Physical Reality & Daily Life)",
                    "Jotunheim (Outer Chaos / Shadow Challenges & Illusions)",
                    "Svartalfheim (Subconscious / Instincts & Hidden Power)",
                    "Muspelheim (Primal Fire / Passion, Drive & Vital Spark)",
                    "Niflheim (Primal Ice / Resistance, Delays & Karmic Freeze)",
                    "Helheim (Underworld / Ancestral Roots & Rebirth)"
                ]
            }
        }

    def _normalize_spread_key(self, spread_type):
        """Maps legacy or alias spread keys to canonical keys."""
        mapping = {
            '3-card': 'norns',
            'yes-no': 'single',
            'single': 'single',
            'norns': 'norns',
            'five-cross': 'five-cross',
            '5-card': 'five-cross',
            'thor-hammer': 'thor-hammer',
            'nine-worlds': 'nine-worlds',
            'celtic': 'nine-worlds'
        }
        return mapping.get(spread_type, 'norns')

    def get_spread_info(self, spread_type='norns'):
        key = self._normalize_spread_key(spread_type)
        return self.spread_configs.get(key, self.spread_configs['norns'])

    def quantum_draw_with_reversals(self, num_runes=3, allow_reversals=True, include_wyrd=False):
        """Draw unique runes and optional Merkstave (reversed) states using quantum randomness."""
        candidates = [k for k in self.runes.keys() if include_wyrd or k != 'wyrd']
        num_runes = min(num_runes, len(candidates))

        # We request numbers for rune selection + reversal bits
        needed_numbers = len(candidates) + num_runes
        params = {'n': needed_numbers, 'min': 1, 'max': 10000}
        
        numbers = []
        try:
            response = requests.get(url, params=params, timeout=2.5)
            if response.status_code == 200:
                numbers = response.json().get('numbers', [])
        except Exception:
            pass

        if len(numbers) >= needed_numbers:
            # First slice orders candidate runes
            sort_numbers = numbers[:len(candidates)]
            paired = list(zip(sort_numbers, candidates))
            paired.sort(key=lambda x: x[0])
            chosen_keys = [rune_key for _, rune_key in paired[:num_runes]]
            
            # Second slice decides reversals
            rev_numbers = numbers[len(candidates):len(candidates) + num_runes]
            reversals = [(n % 2 == 1) for n in rev_numbers]
        else:
            # Fallback to cryptographically strong system randomness
            sys_rnd = random.SystemRandom()
            chosen_keys = sys_rnd.sample(candidates, num_runes)
            reversals = [sys_rnd.choice([True, False]) for _ in range(num_runes)]

        results = []
        for i, key in enumerate(chosen_keys):
            rune = self.runes[key].copy()
            rune['key'] = key
            
            # Merkstave logic: only reversible runes can be inverted
            can_reverse = rune.get('reversible', False)
            is_rev = bool(allow_reversals and can_reverse and reversals[i])
            rune['is_reversed'] = is_rev
            rune['orientation'] = 'Merkstave (Reversed)' if is_rev else 'Upright'
            
            if is_rev:
                rune['active_meaning'] = rune['merkstave']
                rune['active_keywords'] = rune['merkstave_keywords']
            else:
                rune['active_meaning'] = rune['meaning']
                rune['active_keywords'] = rune['keywords']

            results.append(rune)

        return results

    def cast_spread(self, spread_type='norns', allow_reversals=True, include_wyrd=False):
        """Performs a full ceremonial spread casting."""
        config = self.get_spread_info(spread_type)
        drawn = self.quantum_draw_with_reversals(
            num_runes=config['count'],
            allow_reversals=allow_reversals,
            include_wyrd=include_wyrd
        )
        return {
            'spread_key': self._normalize_spread_key(spread_type),
            'spread_name': config['name'],
            'description': config['description'],
            'positions': config['positions'],
            'runes': drawn
        }

    # Backwards-compatible methods
    def cast_runes(self, num_runes=3):
        return self.quantum_draw_with_reversals(num_runes=num_runes, allow_reversals=True, include_wyrd=True)

    def single_rune(self):
        cast = self.cast_spread('single', allow_reversals=True, include_wyrd=False)
        return cast['runes'][0]

    def three_rune_spread(self):
        cast = self.cast_spread('norns', allow_reversals=True, include_wyrd=False)
        return {
            'situation': cast['runes'][0],
            'action': cast['runes'][1],
            'outcome': cast['runes'][2],
            'positions': cast['positions']
        }

    def get_all_runes(self):
        return self.runes
