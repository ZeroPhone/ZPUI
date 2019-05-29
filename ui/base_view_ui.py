from threading import Event

from helpers import setup_logger
from utils import to_be_foreground

logger = setup_logger(__name__, "warning")

global_config = {}

# Documentation building process has problems with this import
try:
    import ui.config_manager as config_manager
except (ImportError, AttributeError):
    pass
else:
    cm = config_manager.get_ui_config_manager()
    cm.set_path("ui/configs")
    try:
        global_config = cm.get_global_config()
    except OSError as e:
        logger.error("Config files not available, running under ReadTheDocs?")
        logger.exception(e)


class BaseViewMixin(object):

    config_key = None
    default_pixel_view = None
    default_char_view = None
    view_mixin = None

    def __init__(self, **kwargs):
        config = kwargs.pop("config", None)
        self.config = config if config is not None else global_config
        self.set_view(self.config.get(self.config_key, {}))
        self.inhibit_refresh = Event()

    def set_views_dict(self):
        self.views = self.generate_views_dict()
        self.add_view_mixin()

    def generate_views_dict(self):
        raise NotImplementedError

    def add_view_mixin(self):
        if self.view_mixin:
            class_name = self.__class__.__name__
            for view_name, view_class in self.views.items():
                if view_class.use_mixin:
                    name = "{}-{}".format(view_name, class_name)
                    logger.debug("Subclassing {} into {}".format(view_name, name))
                    self.views[view_name] = type(name, (self.view_mixin, view_class), {})

    def set_view(self, config):
        view = None
        kwargs = {}
        self.set_views_dict()
        if self.name in config.get("custom_views", {}).keys():
            view_config = config["custom_views"][self.name]
            if isinstance(view_config, basestring):
                if view_config not in self.views:
                    logger.warning('Unknown view "{}" given for UI element "{}"!'.format(view_config, self.name))
                else:
                    view = self.views[view_config]
            elif isinstance(view_config, dict):
                raise NotImplementedError
                # This is the part where fine-tuning views will be possible,
                # once passing kwargs is implemented, that is
            else:
                logger.error(
                    "Custom view description can only be a string or a dictionary; is {}!".format(type(view_config)))
        elif not view and "default" in config:
            view_config = config["default"]
            if isinstance(view_config, basestring):
                if view_config not in self.views:
                    logger.warning('Unknown view "{}" given for UI element "{}"!'.format(view_config, self.name))
                else:
                    view = self.views[view_config]
            elif isinstance(view_config, dict):
                raise NotImplementedError  # Again, this is for fine-tuning
        elif not view:
            view = self.get_default_view()
        self.view = self.create_view_object(view, **kwargs)

    def create_view_object(self, view, **kwargs):
        return view(self.o, self, **kwargs)

    def get_default_view(self):
        """
        Decides on the view to use for UI element when the supplied config
        has no information on it.
        """
        if self.default_pixel_view and "b&w-pixel" in self.o.type:
            return self.views[self.default_pixel_view]
        elif self.default_char_view and "char" in self.o.type:
            return self.views[self.default_char_view]
        else:
            raise ValueError("Unsupported display type: {}".format(repr(self.o.type)))

    def add_view_wrapper(self, wrapper):
        """
        A function that allows overlays to set view wrappers,
        allowing them to modify the on-screen image.
        """
        self.view.wrappers.append(wrapper)

    @to_be_foreground
    def refresh(self):
        if self.inhibit_refresh.isSet():
            return False
        self.view.refresh()
        return True


class BaseView(object):

    def __init__(self, o, el):
        self.o = o
        self.el = el
        self.wrappers = []

    def execute_wrappers(self, data):
        """
        For all the defined wrappers, passes the data to be displayed
        (whether it's text or an image) through them.
        """
        for wrapper in self.wrappers:
            data = wrapper(data)
        return data

    def get_displayed_image(self):
        """ Needs to be implemented by child views. """
        raise NotImplementedError

    def graphical_refresh(self):
        """
        A very cookie-cutter graphical refresh for a view,
        might not even need to be redefined.
        """
        image = self.get_displayed_image()
        image = self.execute_wrappers(image)
        self.o.display_image(image)

    def get_cursor_pos(self):
        """
        A helper function to get cursor coordinates - if anything other than None
        is returned, the cursor will be drawn in the character view.
        """
        return None

    def character_refresh(self):
        """
        A very cookie-cutter char display refresh for a view,
        might not even need to be redefined. Draws the cursor
        if ``self.get_cursor_pos()`` returns anything other than ``None``.
        """
        data = self.get_displayed_data()
        data = self.execute_wrappers(data)
        cursor_pos = self.get_cursor_pos()
        if cursor_pos is not None:
            self.o.noCursor()
            self.o.setCursor(*cursor_pos)
        self.o.display_data(*data)
        if cursor_pos is not None:
            self.o.cursor()

    def refresh(self):
        return self.graphical_refresh()
