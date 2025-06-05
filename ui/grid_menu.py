from time import sleep
from math import ceil
from copy import copy

from ui.base_list_ui import SixteenPtView
from ui.menu import Menu
from ui.entry import Entry
from ui.canvas import Canvas, MockOutput, replace_color, swap_colors
from ui.utils import fit_image_to_dims

from PIL import Image

class GridMenu(Menu):

    cols = 3
    rows = 3
    font = None
    config_key = "grid_menu"

    def __init__(self, contents, i, o, name=None, font = None, **kwargs):

        self.font = font
        Menu.__init__(self, contents, i, o, name=name, override_left=False, scrolling=False, **kwargs)
        self.rows = self.view.rows
        self.cols = self.view.cols

    def get_views_dict(self):
        views = {k:v for k, v in Menu.get_views_dict(self).items()}
        new = {
            "GridView": GridView,
            "BebbleGridView": BebbleGridView,
        }
        views.update(new)
        return views

    def get_default_view(self):
        """Decides on the view to use for UI element when config file has
        no information on it."""
        if "b&w" in self.o.type:
            # typical displays
            #if self.o.width:
            if self.o.width <= 240:
                view = self.views["GridView"]
                view.entry_width = 32
                return view
            else:
                return self.views["BebbleGridView"]
        elif "char" in self.o.type:
            return self.views["TextView"]
        else:
            raise ValueError("Unsupported display type: {}".format(repr(self.o.type)))

    def generate_keymap(self):
        keymap = Menu.generate_keymap(self)
        keymap.update({
            "KEY_RIGHT": "move_down",
            "KEY_LEFT": "move_up",
            "KEY_UP": "grid_move_up",
            "KEY_DOWN": "grid_move_down",
            "KEY_ENTER": "select_entry",
        })
        if self.exitable:
            keymap.update({"KEY_F1": "deactivate"})
        return keymap

    def grid_move_up(self):
        Menu.page_up(self, counter=self.cols)

    def grid_move_down(self):
        Menu.page_down(self, counter=self.cols)

    def add_view_wrapper(self, wrapper):
        self.view.wrappers.append(wrapper)


