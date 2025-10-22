import google.generativeai as genai
from dotenv import load_dotenv
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# from IPython.display import display, Markdown
from tarot import TarotDeck

import requests
import json

url="https://qrandom.io/api/random/int"
load_dotenv()

GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')



class GeminiOracle:
    def __init__(self):
        self.name = "The Oracle"
        self.generation_config={
            "temperature": 1.8
        }
        genai.configure(api_key=GOOGLE_API_KEY)
        self.deck=TarotDeck()
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-exp-0827", 
            safety_settings={HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:HarmBlockThreshold.BLOCK_NONE}, 
            generation_config=self.generation_config,
            )
        self.chat = self.model.start_chat(history=[])
        self.initialize_assistant()
        

    def initialize_assistant(self):
        system_prompt = """
        You are an oracle and a soothsayer. You provide mystical predictions of the future. 
        You are also an expert on tarot. If you are given tarot cards with a question, you will use a three card spread, representing past, present and future to answer the questions. 
        Some requests you are given will come with a magic number. You will interpret that number as a sign to make your reading.
        For number readings you will use your knowledge from numerology, astrology and numbers in spiritual traditions to interpret the number's meaning.
        You will begin by telling the user what number you see, by telling the user the number or cards you were given, by saying "Your cards are " or "Your number is"
        You will then offer your divination to the user. 
        Speak like a goddess.
        


        """
        self.chat.send_message(system_prompt)

    def respond(self, user_input):
        q_response=requests.get(url)
        quantum_data=q_response.json()
        random_number=quantum_data['number']
        new_prompt=f"The user supplies this number {random_number}  And this request + {user_input}"
        response = self.chat.send_message(new_prompt)
        return response.text
    
    def tarot_response(self, user_input):
        self.deck.quantum_shuffle()
        spread=self.deck.reading(3)
        new_prompt=f"These are the cards you've drawn {spread}, to answer this request: {user_input}"
        response = self.chat.send_message(new_prompt)
        return response.text

    def tarot_response_structured(self, user_input, spread_type='3-card'):
        """Returns both the reading text and card data for visual display."""
        self.deck.quantum_shuffle()

        # Determine number of cards based on spread type
        num_cards = {
            '3-card': 3,
            'yes-no': 1,
            '5-card': 5,
            'celtic': 10
        }.get(spread_type, 3)

        spread = self.deck.reading(num_cards)
        card_data = [self.deck.get_card_info(card) for card in spread]
        positions = self.deck.get_spread_positions(spread_type)

        # Customize prompt based on spread type
        if spread_type == 'yes-no':
            new_prompt = f"You drew the card {spread[0]}. Using this card, provide a clear Yes or No answer to: {user_input}. Explain your reasoning based on the card's meaning."
        elif spread_type == 'celtic':
            new_prompt = f"You've drawn a Celtic Cross spread with these 10 cards: {spread}. Provide a comprehensive reading for: {user_input}"
        else:
            new_prompt = f"These are the cards you've drawn {spread}, representing {', '.join(positions)}. Answer this request: {user_input}"

        response = self.chat.send_message(new_prompt)
        return {
            'text': response.text,
            'cards': card_data,
            'positions': positions,
            'spread_type': spread_type
        }

    def clear_history(self):
        """Clears the chat history."""
        self.chat = self.model.start_chat(history=[])  # Start a new chat with empty history
       # print(f"{self.name}: Chat history cleared!")

    def run(self):
        print(f"Welcome! I'm {self.name}. I am here to provide whatever solutions you may need. What do you desire?")

        while True:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit', 'bye']:
                self.clear_history()
                print(f"{self.name}: Blessings")
                break
           
            response = self.tarot_response(user_input)
            print(f"{self.name}: {response}")



#oracle=GeminiOracle()
#oracle.run()