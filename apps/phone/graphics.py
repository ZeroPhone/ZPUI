# This function allows to insert polygons as a list of points whose code is
# laid out in a shape somewhat similar to the polygon's shape. The problem
# with that is - order of points in the polygon list matters when drawing it,
# so we have to reorder the points - otherwise they'll become an untangled mess.
# So, that's what this function does - untangles the polygons according to
# a given mapping.

def untangle_points_by_mapping(points, mapping):
    new_points = [p for p in points]
    for dest, so in enumerate(mapping):
       so = int(so)
       new_points[dest] = points[so]
    return new_points

# Graphics

arrow = (                     # indices:
          (3, 0),             #    0
(0, 3),(2, 3),(4, 3),(6, 3),  # 1 2 3 4
       (2, 8),(4, 8)          #   5 6
)

mapping = "0436521"

arrow = untangle_points_by_mapping(arrow, mapping)

cross = (                               # indices:
      (1, 0),            (7, 0),        #  0     1
(0, 1),                        (8, 1),  # 2       3
                (4, 3),                 #     4
          (3, 4),     (5, 4),           #    5 6
                (4, 5),                 #     7
(0, 7),                        (8, 7),  # 8       9
      (1, 8),            (7, 8)         #  10   11
)

mapping = (0, 4, 1, 3, 6, 9, 11, 7, 10, 8, 5, 2)

cross = untangle_points_by_mapping(cross, mapping)

phone_handset = (
        (4, 0),           # 0
               (8, 1),    # 1
        (4, 3),           # 2
                (7, 4),   # 3

   (2, 11),               # 4
        (4, 12),          # 5
(0, 13),                  # 6
      (3, 15)             # 7
)

mapping = "01324576"

phone_handset = untangle_points_by_mapping(phone_handset, mapping)
