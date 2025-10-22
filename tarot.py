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

    def shuffle(self):
        """Shuffles the deck using a standard random number generator."""
        random.shuffle(self.cards)

    def quantum_shuffle(self):
        """Shuffles the deck using quantum random numbers."""
        
            # Fetch quantum random numbers from ANU Quantum Random Numbers Server
        response = requests.get(url, params)
            
            
        quantum_numbers = response.json()['numbers']
            # Create a list of tuples pairing each card with a quantum number
        paired = list(zip(quantum_numbers, self.cards))
                # Sort the pairs by the quantum number
        paired.sort(key=lambda x: x[0])
                # Extract the shuffled cards
        self.cards = [card for _, card in paired]
           

    def draw_card(self):
        """Draws a card from the top of the deck."""
        if self.cards:
            return self.cards.pop(0)
        else:
            return "The deck is empty."
      
    def reading(self, num_cards):
        """Pulls the specified number of cards and returns them as a collection."""
        self.quantum_shuffle()
        if num_cards > len(self.cards):
            return "Not enough cards in the deck."
        reading_cards = [self.draw_card() for _ in range(num_cards)]
        return reading_cards
    


#deck=TarotDeck()
#deck.quantum_shuffle()

#print("Here are your cards:")
#print(deck.reading(3))