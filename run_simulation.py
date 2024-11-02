from blackjack import Blackjack, BlackjackRules  # Our previous blackjack implementation
from basic_strategy import BasicStrategy, Action  # Our previous basic strategy implementation
from blackjack_simulator import BlackjackSimulator, print_simulation_results

def run_blackjack_simulation(hands: int = 100000, bankroll: float = 100000.0):
    """
    Run a blackjack simulation with basic strategy.
    
    Args:
        hands: Number of hands to simulate
        bankroll: Starting bankroll
    """
    # Initialize rules
    rules = BlackjackRules(
        deck_penetration=0.80,
        max_splits=3,
        allow_resplit_aces=False,
        allow_double_after_split=True,
        allow_surrender=True,
        early_surrender=True,
        insurance_offered=True,
        even_money_offered=True,
        min_bet=10.0,
        max_bet=500.0,
        number_of_decks=6,
        blackjack_payout=1.5
    )
    
    # Initialize game, strategy and simulator
    game = Blackjack("Simulator", bankroll, rules)
    strategy = BasicStrategy()
    simulator = BlackjackSimulator(game, strategy, initial_bankroll=bankroll)
    
    print(f"Starting simulation of {hands:,} hands...")
    print(f"Initial bankroll: ${bankroll:,.2f}")
    print("Using basic strategy with standard casino rules")
    print("\nSimulating...")
    
    # Run simulation with single process
    results = simulator.run_simulation(num_hands=hands, processes=1)
    
    # Print results
    print_simulation_results(results)

if __name__ == "__main__":
    # Run a simulation with single process
    run_blackjack_simulation(hands=100000, bankroll=100000.0)
