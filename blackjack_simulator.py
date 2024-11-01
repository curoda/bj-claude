from blackjack import Blackjack, BlackjackRules, Card, Hand, GameResult
from basic_strategy import BasicStrategy, Action
from typing import List, Tuple, Dict
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import random
from tqdm import tqdm
import statistics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimulationResult:
    hands_played: int
    total_wagered: float
    total_won: float
    total_lost: float
    blackjacks: int
    wins: int
    losses: int
    pushes: int
    surrenders: int
    doubles: int
    splits: int
    house_edge: float
    std_deviation: float
    bankroll_history: List[float]

class BlackjackSimulator:
    def __init__(self, blackjack_game, basic_strategy, initial_bankroll: float = 100000.0):
        self.game = blackjack_game
        self.strategy = basic_strategy
        self.initial_bankroll = initial_bankroll
        self.base_bet = 10.0  # Standard bet size
        
    def reset_game(self):
        """Reset the game state for a new simulation"""
        self.game = Blackjack(self.game.player.name, self.initial_bankroll, self.game.rules)
        
    def get_strategy_move(self, hand: Hand, dealer_upcard: Card) -> str:
        """Get the basic strategy move for the current hand"""
        # Convert cards to strategy format
        player_cards = []
        for card in hand.cards:
            if card.rank in ['10', 'J', 'Q', 'K']:
                player_cards.append('T')  # All 10-value cards become 'T'
            else:
                player_cards.append(card.rank)
                
        dealer_card = 'T' if dealer_upcard.rank in ['10', 'J', 'Q', 'K'] else dealer_upcard.rank
        
        action = self.strategy.get_action(player_cards, dealer_card)
        return self._convert_action_to_move(action, hand)
    
    def _convert_action_to_move(self, action: Action, hand: Hand) -> str:
        """Convert strategy action to valid game move"""
        valid_moves = self.game.get_valid_moves(hand)
        
        if action == Action.STAND:
            return 'stand'
        elif action == Action.HIT:
            return 'hit'
        elif action == Action.SPLIT and 'split' in valid_moves:
            return 'split'
        elif action == Action.DOUBLE_OR_HIT:
            return 'double' if 'double' in valid_moves else 'hit'
        elif action == Action.DOUBLE_OR_STAND:
            return 'double' if 'double' in valid_moves else 'stand'
        elif action == Action.SPLIT_OR_HIT:
            return 'split' if 'split' in valid_moves else 'hit'
        elif action == Action.SURRENDER_OR_HIT:
            return 'surrender' if 'surrender' in valid_moves else 'hit'
        elif action == Action.SURRENDER_OR_STAND:
            return 'surrender' if 'surrender' in valid_moves else 'stand'
        
        return 'hit'  # Default to hit if no valid move found

    def play_hand(self) -> Tuple[float, Dict]:
        """Play a single hand using basic strategy"""
        metrics = {
            'blackjack': 0,
            'win': 0,
            'loss': 0,
            'push': 0,
            'surrender': 0,
            'double': 0,
            'split': 0
        }

        # Start the round
        if not self.game.start_round(self.base_bet):
            return 0, metrics

        # Get initial state
        dealer_upcard = self.game.get_dealer_upcard()
        
        # Basic strategy never takes insurance or even money
        # Loop through each hand (important for splits)
        hand_index = 0
        while hand_index < len(self.game.player.hands):
            current_hand = self.game.player.hands[hand_index]
            
            # Play the current hand until it's done
            while not current_hand.is_done():
                # Get the strategy move
                move = self.get_strategy_move(current_hand, dealer_upcard)
                
                # Execute the move
                success = self.game.execute_move(move, hand_index)
                
                # Update metrics
                if success:
                    if move == 'split':
                        metrics['split'] += 1
                    elif move == 'double':
                        metrics['double'] += 1
                    elif move == 'surrender':
                        metrics['surrender'] += 1
                
                # If the move wasn't successful or it was a stand, move to next hand
                if not success or move == 'stand':
                    break
            
            # Move to next hand
            hand_index += 1

        # Complete the round
        result = self.game.finish_round()
        
        # Process results
        for game_result, amount in result.hand_results:
            if game_result == GameResult.BLACKJACK:
                metrics['blackjack'] += 1
                metrics['win'] += 1
            elif game_result == GameResult.WIN:
                metrics['win'] += 1
            elif game_result == GameResult.LOSE:
                metrics['loss'] += 1
            elif game_result == GameResult.PUSH:
                metrics['push'] += 1
            elif game_result == GameResult.SURRENDER:
                metrics['surrender'] += 1

        return result.total_win_loss, metrics

    # Rest of the simulator class remains the same...
def print_simulation_results(results: SimulationResult):
    """Print formatted simulation results"""
    print("\nSimulation Results:")
    print(f"Hands Played: {results.hands_played:,}")
    print(f"Total Wagered: ${results.total_wagered:,.2f}")
    print(f"\nOutcomes:")
    print(f"Wins: {results.wins:,} ({results.wins/results.hands_played*100:.2f}%)")
    print(f"Losses: {results.losses:,} ({results.losses/results.hands_played*100:.2f}%)")
    print(f"Pushes: {results.pushes:,} ({results.pushes/results.hands_played*100:.2f}%)")
    print(f"Blackjacks: {results.blackjacks:,} ({results.blackjacks/results.hands_played*100:.2f}%)")
    print(f"Surrenders: {results.surrenders:,} ({results.surrenders/results.hands_played*100:.2f}%)")
    print(f"\nSpecial Plays:")
    print(f"Doubles: {results.doubles:,} ({results.doubles/results.hands_played*100:.2f}%)")
    print(f"Splits: {results.splits:,} ({results.splits/results.hands_played*100:.2f}%)")
    print(f"\nMoney Statistics:")
    print(f"Total Won: ${results.total_won:,.2f}")
    print(f"Total Lost: ${results.total_lost:,.2f}")
    print(f"Net Result: ${results.total_won-results.total_lost:,.2f}")
    print(f"House Edge: {results.house_edge:.3f}%")
    print(f"Standard Deviation: ${results.std_deviation:.2f}")

if __name__ == "__main__":
    # Initialize the game and strategy
    rules = BlackjackRules(
        deck_penetration=0.80,
        max_splits=3,
        allow_resplit_aces=False,
        allow_surrender=True,
        early_surrender=True,
        even_money_offered=True
    )
    
    game = Blackjack("Simulator", 100000.0, rules)
    strategy = BasicStrategy()
    simulator = BlackjackSimulator(game, strategy)
    
    # Run simulation
    print("Running simulation...")
    results = simulator.run_simulation(num_hands=1000000)
    print_simulation_results(results)
