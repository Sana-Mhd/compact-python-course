
from __future__ import annotations
 
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
 
Position = tuple[int, int]
 
 
 
# ========================================================================
# Pieces
# ========================================================================
 
WHITE = "white"
BLACK = "black"
 
ALL_DIRECTIONS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
 
 
class Checker(ABC):
    """One checker on the board."""
 
    def __init__(self, color: str) -> None:
        if color not in (WHITE, BLACK):
            raise ValueError(f"unknown colour: {color!r}")
        self.color = color
 
    # --- what the board asks every piece -------------------------------
 
    @abstractmethod
    def move_directions(self) -> tuple[tuple[int, int], ...]:
        """Diagonals this piece may travel along for a quiet move."""
 
    def capture_directions(self) -> tuple[tuple[int, int], ...]:
        """Diagonals this piece may capture along.  All four by default."""
        return ALL_DIRECTIONS
 
    @abstractmethod
    def reach(self, board) -> int:
        """How many squares this piece may travel in one direction."""
 
    @property
    @abstractmethod
    def symbol(self) -> str:
        """Single character used when the board prints itself."""
 
    # --- helpers --------------------------------------------------------
 
    @property
    def forward(self) -> int:
        """Row delta that counts as 'forward' for this colour.
 
        White sits at the bottom of the board and moves up (towards row 0),
        black sits at the top and moves down.
        """
        return -1 if self.color == WHITE else 1
 
    @property
    def is_king(self) -> bool:
        return isinstance(self, King)
 
    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"{type(self).__name__}({self.color})"
 
 
class Man(Checker):
    """An ordinary checker: one step forward, captures in every direction."""
 
    def move_directions(self) -> tuple[tuple[int, int], ...]:
        return ((self.forward, -1), (self.forward, 1))
 
    def reach(self, board) -> int:
        return 1
 
    @property
    def symbol(self) -> str:
        return "w" if self.color == WHITE else "b"
 
 
class King(Checker):
    """A promoted checker.
 
    On a board with flying kings it slides any distance along a diagonal;
    otherwise it behaves like a man that may also move backwards.
    """
 
    def move_directions(self) -> tuple[tuple[int, int], ...]:
        return ALL_DIRECTIONS
 
    def reach(self, board) -> int:
        return board.size if board.flying_kings else 1
 
    @property
    def symbol(self) -> str:
        return "W" if self.color == WHITE else "B"
 
# ========================================================================
# Board
# ========================================================================
 
@dataclass(frozen=True)
class Move:
    """A single move: where it starts, the squares it lands on, what it takes."""
 
    path: tuple[Position, ...]
    captured: tuple[Position, ...] = field(default_factory=tuple)
 
    @property
    def start(self) -> Position:
        return self.path[0]
 
    @property
    def end(self) -> Position:
        return self.path[-1]
 
    @property
    def is_capture(self) -> bool:
        return bool(self.captured)
 
 
