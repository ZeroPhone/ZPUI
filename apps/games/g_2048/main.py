from threading import Event, Lock
from time import sleep

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import DialogBox, ffs, Canvas
from zpui_lib.helpers import ExitHelper, local_path_gen

from logic import GameOf2048


class GameApp(ZeroApp):
    game = None
    do_exit = None
    is_processing = None
    menu_name = "2048"

    font = ("Mukta-SemiBold.ttf", 12)

    def on_start(self):
        self.digit_sizes = {}
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
        """
        # some matrices for testing:
        # matrix with many easy wins
        self.game.set_matrix([ \
          [1024, 512, 256, 128], \
          [   8,  16,  32,  64], \
          [   4,   2,   2,   0], \
          [   0,   0,   0,   0]  \
        ])
        # matrix with 2048 as next move
        self.game.set_matrix([ \
          [1024, 1024,  0,   0], \
          [   0,   0,   0,   0], \
          [   0,   0,   0,   0], \
          [   0,   0,   0,   0], \
        ])
        # matrix going from text width 4 to text width 5
        self.game.set_matrix([ \
          [8192, 8192,  0,   0], \
          [   0,   0,   0,   0], \
          [   0,   0,   0,   0], \
          [   0,   0,   0,   0], \
        ])
        """
        # Let's launch the main loop
        while not self.do_exit.is_set():
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
        while self.game.get_game_state() == 'not over' and not self.do_exit.is_set():
            sleep(1)
        if self.do_exit.is_set():
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

    def display_field_char(self, field):
        # character display code
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

    def get_field_image(self, field):
        c = Canvas(self.o)
        # drawing grid
        num_cells = 4
        font = self.font
        box_dim_base = int(min(c.width, c.height)*0.9)
        # center placement x, center placement y
        # so, top left corner of the box
        cpx, cpy = c.center_box(box_dim_base, box_dim_base, *c.size)
        c.rectangle_wh((cpx, cpy, box_dim_base, box_dim_base), )
        cell_size = box_dim_base // num_cells
        coords_x = [cpx]
        coords_y = [cpy]
        for i in range(num_cells-1):
            pos = cell_size*(i+1) # offset for the bar
            coords_x.append(cpx+pos)
            coords_y.append(cpy+pos)
            c.line((cpx+pos, cpy, cpx+pos, cpy+box_dim_base)) # -
            c.line((cpx, cpy+pos, cpx+box_dim_base, cpy+pos)) # |
        for i, field_row in enumerate(field):
            for j, digit in enumerate(field_row):
                digit_font = font
                digit_str = str(digit)
                digit_len = len(digit_str)
                start_font_size = cell_size
                y_offset = 0; x_offset = 0
                while digit_len not in self.digit_sizes:
                    # calculating font size for this specific number length for this specific screen resolution
                    try_font = (font[0], start_font_size)
                    # left offset, top offset, width, height
                    sl, st, sw, sh = c.get_text_bounds_compensated(digit_str, font=try_font)
                    #print(cell_size, start_font_size, sl, st, sw, sh)
                    if sw-sl < cell_size and sh-st < cell_size:
                        x_offset = (cell_size - sw) // 2 - sl
                        y_offset = (cell_size - sh) // 2 - st
                        #print(sh, st, y_offset)
                        # success, it fits
                        self.digit_sizes[digit_len] = (start_font_size, x_offset, y_offset)
                        #print(self.digit_sizes)
                        break
                    else:
                        # decreasing font and trying again
                        start_font_size = int(start_font_size * 0.95)
                        if start_font_size < 12: # getting too small
                            digit_font = None
                            break
                if digit_font != None:
                    font_size, x_offset, y_offset = self.digit_sizes[digit_len]
                    digit_font = (font[0], font_size)
                c.text(digit_str, (coords_x[j]+x_offset, coords_y[i]+y_offset), font=digit_font)
                #print(j, i, coords_x[j], coords_y[i], digit)
        game_state = self.game.get_game_state()
        state_str = {"win": "You won!",
                     "lose": "You lost!",
                     "not over": ""}[game_state]
        font = (self.font[0], 24)
        if game_state == "lose":
            sl, st, sw, sh = c.get_text_bounds_compensated(state_str, font=font)
            sx, sy = c.center_box(sw, sh)
            c.clear((sx, sy, sw, sh))
            c.centered_text(state_str, font=font)
        elif game_state == "win":
            sl, st, sw, sh = c.get_text_bounds_compensated(state_str, font=font)
            sx, sy = c.center_box(sw, sh)
            c.clear((sx, sy, sx+sw, sy+sh))
            c.centered_text(state_str, font=font)
        return c.get_image()

    def refresh(self):
        if self.o.width < 240 or self.o.height < 240:
            # character display code
            displayed_field = self.display_field_char(self.game.get_field())
            self.o.display_data(*displayed_field)
        else: # big screen, go wild!
            image = self.get_field_image(self.game.get_field())
            self.o.display_image(image)

    def write_score(self):
        # overwrite score file if current score is higher than the previous highscore
        # the previous highscore is determined in on_start()
        if self.game.score > self.prev_score:
            with open(self.local_path("score.txt"), "w") as f:
                    f.write(str(self.game.score))
                    self.prev_score = self.game.score
