import random
import streamlit as st

# Use namedtuple for cleaner card representation
from collections import namedtuple
Card = namedtuple('Card', ['rank', 'suit'])

# Simplify card ranks to remove unneeded strings 
ranks = list(range(2, 11)) + ['J', 'Q', 'K', 'A']
suits = ['Hearts', 'Diamonds', 'Spades', 'Clubs']

# Use a dict for card values to simplify lookups
values = {rank: rank for rank in ranks[:-1]} 
values['J'] = 10
values['Q'] = 10
values['K'] = 10 
values['A'] = 11

# Simplify deck class
class Deck:

    def __init__(self):
        self.cards = [Card(suit, rank) for suit in suits 
                                        for rank in ranks]

    def shuffle(self):
        random.shuffle(self.cards)
        
    def deal(self):
        return self.cards.pop()

# Simplify hand class    
class Hand:
    
    def __init__(self):
        self.cards = []
        self.value = 0
        
    def add_card(self, card):
        self.cards.append(card)
        self.value += values[card.rank]
        if card.rank == 'A' and self.value > 21:
            self.value -= 10
            
# Game logic remains the same

# Output results to Streamlit
st.header('Blackjack Simulation')
n = st.number_input('Number of hands', min_value=10) 
wins = run_simulations(n)
st.write(f'Wins: {wins}')
