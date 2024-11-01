from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict
import random
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameResult(Enum):
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"
    SURRENDER = "surrender"
    BLACKJACK = "blackjack"

class RoundState(Enum):
    NOT_STARTED = auto()
    INITIAL_DEAL = auto()
    PLAYER_TURN = auto()
    DEALER_TURN = auto()
    COMPLETE = auto()

class GameError(Exception):
    """Custom exception for game-related errors"""
    pass

@dataclass
class GameEvent:
    timestamp: datetime
    action: str
    hand_index: int
    result: Optional[str] = None
    amount: Optional[float] = None
    dealer_card: Optional[str] = None
    player_cards: Optional[str] = None

@dataclass
class RoundResult:
    hand_results: List[Tuple[GameResult, float]]
    total_win_loss: float
    insurance_result: Optional[float]
    dealer_hand: str
    player_hands: List[str]
    round_events: List[GameEvent]

@dataclass
class BlackjackRules:
    deck_penetration: float = 0.80
    max_splits: int = 3
    allow_resplit_aces: bool = False
    allow_double_after_split: bool = True
    allow_surrender: bool = True
    early_surrender: bool = True
    insurance_offered: bool = True
    even_money_offered: bool = True
    min_bet: float = 10.0
    max_bet: float = 500.0
    number_of_decks: int = 6
    blackjack_payout: float = 1.5  # 3:2 payout
    insurance_payout: float = 2.0  # 2:1 payout

@dataclass
class WagerStats:
    original_wagers: float = 0.0
    additional_wagers: float = 0.0  # Splits, doubles, insurance
    insurance_wagers: float = 0.0
    
    @property
    def total_wagered(self) -> float:
        return self.original_wagers + self.additional_wagers + self.insurance_wagers

@dataclass
class GameStatistics:
    hands_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    hands_pushed: int = 0
    hands_surrendered: int = 0
    blackjacks: int = 0
    splits: int = 0
    doubles: int = 0
    insurances_taken: int = 0
    insurances_won: int = 0
    total_won: float = 0.0
    total_lost: float = 0.0
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    wagers: WagerStats = field(default_factory=WagerStats)
    session_start: datetime = field(default_factory=datetime.now)
    total_time_played: float = 0.0

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        
    def __str__(self):
        return f"{self.rank}{self.suit}"
        
    def get_value(self) -> int:
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == 'A':
            return 11
        return int(self.rank)

class Deck:
    def __init__(self, rules: BlackjackRules):
        self.rules = rules
        self.cards: List[Card] = []
        self.discard_pile: List[Card] = []
        self.reset()
        
    def reset(self):
        self.cards.clear()
        self.discard_pile.clear()
        suits = ['♠', '♣', '♥', '♦']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [Card(suit, rank) for _ in range(self.rules.number_of_decks) 
                     for suit in suits for rank in ranks]
        random.shuffle(self.cards)
        logger.info(f"Deck reshuffled. {len(self.cards)} cards in play.")
        
    def draw(self) -> Optional[Card]:
        if not self.cards:
            total_cards = len(self.cards) + len(self.discard_pile)
            if len(self.discard_pile) < total_cards * (1 - self.rules.deck_penetration):
                self.reset()
            else:
                return None
        card = self.cards.pop()
        self.discard_pile.append(card)
        return card
    
    def cards_remaining(self) -> int:
        return len(self.cards)

