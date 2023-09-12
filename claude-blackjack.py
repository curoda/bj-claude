import random
import streamlit as st

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
       self.cards = [Card(s, r.split(' ')[0]) for s in suits 
                     for r in ranks]
        
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
    hand.add_card(deck.deal())

    
def play_round(deck):
    player = Hand()
    dealer = Hand()
    
    hit(deck, player)
    hit(deck, dealer)
    hit(deck, player)
    hit(deck, dealer)

    while player.value < 21:
        hit(deck, player)
        if player.value > 21:
            return -1

    while dealer.value < 17:
        hit(deck, dealer)
        if dealer.value > 21:
            return 1
    
    return 1 if player.value > dealer.value else -1

    
def run_simulations(n):
    wins = 0
    for _ in range(n):
        deck = Deck()
        deck.shuffle()
        if play_round(deck) > 0:
            wins += 1
    return wins / n


st.title('Blackjack Simulation')  
num_hands = st.number_input('Number hands', min_value=10)
win_rate = run_simulations(num_hands)

st.write(f'Win rate: {win_rate:.2%}')
