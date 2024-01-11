"""Test for the ui element TimePicker"""
import os, unittest

from mock import patch, Mock

try:
	from ui import TimePicker
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
		from time_picker import TimePicker

def get_mock_input():
	return Mock()

def get_mock_output(width=128, height=64, mode="1"):
    m = Mock()
    m.configure_mock(width=width, height=height, device_mode=mode, type=["b&w"])
    return m

tp_name = "Test TimePicker"

class TestDatePicker(unittest.TestCase):
	"""Tests TimePicker"""

	def test_constructor(self):
		"""Tests constructor"""
		tp = TimePicker(get_mock_input(), get_mock_output(), name=tp_name)
		self.assertIsNotNone(tp)

	def test_keymap(self):
		"""Tests keymap"""
		tp = TimePicker(get_mock_input(), get_mock_output(), name=tp_name)
		self.assertIsNotNone(tp)
		for key_name, callback in tp.keymap.items():
			self.assertIsNotNone(callback)

	# Test whether it returns None when deactivating it
	def test_left_key_returns_none(self):
		tp = TimePicker(get_mock_input(), get_mock_output(), name=tp_name)
		tp.refresh = lambda *args, **kwargs: None

		# Checking at start
		def scenario():
			tp.deactivate()
			assert not tp.in_foreground

		with patch.object(tp, 'idle_loop', side_effect=scenario) as t:
			return_value = tp.activate()
		assert return_value is None

		# Chechking after changing the numbers a little
		def scenario():
			for i in range(3):
				tp.decrease_one()
				tp.move_right()
				tp.increase_one()
			tp.deactivate()
			assert not tp.in_foreground

		with patch.object(tp, 'idle_loop', side_effect=scenario) as t:
			return_value = tp.activate()
		assert return_value is None

if __name__ == '__main__':
	unittest.main()