#class GridViewMixin(SixteenPtView):
class GridView(SixteenPtView):
    draw_lines = False # feels like a fugly option lol
    entry_width = None
    fde_increment = 3
    wrappers = []
    font = None
    shows_label = False # helps apply the label mixin dynamically

    def get_entry_count_per_screen(self):
        return self.el.cols*self.el.rows

    def calculate_params(self):
        self.rows = 3
        self.fde_increment = 1 # just following the bebblegridview findings honestly
        self.cols = 3
        self.sidebar_fits = True

    def draw_grid(self):
        contents = self.el.get_displayed_contents()
        pointer = self.el.pointer
        full_entries_shown = self.get_entry_count_per_screen()
        entries_shown = min(len(contents), full_entries_shown)
        disp_entry_positions = list(range(self.first_displayed_entry, self.first_displayed_entry+entries_shown))
        for i in copy(disp_entry_positions):
            if i not in range(len(contents)):
                disp_entry_positions.remove(i)

        c = Canvas(self.o)

        # Calculate margins
        step_width = c.width // self.el.cols if not self.entry_width else self.entry_width
        step_height = c.height // self.el.rows

        # Create a special canvas for drawing text - making sure it's cropped
        text_c = Canvas(MockOutput(step_width, step_height, o=self.o))

        # Calculate grid index
        item_x = (pointer-self.first_displayed_entry)%self.el.cols
        item_y = (pointer-self.first_displayed_entry)//self.el.rows

        # Draw horizontal and vertical lines
        if self.draw_lines:
            for x in range(1, self.el.cols):
                c.line((x*step_width, 0, x*step_width, c.height))
            for y in range(1, self.el.rows):
                c.line((0, y*step_height, c.width, y*step_height))

        # Draw the app names
        for i, index in enumerate(disp_entry_positions):
            entry = contents[index]
            icon = None
            text = None
            if isinstance(entry, Entry):
                text = entry.text
                if entry.icon:
                    icon = entry.icon
            else:
                text = entry[0]
            if icon:
                coords = ((i%self.el.cols)*step_width, (i//self.el.rows)*step_height)
                c.image.paste(icon, coords)
            else:
                text_c.clear()
                text_bounds = c.get_text_bounds(text, font=self.el.font)
                x_cord = (i%self.el.cols)*step_width #+(step_width-text_bounds[0])/2
                y_cord = (i//self.el.rows)*step_height+(step_height-text_bounds[1])//2
                text_c.text(text, (0, 0), font=self.el.font)
                c.image.paste(text_c.image, (x_cord, y_cord))

        # Invert the selected cell
        selected_x = (item_x)*step_width
        selected_y = (item_y)*step_height
        c.invert_rect((selected_x, selected_y, selected_x+step_width, selected_y+step_height))

        return c.get_image()

    def refresh(self):
        # The following code is a dirty hack to fix navigation
        # because I need to make base_list_ui code better
        # at dealing with stuff like this. or maybe make GridViewMixin's
        # own version of fix_pointers_on_refresh?
        underflow = False
        # Moving up, this might happen - clamping FDE
        if self.first_displayed_entry > self.el.pointer:
            self.first_displayed_entry = self.el.pointer
            underflow = True
        self.fix_pointers_on_refresh()
        if self.first_displayed_entry:
            # Making sure FDE is divisible by the grid width
            div, mod = divmod(self.first_displayed_entry, self.el.cols)
            self.first_displayed_entry = div*self.el.cols
            # If we're not moving up
            if mod and not underflow:
                self.first_displayed_entry += self.el.cols
        image = self.draw_grid()
        for wrapper in self.wrappers:
            image = wrapper(image)
        self.o.display_image(image)


class BebbleGridView(GridView):
    MuktaBold = "Mukta-Bold.ttf"
    MuktaSemiBold = "Mukta-SemiBold.ttf"
    MuktaRegular = "Mukta-Regular.ttf"
    font_size = 12
    entry_width = 100
    dim = 50
    between_row = 5 # between-row gap
    bar_height = 30 # status bar
    # 720x720 test for the meme, and it does work!
    #font_size = 27
    #entry_width = 220
    #dim = 110
    # 480x320 test
    #font_size = 16
    #entry_width = 140
    #dim = 70
    shows_label = True # helps apply the label mixin dynamically

    def calculate_params(self):
        # width is at least 240
        self.cols = self.o.width // self.entry_width
        self.rows = (self.o.height-self.bar_height)//self.entry_width
        self.fde_increment = 1 # because uhhhhh it glitches out if I do 4? weird lol maybe this needs to be `1` always
        self.sidebar_fits = False

    def process_contents(self, contents):
        # Create a special canvas for drawing icons
        c = Canvas(MockOutput(height=self.entry_width, width=self.entry_width, o=self.o))

        self.rendered_entries = [[], []]
        for entry in contents:
            if getattr(entry, "icon", None):
                if entry.icon.size[0] < self.dim or entry.icon.size[1] < self.dim:
                    icon = fit_image_to_dims(entry.icon, self.dim, self.dim, resampling=Image.BOX, fill_color=c.background_color)
                    if c.default_color != "white": # default color has been changed
                        color = c.default_color
                        icon = replace_color(icon, "white", color).convert(self.o.device_mode)
                    # probably assign icons to an internal list instead?
                    entry.icon = icon

        # pre-rendering icons
        for entry in contents:
            # fetching/calculating parameters
            icon = None
            inverted_icon = None
            if isinstance(entry, Entry):
                text = entry.text
                if entry.icon:
                    icon = entry.icon
                    if hasattr(entry, "inverted_icon"):
                        inverted_icon = entry.inverted_icon
            else:
                text = entry[0]
            # now actually rendering
            for i in range(2):
                selected = bool(i)
                # set app block colors based on whether the app is selected
                bg_color = c.background_color if selected else c.default_color
                text_color = c.default_color if selected else c.background_color
                fg_color = text_color
                if icon and inverted_icon:
                    # both inverted and non-inverted icons are present
                    icon = inverted_icon if selected else icon

                app_x = 0
                app_y = 0

                # draw border
                c.rectangle((app_x, app_y, app_x+self.entry_width, app_y+self.entry_width), fill=c.background_color, outline=c.background_color)

                # draw background
                c.rectangle( \
                    ( \
                        app_x + self.between_row, \
                        app_y + self.between_row, \
                        app_x + (self.entry_width-self.between_row), \
                        app_y + (self.entry_width-self.between_row) \
                    ), \
                    fill=bg_color, outline=c.background_color)
                # get text size so we can center text
                #text_size = measure_text_ex(res.MuktaSemiBold, entry.get("name"), self.font_size, 0).x
                font_size = int(self.font_size*1.25) if selected else self.font_size
                font = c.decypher_font_reference((self.MuktaSemiBold, font_size))
                _, _, text_size, _ = c.draw.textbbox((0, 0), text, font=font)

                # draw app name
                c.text(
                    text,
                    (app_x + int((self.entry_width - text_size) // 2), app_y + int(self.entry_width*0.72)),
                    font=(self.MuktaSemiBold, font_size), fill=text_color
                )

                # draw icon
                if icon:
                    if inverted_icon: # inverted icon present
                        # the icon's already how we want it, no need to swap color
                        c.paste(icon, (app_x + int(0.25*self.entry_width), app_y + int(0.15*self.entry_width) ))
                    else:
                        do_invert = not selected
                        used_icon = icon
                        if do_invert:
                            used_icon = swap_colors(icon, c.default_color, c.background_color, c.background_color, c.default_color)
                            used_icon = used_icon.convert(self.o.device_mode)
                        c.paste(used_icon, (app_x + int(0.25*self.entry_width), app_y + int(0.15*self.entry_width) )) # need to tell to invert it

                # icon rendered: storing it
                from copy import copy
                self.rendered_entries[i].append(copy(c.get_image().convert(self.o.device_mode)))
                c.clear()

        return contents

    def draw_grid(self):
        contents = self.el.get_displayed_contents()
        pointer = self.el.pointer
        full_entries_shown = self.get_entry_count_per_screen()
        entries_shown = min(len(contents), full_entries_shown)
        disp_entry_positions = list(range(self.first_displayed_entry, self.first_displayed_entry+entries_shown))
        for i in copy(disp_entry_positions):
            if i not in range(len(contents)):
                disp_entry_positions.remove(i)

        c = Canvas(self.o)

        # status bar text placeholder
        c.text("Status bar will go here", (25, 4), font=(self.MuktaSemiBold, 12))
        # menu background fill (with default color)
        c.rectangle((0, self.bar_height, c.width, c.height), fill=c.default_color)

        for i, index in enumerate(disp_entry_positions):
            selected = pointer == index
            entry = contents[index]
            ## TODO: Make all of this math for figure out the app x and y actually make sense. Also pagenate
            ## TODO todo: yeah that's a real todo moment I agree :sob:
            #for i in range(rows):
            x_offset = (self.o.width - (self.entry_width*self.cols) + self.between_row*(self.cols-1) )//2
            row = i // self.cols
            col = i % self.cols
            app_x = (col * self.entry_width) + x_offset - self.between_row * col
            app_y = self.bar_height+7 + (self.entry_width-5)*row

            # now, simply pasting pre-rendered entries. so so very fast!!
            c.paste(self.rendered_entries[1 if selected else 0][index], (app_x, app_y))

        return c.get_image()
