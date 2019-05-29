"""tests for coords"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import Canvas, coords
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
        from canvas import Canvas
        import coords


def get_mock_output(width=128, height=64, mode="1"):
    m = Mock()
    m.configure_mock(width=width, height=height, device_mode=mode, type=["b&w-pixel"])
    return m


class TestCanvas(unittest.TestCase):
    """Tests the coords functions"""

    def test_coords_filtering(self):
        """tests whether the coordinate filtering works"""
        w = 128
        h = 64
        c = Canvas(get_mock_output(width=w, height=h))
        assert (coords.check_coordinates(c, (0, 1)) == (0, 1))
        assert (coords.check_coordinates(c, ("-2", "-3")) == (w-2, h-3))
        assert (coords.check_coordinates(c, (0, 1, 2, 3)) == (0, 1, 2, 3))
        assert (coords.check_coordinates(c, (0, 1, "-2", "-3")) == (0, 1, w-2, h-3))
        assert (coords.check_coordinates(c, ("-0", "-1", "-2", "-3")) == (w, h-1, w-2, h-3))
        assert (coords.check_coordinates(c, ("-0", "1", "-2", "-3")) == (w, h+1, w-2, h-3))

    def test_cflip(self):
        """ Tests convert_flat_list_into_pairs """
        cflip = coords.convert_flat_list_into_pairs
        assert cflip((1, 2, 3, 4)) == ((1, 2), (3, 4))
        assert cflip((1, 2, 3, 4, 5, 6)) == ((1, 2), (3, 4), (5, 6))
        assert cflip((1, 2, 3, 4, 5)) == ((1, 2), (3, 4))

    def test_get_bounds_for_points(self):
        """ Tests convert_flat_list_into_pairs """
        gbfp = coords.get_bounds_for_points
        assert gbfp(((1, 2), (3, 4), (5, 6))) == (5, 5)
        assert gbfp(((1, 2), (3, 4))) == (3, 3)

    def test_expand_coords(self):
        """ Tests expand_coords """
        ec = coords.expand_coords
        assert ec((1, 2, 3, 4), 1) == (0, 1, 4, 5)
        assert ec((0, 10, 20, 30), 1) == (-1, 9, 21, 31)

    def test_multiply_points(self):
        """ Tests multiply_points """
        mp = coords.multiply_points
        assert mp(((1, 2), (3, 4)), 1) == ((1, 2), (3, 4))
        assert mp(((1, 2), (3, 4)), 2) == ((2, 4), (6, 8))
        assert mp(((1, 2), (3, 4)), 2.5) == ((2, 5), (7, 10))

    def test_offset_points(self):
        """ Tests offset_points """
        op = coords.offset_points
        assert op(((1, 2), (3, 4)), (10, 10)) == ((11, 12), (13, 14))
        assert op(((1, 2), (3, 4)), (10, 20)) == ((11, 22), (13, 24))
        assert op(((1, 2), (3, 4)), (20, 20)) == ((21, 22), (23, 24))


if __name__ == '__main__':
    unittest.main()
