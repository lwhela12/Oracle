import random
import requests

url="https://qrandom.io/api/random/ints"
params={
   "n": 78,
   "min": 1,
   "max": 78
}

class TarotDeck:
    def __init__(self):
        # Major Arcana
        self.major_arcana = [
            'The Fool', 'The Magician', 'The High Priestess', 'The Empress', 'The Emperor',
            'The Hierophant', 'The Lovers', 'The Chariot', 'Strength', 'The Hermit', 'Wheel of Fortune',
            'Justice', 'The Hanged Man', 'Death', 'Temperance', 'The Devil', 'The Tower', 'The Star',
            'The Moon', 'The Sun', 'Judgement', 'The World'
        ]

        # Minor Arcana
        suits = ['Wands', 'Cups', 'Swords', 'Pentacles']
        ranks = ['Ace', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Page', 'Knight', 'Queen', 'King']

        self.cards = self.major_arcana + [
            f'{rank} of {suit}' for suit in suits for rank in ranks
        ]
        self.spread = []

    def get_card_info(self, card_name):
        """Returns detailed information about a card."""
        is_major = card_name in self.major_arcana

        if is_major:
            arcana_type = 'major'
            suit = None
            rank = None
        else:
            arcana_type = 'minor'
            parts = card_name.split(' of ')
            rank = parts[0]
            suit = parts[1] if len(parts) > 1 else None

        return {
            'name': card_name,
            'arcana': arcana_type,
            'suit': suit,
            'rank': rank
        }

    def reset_deck(self):
        """Resets the deck to the full 78 cards."""
        suits = ['Wands', 'Cups', 'Swords', 'Pentacles']
        ranks = ['Ace', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Page', 'Knight', 'Queen', 'King']
        self.cards = list(self.major_arcana) + [
            f'{rank} of {suit}' for suit in suits for rank in ranks
        ]

    def shuffle(self):
        """Shuffles the deck using a cryptographic/system random number generator."""
        random.SystemRandom().shuffle(self.cards)

    def quantum_shuffle(self):
        """Shuffles the deck using quantum random numbers, falling back gracefully to system random."""
        try:
            response = requests.get(url, params=params, timeout=2.5)
            if response.status_code == 200:
                quantum_numbers = response.json().get('numbers', [])
                if len(quantum_numbers) >= len(self.cards):
                    paired = list(zip(quantum_numbers, self.cards))
                    paired.sort(key=lambda x: x[0])
                    self.cards = [card for _, card in paired]
                    return
        except Exception:
            pass
        # Fallback to cryptographically strong system random
        self.shuffle()

    def draw_card(self):
        """Draws a card from the top of the deck."""
        if self.cards:
            return self.cards.pop(0)
        return None

    def reading(self, num_cards):
        """Resets the deck, shuffles, and pulls the requested number of cards."""
        self.reset_deck()
        self.quantum_shuffle()
        num = min(num_cards, len(self.cards))
        return [self.draw_card() for _ in range(num)]

    def get_spread_positions(self, spread_type):
        """Returns position labels for different spread types."""
        spreads = {
            '3-card': ['Past', 'Present', 'Future'],
            'yes-no': ['Answer'],
            '5-card': ['Present Situation', 'Challenge', 'Past', 'Future', 'Outcome'],
            'celtic': [
                'Present', 'Challenge', 'Past', 'Future', 'Above',
                'Below', 'Advice', 'External', 'Hopes/Fears', 'Outcome'
            ]
        }
        return spreads.get(spread_type, ['Card'])
    


#deck=TarotDeck()
#deck.quantum_shuffle()

#print("Here are your cards:")
#print(deck.reading(3))