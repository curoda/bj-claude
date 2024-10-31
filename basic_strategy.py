from enum import Enum
from typing import Dict, Optional

class Action(Enum):
    HIT = "H"         # Always hit
    STAND = "S"       # Always stand
    SPLIT = "P"       # Always split
    SURRENDER = "R"   # Always surrender
    DOUBLE = "D"      # Always double
    DOUBLE_OR_HIT = "Dh"    # Double if allowed, otherwise hit
    DOUBLE_OR_STAND = "Ds"  # Double if allowed, otherwise stand
    SPLIT_OR_HIT = "Ph"     # Split if allowed, otherwise hit
    SURRENDER_OR_HIT = "Rh" # Surrender if allowed, otherwise hit

class BasicStrategy:
    def __init__(self):
        # Hard totals (no ace counted as 11)
        self.hard_totals = {
            # Player total vs dealer upcard (2-10, A)
            21: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            20: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            19: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            18: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            17: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            16: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"H", 8:"H", 9:"Rh", 10:"Rh", 1:"Rh"},
            15: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"H", 8:"H", 9:"H", 10:"Rh", 1:"H"},
            14: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            13: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            12: {2:"H", 3:"H", 4:"S", 5:"S", 6:"S", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            11: {2:"Dh", 3:"Dh", 4:"Dh", 5:"Dh", 6:"Dh", 7:"Dh", 8:"Dh", 9:"Dh", 10:"Dh", 1:"H"},
            10: {2:"Dh", 3:"Dh", 4:"Dh", 5:"Dh", 6:"Dh", 7:"Dh", 8:"Dh", 9:"Dh", 10:"H", 1:"H"},
            9:  {2:"H", 3:"Dh", 4:"Dh", 5:"Dh", 6:"Dh", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            8:  {2:"H", 3:"H", 4:"H", 5:"H", 6:"H", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            7:  {2:"H", 3:"H", 4:"H", 5:"H", 6:"H", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            6:  {2:"H", 3:"H", 4:"H", 5:"H", 6:"H", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            5:  {2:"H", 3:"H", 4:"H", 5:"H", 6:"H", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            4:  {2:"H", 3:"H", 4:"H", 5:"H", 6:"H", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"}
        }

        # Soft totals (hand with ace counted as 11)
        self.soft_totals = {
            # A + card value vs dealer upcard (2-10, A)
            21: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            20: {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            19: {2:"S", 3:"S", 4:"S", 5:"S", 6:"Ds", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},
            18: {2:"Ds", 3:"Ds", 4:"Ds", 5:"Ds", 6:"Ds", 7:"S", 8:"S", 9:"H", 10:"H", 1:"H"},
            17: {2:"H", 3:"Dh", 4:"Dh", 5:"Dh", 6:"Dh", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            16: {2:"H", 3:"H", 4:"Dh", 5:"Dh", 6:"Dh", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            15: {2:"H", 3:"H", 4:"Dh", 5:"Dh", 6:"Dh", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            14: {2:"H", 3:"H", 4:"H", 5:"Dh", 6:"Dh", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            13: {2:"H", 3:"H", 4:"H", 5:"Dh", 6:"Dh", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"}
        }

        # Pairs
        self.pairs = {
            # Pairs vs dealer upcard (2-10, A)
            'A': {2:"P", 3:"P", 4:"P", 5:"P", 6:"P", 7:"P", 8:"P", 9:"P", 10:"P", 1:"P"},  # Always split aces
            'T': {2:"S", 3:"S", 4:"S", 5:"S", 6:"S", 7:"S", 8:"S", 9:"S", 10:"S", 1:"S"},  # 10,10 never split
            '9': {2:"P", 3:"P", 4:"P", 5:"P", 6:"P", 7:"S", 8:"P", 9:"P", 10:"S", 1:"S"},
            '8': {2:"P", 3:"P", 4:"P", 5:"P", 6:"P", 7:"P", 8:"P", 9:"P", 10:"P", 1:"P"},  # Always split 8s
            '7': {2:"P", 3:"P", 4:"P", 5:"P", 6:"P", 7:"P", 8:"H", 9:"H", 10:"H", 1:"H"},
            '6': {2:"Ph", 3:"P", 4:"P", 5:"P", 6:"P", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            '5': {2:"Dh", 3:"Dh", 4:"Dh", 5:"Dh", 6:"Dh", 7:"Dh", 8:"Dh", 9:"Dh", 10:"H", 1:"H"},  # Never split 5s
            '4': {2:"H", 3:"H", 4:"H", 5:"Ph", 6:"Ph", 7:"H", 8:"H", 9:"H", 10:"H", 1:"H"},
            '3': {2:"Ph", 3:"Ph", 4:"P", 5:"P", 6:"P", 7:"P", 8:"H", 9:"H", 10:"H", 1:"H"},
            '2': {2:"Ph", 3:"Ph", 4:"P", 5:"P", 6:"P", 7:"P", 8:"H", 9:"H", 10:"H", 1:"H"}
        }

    def get_action(self, player_hand: list, dealer_upcard: str) -> Action:
        """
        Get the basic strategy action for a given hand.
        
        Args:
            player_hand: List of card values (e.g., ['A', '7'] or ['10', '6'])
            dealer_upcard: Dealer's upcard value (e.g., 'A' or '10')
            
        Returns:
            Action enum indicating the correct play
        """
        # Convert dealer upcard to numeric value for lookup
        dealer_value = 1 if dealer_upcard == 'A' else (10 if dealer_upcard in ['T', 'J', 'Q', 'K'] else int(dealer_upcard))
        
        # Check for pairs first
        if len(player_hand) == 2 and player_hand[0] == player_hand[1]:
            card_value = 'A' if player_hand[0] == 'A' else ('T' if player_hand[0] in ['T', 'J', 'Q', 'K'] else player_hand[0])
            return Action(self.pairs[card_value][dealer_value])
            
        # Calculate hand value and check for soft hands
        has_ace = 'A' in player_hand
        if has_ace:
            # Calculate soft total
            non_ace_sum = sum(10 if c in ['T', 'J', 'Q', 'K'] else int(c) 
                            for c in player_hand if c != 'A')
            soft_total = non_ace_sum + 11 + (len([c for c in player_hand if c == 'A']) - 1)
            
            if soft_total <= 21:  # Only use soft total if it wouldn't bust
                if soft_total in self.soft_totals:
                    return Action(self.soft_totals[soft_total][dealer_value])
        
        # Calculate hard total
        total = 0
        aces = sum(1 for c in player_hand if c == 'A')
        non_aces = sum(10 if c in ['T', 'J', 'Q', 'K'] else int(c) 
                      for c in player_hand if c != 'A')
        total = non_aces + aces  # Count all aces as 1 initially
        
        return Action(self.hard_totals[total][dealer_value])

    def print_tables(self):
        """Print formatted basic strategy tables"""
        print("\nLegend:")
        print("H   = Hit")
        print("S   = Stand")
        print("P   = Split")
        print("Dh  = Double if allowed, otherwise Hit")
        print("Ds  = Double if allowed, otherwise Stand")
        print("Ph  = Split if allowed, otherwise Hit")
        print("Rh  = Surrender if allowed, otherwise Hit")
        
        print("\nHard Totals:")
        print("     2  3  4  5  6  7  8  9  T  A")
        for total in range(20, 4, -1):
            row = f"{total:2d}"
            for dealer in range(2, 11):
                row += f"  {self.hard_totals[total][dealer]}"
            row += f"  {self.hard_totals[total][1]}"  # Ace
            print(row)

        print("\nSoft Totals:")
        print("     2  3  4  5  6  7  8  9  T  A")
        for total in range(20, 12, -1):
            row = f"A,{total-11}"
            for dealer in range(2, 11):
                row += f"  {self.soft_totals[total][dealer]}"
            row += f"  {self.soft_totals[total][1]}"  # Ace
            print(row)

        print("\nPairs:")
        print("     2  3  4  5  6  7  8  9  T  A")
        pairs = ["A", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
        for pair in pairs:
            row = f"{pair},{pair}"
            for dealer in range(2, 11):
                row += f"  {self.pairs[pair][dealer]}"
            row += f"  {self.pairs[pair][1]}"  # Ace
            print(row)

if __name__ == "__main__":
    strategy = BasicStrategy()
    strategy.print_tables()
    
    print("\nExample decisions:")
    print(f"8,8 vs Dealer 9:   {strategy.get_action(['8', '8'], '9')}")     # Should be Split
    print(f"A,7 vs Dealer 3:   {strategy.get_action(['A', '7'], '3')}")     # Should be Double/Stand
    print(f"10,6 vs Dealer T:  {strategy.get_action(['10', '6'], '10')}")   # Should be Surrender/Hit
    print(f"6,6 vs Dealer 2:   {strategy.get_action(['6', '6'], '2')}")     # Should be Split/Hit
    print(f"A,6 vs Dealer 4:   {strategy.get_action(['A', '6'], '4')}")     # Should be Double/Hit