class Hand:
    def __init__(self):
        self.cards: List[Card] = []
        self.bet = 0
        self.is_split = False
        self.is_doubled = False
        self.is_surrendered = False
        self.original_bet = 0
        self.split_from_aces = False
        self.insurance_bet = 0
        self.took_even_money = False
        self.moves: List[GameEvent] = []
        
    def add_card(self, card: Card) -> bool:
        if self.is_done():
            return False
        self.cards.append(card)
        self.moves.append(GameEvent(
            timestamp=datetime.now(),
            action="hit",
            hand_index=0,
            result=str(self.get_value()[0]),
            player_cards=str(self)
        ))
        return True
        
    def get_value(self) -> Tuple[int, bool]:
        # Calculate value of non-ace cards first
        non_ace_value = sum(card.get_value() for card in self.cards if card.rank != 'A')
        aces = sum(1 for card in self.cards if card.rank == 'A')
        
        # Start with all aces = 1
        value = non_ace_value + aces
        
        # Try to use one ace as 11 if it wouldn't bust
        if aces > 0 and value + 10 <= 21:
            value += 10
            
        return value, self.is_blackjack()
    
    def is_blackjack(self) -> bool:
        # Only original non-split hands can have blackjack
        return (len(self.cards) == 2 and 
                self.get_value()[0] == 21 and 
                not self.is_split and
                not self.took_even_money)
    
    def is_busted(self) -> bool:
        return self.get_value()[0] > 21
    
    def is_done(self) -> bool:
        return (self.is_busted() or 
                self.is_blackjack() or 
                self.is_surrendered or 
                self.took_even_money or
                (self.is_doubled and len(self.cards) > 2) or
                (self.split_from_aces and len(self.cards) > 1))
    
    def is_soft(self) -> bool:
        non_ace_value = sum(card.get_value() for card in self.cards if card.rank != 'A')
        aces = sum(1 for card in self.cards if card.rank == 'A')
        
        # A hand is soft if we can count an ace as 11 without busting
        return aces > 0 and (non_ace_value + aces - 1 + 11) <= 21
    
    def can_split(self, rules: BlackjackRules) -> bool:
        if not (len(self.cards) == 2 and 
                self.cards[0].rank == self.cards[1].rank and 
                not self.is_doubled and
                not self.is_surrendered):
            return False
        
        # Handle ace splits based on rules
        if self.cards[0].rank == 'A':
            return not self.is_split or rules.allow_resplit_aces
            
        return True
    
    def can_double(self, rules: BlackjackRules) -> bool:
        return (len(self.cards) == 2 and 
                not self.is_doubled and
                not self.is_surrendered and
                (not self.is_split or rules.allow_double_after_split))
    
    def can_surrender(self, rules: BlackjackRules) -> bool:
        return (rules.allow_surrender and
                len(self.cards) == 2 and 
                not self.is_split and 
                not self.is_doubled and 
                not self.is_surrendered)
    
    def can_take_even_money(self, rules: BlackjackRules, dealer_upcard: Card) -> bool:
        return (rules.even_money_offered and
                self.is_blackjack() and
                dealer_upcard.rank == 'A' and
                not self.took_even_money)
    
    def get_status(self) -> str:
        value, is_blackjack = self.get_value()
        status = []
        if self.is_surrendered:
            status.append("SURRENDERED")
        elif self.is_busted():
            status.append("BUSTED")
        elif is_blackjack:
            status.append("BLACKJACK")
        elif self.took_even_money:
            status.append("EVEN MONEY")
        elif self.is_done():
            status.append(f"FINAL: {value}")
        else:
            status.append(f"Current: {value}")
        
        if self.is_split:
            status.append("(Split)")
        if self.is_doubled:
            status.append("(Doubled)")
        if self.split_from_aces:
            status.append("(Split Aces)")
        if self.insurance_bet > 0:
            status.append("(Insured)")
        
        return " ".join(status)
    
    def __str__(self):
        return f"{' '.join(str(card) for card in self.cards)} - {self.get_status()}"

