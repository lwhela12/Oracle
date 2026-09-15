import random
from quantum_random import random_indices

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
        """Uniformly reorder the full deck when a caller explicitly needs it."""
        indices = random_indices(range(len(self.cards), 0, -1))
        self.cards = [self.cards.pop(index) for index in indices]

    def draw_card(self):
        """Draws a card from the top of the deck."""
        if self.cards:
            return self.cards.pop(0)
        return None

    def reading(self, num_cards):
        """Draw directly from the shrinking deck, one value per requested card."""
        self.reset_deck()
        num = max(0, min(num_cards, len(self.cards)))
        indices = random_indices(range(len(self.cards), len(self.cards) - num, -1))
        return [self.cards.pop(index) for index in indices]

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
