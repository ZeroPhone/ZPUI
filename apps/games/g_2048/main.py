from threading import Event, Lock
from time import sleep

from apps import ZeroApp
from ui import DialogBox, ffs
from zpui_lib.helpers import ExitHelper, local_path_gen

from logic import GameOf2048


class GameApp(ZeroApp):
    game = None
    do_exit = None
    is_processing = None
    menu_name = "2048"

    def on_start(self):
        self.local_path = local_path_gen(__name__)
        try:
            with open(self.local_path("score.txt"), "r") as f:
                # read the highscore from score.txt (integer on first line)
                # if it doesn't exist, it's set to 0.
                prev_score = f.readline()
                if prev_score == '':
                    self.prev_score = 0
                else:
                    self.prev_score = int(prev_score)
        except IOError:
            with open(self.local_path("score.txt"), "w") as f:
                f.write('0')
                self.prev_score = 0

        self.do_exit = Event()
        self.moving = Lock()
        if self.game is None:
            # No game started yet, starting
            self.start_new_game()
        elif self.game.get_game_state() == 'lose':
            start_new = DialogBox("ync", self.i, self.o, message="Last game lost, start new?").activate()
            if start_new is None:
                return  # Picked cancel, exiting the app
            elif start_new is True:
                self.start_new_game()
        # By now, the `game` property should have a game
        # Let's launch the main loop
        while not self.do_exit.isSet():
            self.game_loop()

    def start_new_game(self):
        self.game = GameOf2048(4, 4)

    def set_keymap(self):
        keymap = {"KEY_LEFT": lambda: self.make_a_move("left"),
                  "KEY_RIGHT": lambda: self.make_a_move("right"),
                  "KEY_UP": lambda: self.make_a_move("up"),
                  "KEY_DOWN": lambda: self.make_a_move("down"),
                  "KEY_ENTER": self.confirm_exit}
        self.i.stop_listen()
        self.i.set_keymap(keymap)
        self.i.listen()

    def confirm_exit(self):
        with self.moving:
            if self.game.get_game_state() == 'not over':
                choices = ["n", ["Restart", "restart"], "y"]
            else:
                choices = ["y", ["Restart", "restart"], "n"]
            choice = DialogBox(choices, self.i, self.o, message="Exit the game?").activate()
            if choice == "restart":
                self.write_score()  # write score if user restarts
                self.start_new_game()
                self.set_keymap()
                self.refresh()
            elif choice is True:
                self.write_score()  # write score if user exits
                self.do_exit.set()
            else:
                self.set_keymap()
                self.refresh()

    def make_a_move(self, direction):
        with self.moving:
            assert (direction in ["up", "down", "left", "right"])
            getattr(self.game, direction)()
            self.refresh()

    def game_loop(self):
        self.set_keymap()
        self.refresh()
        while self.game.get_game_state() == 'not over' and not self.do_exit.isSet():
            sleep(1)
        if self.do_exit.isSet():
            self.write_score()

            return
        # Waiting for player to click any of five primary keys
        # Then, prompting to restart the game
        eh = ExitHelper(self.i, keys=self.i.reserved_keys).start()
        while eh.do_run():
            sleep(0.1)
        do_restart = DialogBox("ync", self.i, self.o, message="Restart the game?").activate()
        if do_restart is None:  # Cancel, leaving the playing field as-is
            return
        elif do_restart is False:  # No, not restarting, thus exiting the game
            self.write_score()  # write score if user exits
            self.do_exit.set()
        else:
            self.write_score()  # write score if user restarts
            self.start_new_game()  # Yes, restarting (game_loop will be entered once more from on_start() )

    def display_field(self, field):
        assert len(field) == 4, "Can't display a field that's not 4x4!"
        assert len(field[0]) == 4, "Can't display a field that's not 4x4!"
        display_data = []
        space_for_each_number = self.o.cols // len(field[0])
        for field_row in field:
            field_row_str = [str(i) if i else "." for i in field_row]
            display_row = "".join(str(i).center(space_for_each_number) for i in field_row_str)
            display_data.append(display_row.ljust(self.o.cols))
            display_data.append("" * self.o.cols)
        # Replacing the center row with the game state, if applicable
        game_state = self.game.get_game_state()
        state_str = {"win": "You won!",
                     "lose": "You lost!",
                     "not over": ""}[game_state]
        display_data[3] = state_str.center(self.o.cols)
        # Footer - score
        display_data[7] = str(str(self.game.score) + " - " + str(self.prev_score)).center(self.o.cols)
        return display_data

    def refresh(self):
        displayed_field = self.display_field(self.game.get_field())
        self.o.display_data(*displayed_field)

    def write_score(self):
        # overwrite score file if current score is higher than the previous highscore
        # the previous highscore is determined in on_start()
        if self.game.score > self.prev_score:
            with open(self.local_path("score.txt"), "w") as f:
                    f.write(str(self.game.score))
                    self.prev_score = self.game.score