class Board:
    """Abstract base board."""
 
    size: int = 0
    rows_of_pieces: int = 0
    flying_kings: bool = False
    name: str = "board"
 
    def __init__(self) -> None:
        if type(self) is Board:
            raise TypeError("Board is abstract - use StandardBoard or InternationalBoard")
        self.squares: list[list[Checker | None]] = [
            [None] * self.size for _ in range(self.size)
        ]
        self.setup()
 
    # --- construction ---------------------------------------------------
 
    def setup(self) -> None:
        """Put both armies on their starting squares."""
        for row in range(self.rows_of_pieces):
            for col in range(self.size):
                if self.is_dark((row, col)):
                    self.squares[row][col] = Man(BLACK)
 
        for row in range(self.size - self.rows_of_pieces, self.size):
            for col in range(self.size):
                if self.is_dark((row, col)):
                    self.squares[row][col] = Man(WHITE)
 
    # --- small queries --------------------------------------------------
 
    def in_bounds(self, pos: Position) -> bool:
        row, col = pos
        return 0 <= row < self.size and 0 <= col < self.size
 
    @staticmethod
    def is_dark(pos: Position) -> bool:
        """Checkers is played on the dark squares only."""
        row, col = pos
        return (row + col) % 2 == 1
 
    def piece_at(self, pos: Position) -> Checker | None:
        if not self.in_bounds(pos):
            return None
        return self.squares[pos[0]][pos[1]]
 
    def pieces_of(self, color: str) -> list[tuple[Position, Checker]]:
        found = []
        for row in range(self.size):
            for col in range(self.size):
                piece = self.squares[row][col]
                if piece is not None and piece.color == color:
                    found.append(((row, col), piece))
        return found
 
    def count(self, color: str) -> int:
        return len(self.pieces_of(color))
 
    def promotion_row(self, color: str) -> int:
        return 0 if color == WHITE else self.size - 1
 
    # --- move generation -------------------------------------------------
 
    def legal_moves(self, color: str) -> list[Move]:
        """Every move `color` may play.
 
        Capturing is compulsory: if any capture exists, the quiet moves are
        dropped.
        """
        captures: list[Move] = []
        quiet: list[Move] = []
 
        for pos, piece in self.pieces_of(color):
            captures.extend(self._capture_moves(pos, piece))
            quiet.extend(self._quiet_moves(pos, piece))
 
        return captures if captures else quiet
 
    def _quiet_moves(self, pos: Position, piece: Checker) -> list[Move]:
        moves: list[Move] = []
        for d_row, d_col in piece.move_directions():
            for step in range(1, piece.reach(self) + 1):
                target = (pos[0] + d_row * step, pos[1] + d_col * step)
                if not self.in_bounds(target) or self.piece_at(target) is not None:
                    break
                moves.append(Move(path=(pos, target)))
        return moves
 
    def _capture_moves(self, pos: Position, piece: Checker) -> list[Move]:
        """All capture sequences, including chains of several jumps."""
        results: list[Move] = []
        self._extend_captures(pos, piece, (pos,), (), results)
        return results
 
    def _extend_captures(
        self,
        pos: Position,
        piece: Checker,
        path: tuple[Position, ...],
        taken: tuple[Position, ...],
        out: list[Move],
    ) -> None:
        found_any = False
 
        for d_row, d_col in piece.capture_directions():
            victim = self._first_piece_along(pos, (d_row, d_col), piece.reach(self), taken)
            if victim is None:
                continue
 
            victim_pos, victim_piece = victim
            if victim_piece.color == piece.color or victim_pos in taken:
                continue
 
            landing_steps = self.size if piece.reach(self) > 1 else 1
            for step in range(1, landing_steps + 1):
                landing = (victim_pos[0] + d_row * step, victim_pos[1] + d_col * step)
                if not self.in_bounds(landing):
                    break
                occupant = self.piece_at(landing)
                if occupant is not None and landing != path[0]:
                    break
                found_any = True
                self._extend_captures(
                    landing, piece, path + (landing,), taken + (victim_pos,), out
                )
 
        if not found_any and taken:
            out.append(Move(path=path, captured=taken))
 
    def _first_piece_along(
        self,
        pos: Position,
        direction: tuple[int, int],
        reach: int,
        taken: tuple[Position, ...],
    ) -> tuple[Position, Checker] | None:
        """Walk one diagonal and return the first piece that blocks it."""
        d_row, d_col = direction
        for step in range(1, reach + 1):
            square = (pos[0] + d_row * step, pos[1] + d_col * step)
            if not self.in_bounds(square):
                return None
            piece = self.piece_at(square)
            if piece is not None and square not in taken:
                return square, piece
        return None
 
    # --- playing a move ---------------------------------------------------
 
    def apply(self, move: Move) -> bool:
        """Play `move` on the board.  Returns True if the piece was promoted."""
        piece = self.piece_at(move.start)
        if piece is None:
            raise ValueError(f"no piece on {move.start}")
 
        self.squares[move.start[0]][move.start[1]] = None
        for row, col in move.captured:
            self.squares[row][col] = None
 
        promoted = False
        if not piece.is_king and move.end[0] == self.promotion_row(piece.color):
            piece = King(piece.color)
            promoted = True
 
        self.squares[move.end[0]][move.end[1]] = piece
        return promoted
 
    # --- notation and printing ---------------------------------------------
 
    def to_notation(self, pos: Position) -> str:
        row, col = pos
        return f"{chr(ord('a') + col)}{self.size - row}"
 
    def from_notation(self, text: str) -> Position:
        text = text.strip().lower()
        if len(text) < 2:
            raise ValueError(f"cannot read square {text!r}")
        col = ord(text[0]) - ord("a")
        try:
            row = self.size - int(text[1:])
        except ValueError as exc:
            raise ValueError(f"cannot read square {text!r}") from exc
        if not self.in_bounds((row, col)):
            raise ValueError(f"square {text!r} is outside the board")
        return row, col
 
    def render(self) -> str:
        files = "   " + " ".join(chr(ord("a") + c) for c in range(self.size))
        lines = [files]
        for row in range(self.size):
            cells = []
            for col in range(self.size):
                piece = self.squares[row][col]
                if piece is not None:
                    cells.append(piece.symbol)
                elif self.is_dark((row, col)):
                    cells.append(".")
                else:
                    cells.append(" ")
            number = self.size - row
            lines.append(f"{number:>2} " + " ".join(cells) + f" {number:<2}")
        lines.append(files)
        return "\n".join(lines)
 
    def __str__(self) -> str:
        return self.render()
 
 
