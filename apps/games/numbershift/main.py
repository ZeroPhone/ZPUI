from threading import Event, Lock
from time import sleep
from copy import copy
import random

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import DialogBox, ffs, Canvas
from zpui_lib.helpers import ExitHelper, local_path_gen, get_platform, flatten

"""
This code is heavily inherited from the 2048 game UI.
So, if anything's unclear, that might be why. I apologize in advance.
"""

class GameApp(ZeroApp):
    game = None
    do_exit = None
    is_processing = None
    menu_name = "Number shift"

    font = ("Mukta-SemiBold.ttf", 12)

    def init_app(self):
        self.db = DialogBox("ync", self.i, self.o, message="Exit the game?")
        # placeholder db to make code work better

    def on_start(self):
        self.digit_sizes = {}
        self.local_path = local_path_gen(__name__)
        """ # TODO: actually implement scoring
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
        """

        self.do_exit = Event()
        self.moving = Lock()
        if self.game is None:
            # No game started yet, starting
            self.start_new_game()
        elif self.game["state"] == 'lose':
            start_new = DialogBox("ync", self.i, self.o, message="Last game lost, start new?").activate()
            if start_new is None:
                return  # Picked cancel, exiting the app
            elif start_new is True:
                self.start_new_game()
        # By now, the `game` property should have a game
        """
        # test field one move away from a win
        self.game["field"] = [1, 2, 3, 4,  5, 6, 7, 8,  9, 10, 11, 0,  13, 14, 15, 12]
        self.game["pointer"] = [3, 2]
        """
        # Let's launch the main loop
        while not self.do_exit.is_set():
            self.game_loop()

    def start_new_game(self):
        self.game = {"score":0, "state":"not over"}
        self.field_size = 4
        self.generate_field()
        x = self.game["field"].index(0) % 4
        y = self.game["field"].index(0) // 4
        self.game["pointer"] = [x, y]
        #print(self.game)

    def generate_field(self):
        field = list(range(self.field_size**2))
        while self.check_win(field=field):
            #print("shuffle")
            random.shuffle(field)
        self.game["field"] = field

    def check_win(self, field=None):
        if field == None:
            field = self.game["field"]
        field = copy(field) # sorting the field without 0, since it can be in the middle of the sequence
        field.remove(0)
        #print(field)
        # field has to be sorted (not including empty space) to win
        return sorted(field) == field

    def set_keymap(self):
        #if self.db.is_active:
        #    return # working around a bug
        left = lambda: self.make_a_move("left")
        right = lambda: self.make_a_move("right")
        up = lambda: self.make_a_move("up")
        down = lambda: self.make_a_move("down")
        enter = self.confirm_exit
        keymap = {"KEY_LEFT": left,
                  "KEY_RIGHT": right,
                  "KEY_UP": up,
                  "KEY_DOWN": down,
                  "KEY_ENTER": enter}
        if "beepy" in get_platform() or "emulator" in get_platform():
            # extra keys on keyboard
            keymap["KEY_E"] = up
            keymap["KEY_S"] = left
            keymap["KEY_F"] = right
            keymap["KEY_D"] = enter
            keymap["KEY_X"] = down
        self.i.stop_listen()
        self.i.set_keymap(keymap)
        self.i.listen()

    def confirm_exit(self):
        with self.moving:
            if self.game["state"] == 'not over':
                choices = ["n", ["Restart", "restart"], "y"]
            else:
                choices = ["y", ["Restart", "restart"], "n"]
            self.db = DialogBox(choices, self.i, self.o, message="Exit the game?")
            choice = self.db.activate()
            if choice == "restart":
                #self.write_score()  # write score if user restarts
                self.start_new_game()
                self.set_keymap()
                self.refresh()
            elif choice is True:
                #self.write_score()  # write score if user exits
                self.do_exit.set()
            else:
                self.set_keymap()
                self.refresh()

    def make_a_move(self, direction):
        if self.game["state"] == "win":
            # game is finished, nothing to do
            return
        with self.moving:
            assert (direction in ["up", "down", "left", "right"])
            x, y = self.game["pointer"]
            pos = y*self.field_size+x
            #print(self.game["field"])
            #print(pos)
            if direction == "up":
                if y == self.field_size-1: return
                self.game["field"][pos] = self.game["field"][pos+self.field_size]
                y += 1; self.game["pointer"][1] = y
                pos = y*self.field_size+x
                self.game["field"][pos] = 0
            if direction == "down":
                if y == 0: return
                self.game["field"][pos] = self.game["field"][pos-self.field_size]
                y -= 1; self.game["pointer"][1] = y
                pos = y*self.field_size+x
                self.game["field"][pos] = 0
            if direction == "left":
                if x == self.field_size-1: return
                self.game["field"][pos] = self.game["field"][pos+1]
                x += 1; self.game["pointer"][0] = x
                pos += 1
                self.game["field"][pos] = 0
            if direction == "right":
                if x == 0: return
                self.game["field"][pos] = self.game["field"][pos-1]
                x -= 1; self.game["pointer"][0] = x
                pos -= 1
                self.game["field"][pos] = 0
            #print(pos)
            #print(self.game["field"])
            if self.check_win():
                self.game["state"] = "win"
            self.refresh()

    def game_loop(self):
        self.do_exit.clear()
        self.set_keymap()
        self.refresh()
        #print("game loops", self.game, self.do_exit.is_set())
        while self.game["state"] == 'not over' and not self.do_exit.is_set():
            sleep(1)
        #print("game loop2", self.game, self.do_exit.is_set())
        if self.do_exit.is_set():
        #    self.write_score()
            return
        # Waiting for player to click any of five primary keys
        # Then, prompting to restart the game
        eh = ExitHelper(self.i, keys=self.i.reserved_keys).start()
        while eh.do_run():
            sleep(0.1)
        self.db = DialogBox("ync", self.i, self.o, message="Restart the game?")
        do_restart = self.db.activate()
        if do_restart is None:  # Cancel, leaving the playing field as-is
            return
        elif do_restart is False:  # No, not restarting, thus exiting the game
            #self.write_score()  # write score if user exits
            self.do_exit.set()
        else:
            #self.write_score()  # write score if user restarts
            self.start_new_game()  # Yes, restarting (game_loop will be entered once more from on_start() )

    def display_field_char(self, field):
        # character display code
        display_data = []
        assert len(field) == 4, "Can't display a field that's not 4x4!"
        assert len(field[0]) == 4, "Can't display a field that's not 4x4!"
        #print(field)
        space_for_each_number = self.o.cols // len(field[0])
        for field_row in field:
            field_row_str = [str(i) if i else "." for i in field_row]
            display_row = "".join(str(i).center(space_for_each_number) for i in field_row_str)
            display_data.append(display_row.ljust(self.o.cols))
            display_data.append("" * self.o.cols)
        # Replacing the center row with the game state, if applicable
        game_state = self.game["state"]
        state_str = {"win": "You won!",
                     "lose": "You lost!",
                     "not over": ""}[game_state]
        display_data[3] = state_str.center(self.o.cols)
        # Footer - score
        #display_data[7] = str(str(self.game["score"]) + " - " + str(self.prev_score)).center(self.o.cols)
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
                if digit == 0: continue # do not display the zero
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
        game_state = self.game["state"]
        state_str = {"win": "You won!",
                     "lose": "You lost!",
                     "not over": ""}[game_state]
        font = (self.font[0], 24)
        if game_state in ["lose", "win"]:
            sl, st, sw, sh = c.get_text_bounds_compensated(state_str, font=font)
            sx, sy = c.center_box(sw, sh)
            c.clear((sx, sy, sx+sw, sy+sh))
            c.centered_text(state_str, font=font)
        return c.get_image()

    def refresh(self):
        field = self.game["field"]
        field = [field[(i*self.field_size):][:self.field_size] for i in range(self.field_size)]
        if self.o.width < 240 or self.o.height < 240:
            # character display code
            displayed_field = self.display_field_char(field)
            self.o.display_data(*displayed_field)
        else: # big screen, go wild!
            image = self.get_field_image(field)
            self.o.display_image(image)

    """
    def write_score(self):
        # overwrite score file if current score is higher than the previous highscore
        # the previous highscore is determined in on_start()
        if self.game["score"] > self.prev_score:
            with open(self.local_path("score.txt"), "w") as f:
                    f.write(str(self.game["score"]))
                    self.prev_score = self.game["score"]
    """
