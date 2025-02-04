"""Test for the ui element DatePicker"""
import os, unittest

from mock import patch, Mock

try:
	from ui import DatePicker
except ImportError:
	print("Absolute imports failed, trying relative imports")
	os.sys.path.append(os.path.dirname(os.path.abspath('.')))
	# Store original __import__
	orig_import = __import__

	def import_mock(name, *args):
		if name in ['helpers']:
			return Mock()
		elif name == 'ui.utils':
			import utils
			return utils
		return orig_import(name, *args)

	with patch('__builtin__.__import__', side_effect=import_mock):
		from date_picker import DatePicker

def get_mock_input():
	return Mock()

def get_mock_output(width=128, height=64, mode="1"):
    m = Mock()
    m.configure_mock(width=width, height=height, device_mode=mode, type=["b&w"])
    return m

dp_name = "Test DatePicker"

class TestDatePicker(unittest.TestCase):
	"""Tests DatePicker"""

	def test_constructor(self):
		"""Tests constructor"""
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)
		self.assertIsNotNone(dp)

	def test_keymap(self):
		"""Tests keymap"""
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)
		self.assertIsNotNone(dp)
		for key_name, callback in dp.keymap.items():
			self.assertIsNotNone(callback)

	# Test whether it returns None when deactivating it
	def test_left_key_returns_none(self):
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)
		dp.refresh = lambda *args, **kwargs: None

		# Checking at start
		def scenario():
			dp.deactivate()
			assert not dp.in_foreground

		with patch.object(dp, 'idle_loop', side_effect=scenario) as d:
			return_value = dp.activate()
		assert return_value is None

		# Chacking after moving a few cells
		def scenario():
			for i in range(3):
				dp.move_down()
				dp.move_right()
			dp.deactivate()
			assert not dp.in_foreground

		with patch.object(dp, 'idle_loop', side_effect=scenario) as d:
			return_value = dp.activate()
		assert return_value is None

	def test_accepts_and_returns_dict(self):
		date = {"year":2018, "month":2, "day":1}
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name, **date)
		dp.refresh = lambda *args, **kwargs: None

		def scenario():
			dp.accept_value()
			dp.deactivate()
			assert not dp.is_active

		with patch.object(dp, 'idle_loop', side_effect=scenario) as p:
			return_value = dp.activate()
		assert isinstance(return_value, dict)
		assert return_value == date

	def test_set_current_day(self):
		grid = [30,  31, -1, -1, -1, -1,  1,
			 2,   3,  4,  5,  6,  7,  8,
			 9,  10, 11, 12, 13, 14, 15,
			 16, 17, 18, 19, 20, 21, 22,
			 23, 24, 25, 26, 27, 28, 29]
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)
		dp.refresh = lambda *args, **kwargs: None
		dp._set_month_year(7, 2018)
		assert(dp.calendar_grid == grid)
		dp.set_current_day(1)
		assert(dp.selected_option == {"x":6, "y":0})

	def test_moving_right_left(self):
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)
		dp.refresh = lambda *args, **kwargs: None
		dp._set_month_year(7, 2018)
		dp.set_current_day(1)
		dp.move_right()
		assert(dp.get_current_day() == 2)
		assert(dp.selected_option == {"x":0, "y":1})
		dp.set_current_day(1)
		assert(dp.selected_option == {"x":6, "y":0})
		dp.move_left()
		assert(dp.current_month == 6)
		assert(dp.current_year == 2018)
		assert(dp.selected_option == {"x":5, "y":4})

	def test_moving_up_down(self):
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)
		dp.refresh = lambda *args, **kwargs: None
		dp._set_month_year(7, 2018)
		dp.set_current_day(1)
		dp.move_down()
		assert(dp.get_current_day() == 8)
		dp.move_up()
		assert(dp.get_current_day() == 1)

	def test_callback(self):
		cb1 = Mock()

		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name, callback=cb1)
		dp.refresh = lambda *args, **kwargs: None

		def scenario():
			dp.accept_value()
			cb1.assert_called_once()
			assert isinstance(cb1.call_args[0][0], dict)
			assert dp.is_active
			dp.deactivate()
			assert not dp.is_active

		with patch.object(dp, 'idle_loop', side_effect=scenario) as p:
			return_value = dp.activate()
		assert return_value is None

	def test_callback_with_return_strftime(self):
		cb1 = Mock()
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name, callback=cb1, return_strftime="%Y-%m-%d %H:%M:%S")
		dp.refresh = lambda *args, **kwargs: None

		def scenario():
			dp.accept_value()
			cb1.assert_called_once()
			assert isinstance(cb1.call_args[0][0], basestring)
			assert dp.is_active
			dp.deactivate()
			assert not dp.is_active

		with patch.object(dp, 'idle_loop', side_effect=scenario) as p:
			return_value = dp.activate()
		assert return_value is None

	def test_init_strftime(self):
		init_str = "2018-02-01"
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name, init_strftime=init_str)
		dp.refresh = lambda *args, **kwargs: None

		def scenario():
			dp.accept_value()
			dp.deactivate()
			assert not dp.is_active

		with patch.object(dp, 'idle_loop', side_effect=scenario) as p:
			return_value = dp.activate()
		assert isinstance(return_value, dict)
		assert return_value == {"year":2018, "month":2, "day":1}

	def test_redraw(self):
		dp = DatePicker(get_mock_input(), get_mock_output(), name=dp_name)

		def scenario():
			dp.deactivate()
			assert not dp.is_active

		with patch.object(dp, 'idle_loop', side_effect=scenario) as p:
			return_value = dp.activate()
		dp.o.display_image.assert_called_once()


if __name__ == '__main__':
	unittest.main()
