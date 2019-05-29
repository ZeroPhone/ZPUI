from ui.utils import is_sequence_not_string as issequence

def check_coordinates(canvas, coords, check_count=True):
    # type: tuple -> tuple
    """
    A helper function to check and reformat coordinates supplied to
    functions. Currently, accepts integer coordinates, as well as strings
    - denoting offsets from opposite sides of the screen.
    """
    # Checking for string offset coordinates
    # First, we need to make coords into a mutable sequence - thus, a list
    coords = list(coords)
    for i, c in enumerate(coords):
        sign = "+"
        if isinstance(c, basestring):
            if c.startswith("-"):
                sign = "-"
                c = c[1:]
            assert c.isdigit(), "A numeric string expected, received: {}".format(coords[i])
            offset = int(c)
            dim = canvas.size[i % 2]
            if sign == "+":
                coords[i] = dim + offset
            elif sign == "-":
                coords[i] = dim - offset
        elif isinstance(c, float):
            logger.warning("Received {} as a coordinate - pixel offsets can't be float, converting to int".format(c))
            coords[i] = int(c)
    # Restoring the status-quo
    coords = tuple(coords)
    # Now all the coordinates should be integers - if something slipped by the checks,
    # it's of type we don't process and we should raise an exception now
    for c in coords:
        assert isinstance(c, int), "{} not an integer or 'x' string!".format(c)
    if len(coords) == 2:
        return coords
    elif len(coords) == 4:
        x1, y1, x2, y2 = coords
        # Not sure those checks make sense
        #assert (x2 >= x1), "x2 ({}) is smaller than x1 ({}), rearrange?".format(x2, x1)
        #assert (y2 >= y1), "y2 ({}) is smaller than y1 ({}), rearrange?".format(y2, y1)
        return coords
    else:
        if check_count:
            raise ValueError("Invalid number of coordinates!")
        else:
            return coords

def check_coordinate_pairs(canvas, coord_pairs):
    # type: tuple -> tuple
    """
    A helper function to check and reformat coordinate pairs supplied to
    functions. Each pair is checked by ``check_coordinates``.
    """
    if not all([issequence(c) for c in coord_pairs]):
        # Didn't get pairs of coordinates - converting into pairs
        # But first, sanity checks
        assert (len(coord_pairs) % 2 == 0), "Odd number of coordinates supplied! ({})".format(coord_pairs)
        assert all([isinstance(c, (int, basestring)) for i in coord_pairs]), "Coordinates are non-uniform! ({})".format(coord_pairs)
        coord_pairs = convert_flat_list_into_pairs(coord_pairs)
    coord_pairs = list(coord_pairs)
    for i, coord_pair in enumerate(coord_pairs):
        coord_pairs[i] = check_coordinates(canvas, coord_pair)
    return tuple(coord_pairs)

def offset_points(points, offset):
    """
    Given a list/tuple of points and a two-integer offset tuple
    (``(x, y)``), will offset all the points by that ``x`` and ``y``
    and return a tuple.
    """
    return tuple([(p[0]+offset[0], p[1]+offset[1]) for p in points])

def multiply_points(points, mul):
    """
    Given a list/tuple of points and an integer/float multiplier,
    will multiply all the point coordinates (both x and y)
    and return them.
    """
    return tuple([(int(p[0]*mul), int(p[1]*mul)) for p in points])

def expand_coords(coords, expand):
    """
    Expands 4 coordinate values by either a single number or a tuple -
    depends on what you supply to it.
    """
    assert len(coords) == 4, "Need to supply 4 numbers as 'coords' - received {}".format(coords)
    if isinstance(expand, int):
        c = coords; e = expand
        return (c[0]-e, c[1]-e, c[2]+e, c[3]+e)
    elif isinstance(expand, (tuple, list)):
        assert len(expand) == 4, "Need to supply 4 numbers as 'expand' if iterable - received {}".format(coords)
        c = coords; e = expand
        return (c[0]-e[0], c[1]-e[1], c[2]+e[2], c[3]+e[3])
    else:
        raise ValueError("Can't do anything with {} as 'expand'".format(expand))

def get_bounds_for_points(points):
    """
    Given a list/tuple of points (assumed to form a polygon), will return two numbers:

      * ``x``: width of the polygon made from the points (difference between rightmost and leftmost + 1)
      * ``y``, height of the polygon made from the points (difference between topmost and bottommost + 1)
    """
    lx = [p[0] for p in points]
    ly = [p[1] for p in points]
    dx = max(lx)-min(lx) + 1
    dy = max(ly)-min(ly) + 1
    return dx, dy

def convert_flat_list_into_pairs(l):
    """
    Given an iterable of elements, will pair them together and return
    a tuple of two-element tuples. If the list has an odd number
    of elements, will silently reject the last element.
    """
    pl = []
    for i in range(len(l)/2):
        pl.append((l[i*2], l[i*2+1]))
    return tuple(pl)