class StandardBoard(Board):
    """8x8 English draughts: twelve pieces a side, kings move one square."""
 
    size = 8
    rows_of_pieces = 3
    flying_kings = False
    name = "Standard 8x8"
 
 
class InternationalBoard(Board):
    """10x10 international draughts: twenty pieces a side, flying kings."""
 
    size = 10
    rows_of_pieces = 4
    flying_kings = True
    name = "International 10x10"
 
 
BOARD_TYPES = {"1": StandardBoard, "2": InternationalBoard}
 
# ========================================================================
# Player
# ========================================================================
 
class Player:
    """One of the two people at the board.
 
    Keeps the information the assignment asks for: name, colour of the
    checkers, how many moves were made, how long the player was at the board
    and the final result.
    """
 
    def __init__(self, name: str, color: str) -> None:
        self.name = name.strip() or f"Player {color}"
        self.color = color
        self.moves = 0
        self.captures = 0
        self.result: str = "not finished"
        self.thinking_time = 0.0
        self._turn_started: float | None = None
 
    # --- bookkeeping ----------------------------------------------------
 
    def start_turn(self) -> None:
        self._turn_started = time.monotonic()
 
    def end_turn(self, captured: int = 0) -> None:
        if self._turn_started is not None:
            self.thinking_time += time.monotonic() - self._turn_started
            self._turn_started = None
        self.moves += 1
        self.captures += captured
 
    @property
    def average_time(self) -> float:
        return self.thinking_time / self.moves if self.moves else 0.0
 
    def status(self) -> str:
        return (
            f"{self.name} ({self.color}) - moves: {self.moves}, "
            f"captures: {self.captures}, time: {self.thinking_time:.1f}s"
        )
 
    def __str__(self) -> str:
        return f"{self.name} ({self.color})"
 
# ========================================================================
# Game
# ========================================================================
 
