import random 
import streamlit as st

# Card class 
from collections import namedtuple
Card = namedtuple('Card', ['rank', 'suit'])

ranks = list(range(2, 11)) + ['J', 'Q', 'K', 'A']
suits = ['Hearts', 'Diamonds', 'Spades', 'Clubs']

values = {rank: rank for rank in ranks[:-1]}
values['J'] = 10 
values['Q'] = 10
values['K'] = 10
values['A'] = 11

class Deck:

    def __init__(self):
        self.cards = [Card(suit, rank) for suit in suits for rank in ranks]
        
    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self):
        return self.cards.pop()


class Hand:
    
    def __init__(self):
        self.cards = []
        self.value = 0
        
    def add_card(self, card):
        self.cards.append(card)
        self.value += values[card.rank]
        if card.rank == 'A' and self.value > 21:
            self.value -= 10

def hit(deck, hand):
    card = deck.deal()
    hand.add_card(card)

def play_round(deck):
    player_hand = Hand()
    dealer_hand = Hand()
    
    # Initial deal
    hit(deck, player_hand)
    hit(deck, dealer_hand)
    hit(deck, player_hand)
    hit(deck, dealer_hand)
    
    # Player turn
    while player_hand.value < 21:
        hit(deck, player_hand)
        if player_hand.value > 21:
            return -1
            
    # Dealer turn 
    while dealer_hand.value < 17:
        hit(deck, dealer_hand)
        if dealer_hand.value > 21:
            return 1
            
    return 1 if player_hand.value > dealer_hand.value else -1
    
        
def run_simulations(n):
    deck = Deck()
    deck.shuffle()

    wins = 0
    for _ in range(n):
        result = play_round(deck)
        if result > 0:
            wins += 1

    win_rate = wins / n
    return win_rate

st.title('Blackjack Simulation')
num_hands = st.number_input('Number of hands', min_value=10)
win_rate = run_simulations(num_hands)

st.write(f'Win rate: {win_rate:.2%}')