class Player:
    def __init__(self, name: str, bankroll: float = 1000.0):
        self.name = name
        self.bankroll = bankroll
        self.hands: List[Hand] = [Hand()]
        self.stats = GameStatistics()
        self.round_events: List[GameEvent] = []
        
    def place_bet(self, amount: float) -> bool:
        if not self._validate_bet(amount):
            return False
            
        self.bankroll -= amount
        self.hands[0].bet = amount
        self.hands[0].original_bet = amount
        self.stats.wagers.original_wagers += amount
        
        self.round_events.append(GameEvent(
            timestamp=datetime.now(),
            action="bet",
            hand_index=0,
            amount=amount
        ))
        return True
    
    def _validate_bet(self, amount: float) -> bool:
        return (amount > 0 and 
                amount == round(amount, 2) and
                amount <= self.bankroll)
    
    def reset_hands(self):
        self.hands = [Hand()]
        self.round_events = []
    
    def get_win_percentage(self) -> float:
        total = self.stats.hands_played - self.stats.hands_surrendered
        return (self.stats.hands_won / total * 100 
                if total > 0 else 0)
    
    def update_stats(self, result: GameResult, amount: float, hand: Hand):
        net_win = amount - hand.original_bet if amount > 0 else -hand.original_bet
        
        if result == GameResult.WIN:
            self.stats.hands_won += 1
            self.stats.total_won += net_win
            self.stats.biggest_win = max(self.stats.biggest_win, net_win)
        elif result == GameResult.LOSE:
            self.stats.hands_lost += 1
            self.stats.total_lost += hand.original_bet
            self.stats.biggest_loss = max(self.stats.biggest_loss, hand.original_bet)
        elif result == GameResult.BLACKJACK:
            self.stats.hands_won += 1
            self.stats.blackjacks += 1
            self.stats.total_won += net_win
            self.stats.biggest_win = max(self.stats.biggest_win, net_win)
        elif result == GameResult.SURRENDER:
            self.stats.hands_surrendered += 1
            self.stats.total_lost += hand.original_bet * 0.5
        elif result == GameResult.PUSH:
            self.stats.hands_pushed += 1
        
        self.round_events.append(GameEvent(
            timestamp=datetime.now(),
            action="result",
            hand_index=self.hands.index(hand),
            result=result.value,
            amount=amount,
            player_cards=str(hand)
        ))
        
        self.stats.hands_played += 1
        
    def get_performance_metrics(self) -> Dict:
        elapsed_time = (datetime.now() - self.stats.session_start).total_seconds()
        self.stats.total_time_played = elapsed_time
        
        return {
            "hands_per_hour": self.stats.hands_played / elapsed_time * 3600 if elapsed_time > 0 else 0,
            "win_rate": self.get_win_percentage(),
            "avg_bet": self.stats.wagers.original_wagers / self.stats.hands_played if self.stats.hands_played > 0 else 0,
            "net_profit_loss": self.stats.total_won - self.stats.total_lost,
            "house_edge": ((self.stats.total_lost - self.stats.total_won) / 
                          self.stats.wagers.total_wagered if self.stats.wagers.total_wagered > 0 else 0)
        }