class Game:
    """One game of checkers between two players."""
 
    def __init__(self, white: Player, black: Player, board: Board | None = None) -> None:
        self.board = board if board is not None else StandardBoard()
        self.white = white
        self.black = black
        self.players = {WHITE: white, BLACK: black}
        self.turn = WHITE
        self.moves = 0
        self.history: list[str] = []
        self.started_at = time.monotonic()
        self.finished_at: float | None = None
        self.winner: Player | None = None
        self.ending = "in progress"
 
    # --- state ------------------------------------------------------------
 
    @property
    def current_player(self) -> Player:
        return self.players[self.turn]
 
    @property
    def opponent(self) -> Player:
        return self.players[BLACK if self.turn == WHITE else WHITE]
 
    @property
    def duration(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.monotonic()
        return end - self.started_at
 
    @property
    def is_over(self) -> bool:
        return self.finished_at is not None
 
    def legal_moves(self) -> list[Move]:
        return self.board.legal_moves(self.turn)
 
    # --- playing -----------------------------------------------------------
 
    def play(self, move: Move) -> str:
        """Apply one move, record it and hand the turn over."""
        player = self.current_player
        promoted = self.board.apply(move)
 
        squares = " - ".join(self.board.to_notation(p) for p in move.path)
        note = squares
        if move.is_capture:
            note += f"  (captures {len(move.captured)})"
        if promoted:
            note += "  (promoted to king)"
 
        self.moves += 1
        player.end_turn(captured=len(move.captured))
        self.history.append(f"{self.moves:>3}. {player.name}: {note}")
 
        self.turn = BLACK if self.turn == WHITE else WHITE
        return note
 
    def check_end(self) -> bool:
        """Finish the game if the side to move has lost."""
        if self.board.count(self.turn) == 0:
            self.finish(winner=self.opponent, ending="all checkers captured")
            return True
        if not self.board.legal_moves(self.turn):
            self.finish(winner=self.opponent, ending="no legal moves left")
            return True
        return False
 
    def finish(self, winner: Player | None, ending: str) -> None:
        self.finished_at = time.monotonic()
        self.winner = winner
        self.ending = ending
        for player in (self.white, self.black):
            if winner is None:
                player.result = "draw"
            else:
                player.result = "won" if player is winner else "lost"
 
    # --- reporting ----------------------------------------------------------
 
    def summary(self) -> str:
        lines = [
            "",
            "=" * 56,
            "GAME OVER",
            "=" * 56,
            f"Board          : {self.board.name}",
            f"Reason         : {self.ending}",
            f"Result         : "
            + (f"{self.winner.name} ({self.winner.color}) wins" if self.winner else "draw"),
            f"Total moves    : {self.moves}",
            f"Total time     : {self.duration:.1f}s",
            "",
            "Players",
            "-" * 56,
        ]
        for player in (self.white, self.black):
            lines.append(f"  {player.status()}")
            lines.append(
                f"    result: {player.result}, "
                f"checkers left: {self.board.count(player.color)}, "
                f"average per move: {player.average_time:.1f}s"
            )
        lines += ["", "Move history", "-" * 56]
        lines += self.history or ["  (no moves were played)"]
        lines.append("=" * 56)
        return "\n".join(lines)
 
# ========================================================================
# Console interface
# ========================================================================
 
def ask(prompt: str, default: str = "") -> str:
    try:
        answer = input(prompt).strip()
    except EOFError:
        return default
    return answer or default
 
 
def choose_board() -> Board:
    print("Which board would you like to play on?")
    for key, board_type in BOARD_TYPES.items():
        print(f"  {key}) {board_type.name}")
    choice = ask("Your choice [1]: ", "1")
    board_type = BOARD_TYPES.get(choice, StandardBoard)
    return board_type()
 
 
def describe_moves(board: Board, moves: list[Move]) -> str:
    return ", ".join(
        " - ".join(board.to_notation(square) for square in move.path) for move in moves
    )
 
 
def parse_move(board: Board, text: str, moves: list[Move]) -> Move | None:
    """Turn something like 'c3-d4' into one of the legal moves."""
    cleaned = text.lower().replace("-", " ").replace(",", " ").replace("x", " ")
    parts = [part for part in cleaned.split() if part]
    if len(parts) < 2:
        print("  Please write a move as two squares, for example c3-d4.")
        return None
 
    try:
        squares = tuple(board.from_notation(part) for part in parts)
    except ValueError as exc:
        print(f"  {exc}")
        return None
 
    exact = [move for move in moves if move.path == squares]
    if exact:
        return exact[0]
 
    matching = [
        move for move in moves if move.start == squares[0] and move.end == squares[-1]
    ]
    if len(matching) == 1:
        return matching[0]
    if len(matching) > 1:
        print("  That start and finish can be reached in more than one way.")
        print(f"  Write the whole path, for example: {describe_moves(board, matching)}")
        return None
 
    print("  That is not a legal move here.")
    return None
 
 
def show_turn(game: Game) -> None:
    player = game.current_player
    print()
    print(game.board.render())
    print()
    print(f"Move {game.moves + 1}  |  {player.status()}")
    print(
        f"Checkers on the board - white: {game.board.count(WHITE)}, "
        f"black: {game.board.count(BLACK)}"
    )
 
 
def play() -> None:
    print("=" * 56)
    print("CHECKERS - two players, one keyboard")
    print("=" * 56)
 
    board = choose_board()
    white = Player(ask("Name of the WHITE player [Player 1]: ", "Player 1"), WHITE)
    black = Player(ask("Name of the BLACK player [Player 2]: ", "Player 2"), BLACK)
    game = Game(white, black, board)
 
    print()
    print(f"{white.name} plays white (w) and moves first.")
    print(f"{black.name} plays black (b).")
    print("Capital letters are kings.  Capturing is compulsory.")
    print("Write a move as two squares, for example c3-d4.")
    print("Type 'q' at any time to finish the game.")
 
    while not game.is_over:
        if game.check_end():
            break
 
        show_turn(game)
        moves = game.legal_moves()
        player = game.current_player
 
        if any(move.is_capture for move in moves):
            print("  You have a capture available and must take it.")
 
        player.start_turn()
        while True:
            answer = ask(
                f"{player.name}, enter your move or 'q' to finish ('?' lists moves): ", "q"
            )
            if answer.lower() in ("q", "quit", "finish", "stop"):
                game.finish(winner=game.opponent, ending=f"{player.name} finished the game")
                break
            if answer == "?":
                print(f"  Legal moves: {describe_moves(board, moves)}")
                continue
 
            move = parse_move(board, answer, moves)
            if move is not None:
                note = game.play(move)
                print(f"  {player.name} played {note}")
                break
 
    print(game.summary())
 
 
if __name__ == "__main__":
    play()
 
