from typing import List, Tuple, Dict
import random
from tqdm import tqdm
import statistics
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

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
            if card.rank in ['J', 'Q', 'K']:
                player_cards.append('T')
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
            'split': 0,
            'insurance': 0
        }

        result = self.game.play_round(self.base_bet)
        
        # Get initial state
        dealer_upcard = self.game.get_dealer_upcard()
        
        # Handle insurance if offered
        if (self.game.rules.insurance_offered and 
            dealer_upcard.rank == 'A' and
            self.strategy.should_take_insurance()):  # This would be a new method to add
            self.game.place_insurance(self.game.player.hands[0])

        # Play each hand according to basic strategy
        for hand_index, hand in enumerate(self.game.player.hands):
            while not hand.is_done():
                move = self.get_strategy_move(hand, dealer_upcard)
                
                if move == 'split':
                    self.game.split(hand_index)
                    metrics['split'] += 1
                elif move == 'double':
                    self.game.double_down(hand)
                    metrics['double'] += 1
                    break
                elif move == 'surrender':
                    self.game.surrender(hand)
                    metrics['surrender'] += 1
                    break
                elif move == 'hit':
                    self.game.hit(hand)
                elif move == 'stand':
                    break

        # Process results
        for result, amount in result.hand_results:
            if result == GameResult.BLACKJACK:
                metrics['blackjack'] += 1
                metrics['win'] += 1
            elif result == GameResult.WIN:
                metrics['win'] += 1
            elif result == GameResult.LOSE:
                metrics['loss'] += 1
            elif result == GameResult.PUSH:
                metrics['push'] += 1
            elif result == GameResult.SURRENDER:
                metrics['surrender'] += 1

        return result.total_win_loss, metrics

    def run_simulation(self, num_hands: int = 100000, processes: int = None) -> SimulationResult:
        """Run multiple hands and gather statistics"""
        if processes is None:
            processes = multiprocessing.cpu_count()

        hands_per_process = num_hands // processes
        
        with ProcessPoolExecutor(max_workers=processes) as executor:
            futures = [
                executor.submit(self._simulate_batch, hands_per_process)
                for _ in range(processes)
            ]
            
            results = [future.result() for future in futures]
        
        # Combine results
        combined = self._combine_simulation_results(results)
        
        # Calculate house edge and other metrics
        combined.house_edge = ((combined.total_lost - combined.total_won) / 
                             combined.total_wagered * 100)
        
        return combined

    def _simulate_batch(self, num_hands: int) -> SimulationResult:
        """Simulate a batch of hands"""
        self.reset_game()
        bankroll_history = []
        results = SimulationResult(
            hands_played=0,
            total_wagered=0,
            total_won=0,
            total_lost=0,
            blackjacks=0,
            wins=0,
            losses=0,
            pushes=0,
            surrenders=0,
            doubles=0,
            splits=0,
            house_edge=0,
            std_deviation=0,
            bankroll_history=[]
        )
        
        for _ in range(num_hands):
            net_win, metrics = self.play_hand()
            
            results.hands_played += 1
            results.total_wagered += self.base_bet
            
            if net_win > 0:
                results.total_won += net_win
            else:
                results.total_lost += abs(net_win)
                
            results.blackjacks += metrics['blackjack']
            results.wins += metrics['win']
            results.losses += metrics['loss']
            results.pushes += metrics['push']
            results.surrenders += metrics['surrender']
            results.doubles += metrics['double']
            results.splits += metrics['split']
            
            bankroll_history.append(self.game.player.bankroll - self.initial_bankroll)
            
        results.bankroll_history = bankroll_history
        results.std_deviation = statistics.stdev(bankroll_history)
        
        return results

    def _combine_simulation_results(self, results: List[SimulationResult]) -> SimulationResult:
        """Combine results from multiple simulation batches"""
        combined = SimulationResult(
            hands_played=sum(r.hands_played for r in results),
            total_wagered=sum(r.total_wagered for r in results),
            total_won=sum(r.total_won for r in results),
            total_lost=sum(r.total_lost for r in results),
            blackjacks=sum(r.blackjacks for r in results),
            wins=sum(r.wins for r in results),
            losses=sum(r.losses for r in results),
            pushes=sum(r.pushes for r in results),
            surrenders=sum(r.surrenders for r in results),
            doubles=sum(r.doubles for r in results),
            splits=sum(r.splits for r in results),
            house_edge=0,  # Will be calculated later
            std_deviation=0,  # Will be calculated later
            bankroll_history=[]  # Will combine all histories
        )
        
        # Combine bankroll histories
        all_values = []
        for result in results:
            all_values.extend(result.bankroll_history)
        combined.bankroll_history = all_values
        combined.std_deviation = statistics.stdev(all_values)
        
        return combined

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