def validate_game_state(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.deck.cards and not self.deck.discard_pile:
            raise GameError("No cards available")
        if self.player.bankroll <= 0:
            raise GameError("Player has no funds")
        if f.__name__ == 'start_round':
            # Allow start_round to be called regardless of current state
            return f(self, *args, **kwargs)
        if self.round_state == RoundState.NOT_STARTED and f.__name__ not in ['play_round', 'start_round']:
            raise GameError("Round hasn't started")
        if self.round_state == RoundState.COMPLETE and f.__name__ not in ['play_round', 'start_round']:
            raise GameError("Round is complete")
        return f(self, *args, **kwargs)
    return wrapper

class Blackjack:
    def __init__(self, player_name: str, initial_bankroll: float = 1000.0, rules: Optional[BlackjackRules] = None):
        self.rules = rules or BlackjackRules()
        self.deck = Deck(self.rules)
        self.player = Player(player_name, initial_bankroll)
        self.dealer_hand = Hand()
        self.round_state = RoundState.NOT_STARTED
        
    @validate_game_state
    def start_round(self, bet_amount: float) -> bool:
        """Start a round by placing bet and dealing initial cards"""
        # Validate bet and round state
        if self.round_state != RoundState.NOT_STARTED:
            raise GameError("Previous round not complete")
            
        if bet_amount < self.rules.min_bet or bet_amount > self.rules.max_bet:
            raise GameError(f"Bet must be between ${self.rules.min_bet:.2f} and ${self.rules.max_bet:.2f}")
        
        if bet_amount != round(bet_amount, 2):
            raise GameError("Bet must be in valid currency units (dollars and cents)")
            
        # Place bet and deal cards
        if not self.player.place_bet(bet_amount):
            raise GameError("Insufficient funds for bet")
            
        if not self.deal_initial_cards():
            return False
            
        self.round_state = RoundState.PLAYER_TURN
        return True

    def deal_initial_cards(self) -> bool:
        """Deal initial cards, return False if insufficient cards"""
        self.player.reset_hands()
        self.dealer_hand = Hand()
        
        # Deal cards alternately
        for _ in range(2):
            player_card = self.deck.draw()
            dealer_card = self.deck.draw()
            if not player_card or not dealer_card:
                return False
                
            self.player.hands[0].add_card(player_card)
            self.dealer_hand.add_card(dealer_card)
            
        self.round_state = RoundState.INITIAL_DEAL
        return True

    def get_dealer_upcard(self) -> Card:
        return self.dealer_hand.cards[0]

    @validate_game_state
    def hit(self, hand: Hand) -> bool:
        if hand.is_done():
            return False
            
        card = self.deck.draw()
        if not card:
            return False
            
        success = hand.add_card(card)
        if success:
            self.player.round_events.append(GameEvent(
                timestamp=datetime.now(),
                action="hit",
                hand_index=self.player.hands.index(hand),
                player_cards=str(hand),
                dealer_card=str(self.get_dealer_upcard())
            ))
        return success

    @validate_game_state
    def double_down(self, hand: Hand) -> bool:
        if not hand.can_double(self.rules) or self.player.bankroll < hand.bet:
            return False
            
        self.player.bankroll -= hand.bet
        hand.bet *= 2
        hand.is_doubled = True
        self.player.stats.doubles += 1
        self.player.stats.wagers.additional_wagers += hand.original_bet
        
        success = self.hit(hand)
        if success:
            self.player.round_events.append(GameEvent(
                timestamp=datetime.now(),
                action="double",
                hand_index=self.player.hands.index(hand),
                amount=hand.bet,
                player_cards=str(hand)
            ))
        return success

    @validate_game_state
    def split(self, hand_index: int) -> bool:
        if len(self.player.hands) >= self.rules.max_splits + 1:
            return False
            
        original_hand = self.player.hands[hand_index]
        if not original_hand.can_split(self.rules):
            return False
            
        if self.player.bankroll < original_hand.original_bet:
            return False
            
        # Create new hand with second card
        new_hand = Hand()
        new_hand.bet = original_hand.original_bet
        new_hand.original_bet = original_hand.original_bet
        new_hand.is_split = True
        new_hand.add_card(original_hand.cards.pop())
        
        # Handle split aces
        is_aces = original_hand.cards[0].rank == 'A'
        if is_aces:
            original_hand.split_from_aces = True
            new_hand.split_from_aces = True
            
        # Add new card to each hand
        original_hand.is_split = True
        card = self.deck.draw()
        if not card:
            return False
        original_hand.add_card(card)
        
        card = self.deck.draw()
        if not card:
            return False
        new_hand.add_card(card)
        
        self.player.hands.insert(hand_index + 1, new_hand)
        self.player.bankroll -= original_hand.bet
        self.player.stats.splits += 1
        self.player.stats.wagers.additional_wagers += original_hand.original_bet
        return True

    @validate_game_state
    def surrender(self, hand: Hand) -> Tuple[bool, float]:
        if not hand.can_surrender(self.rules):
            return False, 0
            
        hand.is_surrendered = True
        surrender_amount = hand.bet * 0.5
        self.player.bankroll += surrender_amount
        self.player.update_stats(GameResult.SURRENDER, surrender_amount, hand)
        return True, surrender_amount

    @validate_game_state
    def place_insurance(self, hand: Hand) -> bool:
        if not self.rules.insurance_offered or self.get_dealer_upcard().rank != 'A':
            return False
            
        insurance_amount = hand.original_bet * 0.5
        if self.player.bankroll < insurance_amount:
            return False
            
        self.player.bankroll -= insurance_amount
        hand.insurance_bet = insurance_amount
        self.player.stats.insurances_taken += 1
        self.player.stats.wagers.insurance_wagers += insurance_amount
        return True
        
    def handle_insurance_payout(self, hand: Hand) -> Optional[float]:
        """Handle insurance bet and return any payout"""
        if not hand.insurance_bet:
            return None
            
        if self.dealer_hand.is_blackjack():
            payout = hand.insurance_bet * (1 + self.rules.insurance_payout)  # Return bet plus 2:1 winnings
            self.player.bankroll += payout
            self.player.stats.insurances_won += 1
            return payout
        return 0
        
    @validate_game_state
    def take_even_money(self, hand: Hand) -> Tuple[bool, float]:
        """Handle even money option for blackjack against dealer ace"""
        if not hand.can_take_even_money(self.rules, self.get_dealer_upcard()):
            return False, 0
            
        # Even money pays 1:1 immediately
        hand.took_even_money = True
        payout = hand.bet * 2  # Original bet plus 1:1
        self.player.bankroll += payout
        self.player.update_stats(GameResult.WIN, payout, hand)
        return True, payout

    def play_dealer_hand(self) -> bool:
        """Play out dealer hand. Return False if insufficient cards."""
        self.round_state = RoundState.DEALER_TURN
        
        while True:
            value = self.dealer_hand.get_value()[0]
            is_soft = self.dealer_hand.is_soft()
            
            if value > 17:
                break
            if value == 17 and not is_soft:
                break
                
            card = self.deck.draw()
            if not card:
                return False
            self.dealer_hand.add_card(card)
            
        return True

    def resolve_hand(self, hand: Hand) -> Tuple[GameResult, float]:
        """Resolve a single hand and return result with payout amount"""
        if hand.is_surrendered:
            return GameResult.SURRENDER, hand.bet * 0.5
            
        player_value, player_blackjack = hand.get_value()
        dealer_value, dealer_blackjack = self.dealer_hand.get_value()
        
        # Handle busts
        if player_value > 21:
            return GameResult.LOSE, 0
        
        if dealer_value > 21:
            return GameResult.WIN, hand.bet * 2
            
        # Handle blackjacks - only original hands can have blackjack
        if player_blackjack and not hand.is_split and not dealer_blackjack:
            return GameResult.BLACKJACK, hand.bet * (1 + self.rules.blackjack_payout)
        if dealer_blackjack and not (player_blackjack and not hand.is_split):
            return GameResult.LOSE, 0
        if player_blackjack and dealer_blackjack and not hand.is_split:
            return GameResult.PUSH, hand.bet
            
        # Handle regular wins/losses/pushes
        if player_value > dealer_value:
            return GameResult.WIN, hand.bet * 2
        elif player_value < dealer_value:
            return GameResult.LOSE, 0
        else:
            return GameResult.PUSH, hand.bet

    def handle_dead_hand(self) -> RoundResult:
        """Handle situation when we run out of cards"""
        results = []
        total_win_loss = 0
        
        # Return all active bets
        for hand in self.player.hands:
            if not hand.is_done():
                self.player.bankroll += hand.bet
                results.append((GameResult.PUSH, hand.bet))
                self.player.update_stats(GameResult.PUSH, hand.bet, hand)
            else:
                result, amount = self.resolve_hand(hand)
                results.append((result, amount))
                self.player.bankroll += amount
                self.player.update_stats(result, amount, hand)
                total_win_loss += amount - hand.original_bet
                
        self.round_state = RoundState.COMPLETE
        return RoundResult(
            hand_results=results,
            total_win_loss=total_win_loss,
            insurance_result=None,
            dealer_hand=str(self.dealer_hand),
            player_hands=[str(hand) for hand in self.player.hands],
            round_events=self.player.round_events
        )

    @validate_game_state
    def finish_round(self) -> RoundResult:
        """Complete the round by playing dealer hand and resolving all hands"""
        results = []
        total_win_loss = 0
        
        # Play out dealer hand if necessary (skip if all player hands are busted/surrendered)
        all_hands_resolved = all(hand.is_done() for hand in self.player.hands)
        if not all_hands_resolved:
            dealer_cards_ok = self.play_dealer_hand()
            if not dealer_cards_ok:
                return self.handle_dead_hand()
                
        # Resolve all player hands
        for hand in self.player.hands:
            # Skip hands that took even money
            if hand.took_even_money:
                continue
                
            result, amount = self.resolve_hand(hand)
            results.append((result, amount))
            total_win_loss += amount - hand.original_bet
            self.player.bankroll += amount
            self.player.update_stats(result, amount, hand)
        
        self.round_state = RoundState.COMPLETE
        
        return RoundResult(
            hand_results=results,
            total_win_loss=total_win_loss,
            insurance_result=None,
            dealer_hand=str(self.dealer_hand),
            player_hands=[str(hand) for hand in self.player.hands],
            round_events=self.player.round_events
        )

    @validate_game_state
    def play_round(self, bet_amount: float) -> RoundResult:
        """Play a complete round (for non-simulation play)"""
        if not self.start_round(bet_amount):
            return self.handle_dead_hand()
            
        # Handle insurance first if applicable
        dealer_upcard = self.get_dealer_upcard()
        if (self.rules.insurance_offered and 
            dealer_upcard.rank == 'A' and 
            any(h.insurance_bet > 0 for h in self.player.hands)):
            
            for hand in self.player.hands:
                if hand.insurance_bet > 0:
                    self.handle_insurance_payout(hand)
        
        # Handle dealer blackjack
        if self.dealer_hand.is_blackjack():
            return self.finish_round()
            
        # At this point, player would normally make decisions
        # For automated play, we'll just resolve the hand
        return self.finish_round()

    def check_hand_done(self, hand: Hand) -> bool:
        """Check if a hand is finished and update game state if needed"""
        if hand.is_done():
            # Check if all hands are done
            if all(h.is_done() for h in self.player.hands):
                self.round_state = RoundState.DEALER_TURN
            return True
        return False

    def execute_move(self, move: str, hand_index: int) -> bool:
        """Execute a move for the given hand index"""
        if self.round_state != RoundState.PLAYER_TURN:
            return False
            
        hand = self.player.hands[hand_index]
        if hand.is_done():
            return False
            
        success = False
        if move == 'hit':
            success = self.hit(hand)
        elif move == 'stand':
            success = True  # Stand always succeeds
        elif move == 'double':
            success = self.double_down(hand)
        elif move == 'split':
            success = self.split(hand_index)
        elif move == 'surrender':
            success = bool(self.surrender(hand)[0])
        elif move == 'even_money':
            success = bool(self.take_even_money(hand)[0])
            
        if success:
            self.check_hand_done(hand)
            
        return success

    def get_valid_moves(self, hand: Hand) -> List[str]:
        """Get list of valid moves for the given hand"""
        if self.round_state != RoundState.PLAYER_TURN or hand.is_done():
            return []
            
        moves = ['hit', 'stand']
        
        # Handle blackjack options first
        if hand.is_blackjack():
            if (self.rules.even_money_offered and 
                self.get_dealer_upcard().rank == 'A' and
                not hand.took_even_money):
                return ['even_money', 'keep_blackjack']
            return []
            
        if hand.can_surrender(self.rules):
            moves.append('surrender')
            
        if hand.can_double(self.rules) and self.player.bankroll >= hand.bet:
            moves.append('double')
            
        if (hand.can_split(self.rules) and 
            self.player.bankroll >= hand.bet and 
            len(self.player.hands) < self.rules.max_splits + 1):
            moves.append('split')
            
        return moves

    def get_game_state(self) -> Dict:
        """Get current game state including statistics"""
        metrics = self.player.get_performance_metrics()
        
        return {
            'player_name': self.player.name,
            'bankroll': self.player.bankroll,
            'statistics': asdict(self.player.stats),
            'performance_metrics': metrics,
            'current_hand_number': self.player.stats.hands_played + 1,
            'cards_remaining': self.deck.cards_remaining(),
            'rules': asdict(self.rules),
            'round_state': self.round_state.name
        }

def format_currency(amount: float) -> str:
    return f"${amount:.2f}"

# Example usage and testing
if __name__ == "__main__":
    # Initialize game with custom rules
    rules = BlackjackRules(
        deck_penetration=0.80,
        max_splits=3,
        allow_resplit_aces=False,
        allow_surrender=True,
        early_surrender=True,
        even_money_offered=True
    )
    
    game = Blackjack("Player1", 1000.0, rules)
    
    try:
        # Example round with various scenarios
        result = game.play_round(25.0)
        
        print("\nInitial Round Results:")
        print(f"Dealer: {result.dealer_hand}")
        print("Player hands:")
        for hand in result.player_hands:
            print(f"  {hand}")
        
        if result.insurance_result is not None:
            print(f"Insurance result: {format_currency(result.insurance_result)}")
            
        print(f"Total win/loss: {format_currency(result.total_win_loss)}")
        
        # Get game state
        state = game.get_game_state()
        print("\nGame Statistics:")
        print(f"Hands played: {state['statistics']['hands_played']}")
        print(f"Win rate: {state['performance_metrics']['win_rate']:.1f}%")
        print(f"Current bankroll: {format_currency(state['bankroll'])}")
        print(f"Total wagered: {format_currency(state['statistics']['wagers']['total_wagered'])}")
        print(f"Net profit/loss: {format_currency(state['performance_metrics']['net_profit_loss'])}")
        
    except GameError as e:
        print(f"Error: {e}")
