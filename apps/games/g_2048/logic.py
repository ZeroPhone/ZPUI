"""The MIT License (MIT)

Copyright (c) 2014 Tay Yang Shun

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

from random import randint, choice, random
from zpui_lib.helpers import flatten


class GameOf2048(object):
    matrix = None

    def __init__(self, x_dim=4, y_dim=4):
        self.has_won = False  # to remember if the player has already got a 2048 tile once
        self.score = 0  # keep the score
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.matrix = self.get_new_matrix(self.x_dim, self.y_dim)
        self.add_random_digit()
        # add two digits to a new field
        self.add_random_digit()

    @staticmethod
    def get_new_matrix(x, y):
        new = []
        for i in range(y):
            row = []
            for i in range(x):
                row.append(0)
            new.append(row)
        return new

    def add_random_digit(self):
        if not any([cell == 0 for cell in flatten(self.matrix)]):
            # No place available to add
            return
        a = randint(0, self.y_dim - 1)
        b = randint(0, self.x_dim - 1)
        while self.matrix[a][b] != 0:
            a = randint(0, self.y_dim - 1)
            b = randint(0, self.x_dim - 1)
        digit = 2 if random() < 0.9 else 4
        self.matrix[a][b] = digit

    def get_game_state(self):
        if any([cell == 2048 for cell in flatten(self.matrix)]) and not self.has_won:
            # remember that user has already got a 2048 tile, to avoid displaying 'you won' each time.
            self.has_won = True
            return 'win'
        # If there are empty fields, the game isn't over yet
        if any([cell == 0 for cell in flatten(self.matrix)]):
            return 'not over'
        for i in range(len(self.matrix) - 1):  # intentionally reduced to check the row on the right and below
            for j in range(len(
                    self.matrix[0]) - 1):  # more elegant to use exceptions but most likely this will be their solution
                if self.matrix[i][j] == self.matrix[i + 1][j] or self.matrix[i][j + 1] == self.matrix[i][j]:
                    return 'not over'
        for k in range(len(self.matrix) - 1):  # to check the left/right entries on the last row
            if self.matrix[len(self.matrix) - 1][k] == self.matrix[len(self.matrix) - 1][k + 1]:
                return 'not over'
        for j in range(len(self.matrix) - 1):  # check up/down entries on last column
            if self.matrix[j][len(self.matrix) - 1] == self.matrix[j + 1][len(self.matrix) - 1]:
                return 'not over'
        if self.has_won:
            # this happens if the field is full but the user got a 2048 tile once.
            return 'win'
        return 'lose'

    def get_field(self):
        return self.matrix

    def reverse(self):
        new = []
        for i in range(len(self.matrix)):
            new.append([])
            for j in range(len(self.matrix[0])):
                new[i].append(self.matrix[i][len(self.matrix[0]) - j - 1])
        self.matrix = new

    def transpose(self):
        new = []
        for i in range(len(self.matrix[0])):
            new.append([])
            for j in range(len(self.matrix)):
                new[i].append(self.matrix[j][i])
        self.matrix = new

    def cover_up(self):
        new = self.get_new_matrix(self.x_dim, self.y_dim)
        changed = False
        for i in range(4):
            count = 0
            for j in range(4):
                if self.matrix[i][j] != 0:
                    new[i][count] = self.matrix[i][j]
                    if j != count:
                        changed = True
                    count += 1
        self.matrix = new
        return changed

    def merge(self):
        changed = False
        for i in range(4):
            for j in range(3):
                if self.matrix[i][j] == self.matrix[i][j + 1] and self.matrix[i][j] != 0:
                    self.matrix[i][j] *= 2
                    self.score += self.matrix[i][j]
                    self.matrix[i][j + 1] = 0
                    changed = True
        return changed

    # UI-focused functions

    def up(self):
        self.transpose()
        coverup_changed = self.cover_up()
        merge_changed = self.merge()
        has_changed = coverup_changed or merge_changed
        self.cover_up()
        self.transpose()
        if has_changed:
            self.add_random_digit()

    def down(self):
        self.transpose()
        self.reverse()
        coverup_changed = self.cover_up()
        merge_changed = self.merge()
        has_changed = coverup_changed or merge_changed
        self.cover_up()
        self.reverse()
        self.transpose()
        if has_changed:
            self.add_random_digit()

    def left(self):
        coverup_changed = self.cover_up()
        merge_changed = self.merge()
        has_changed = coverup_changed or merge_changed
        self.cover_up()
        if has_changed:
            self.add_random_digit()

    def right(self):
        self.reverse()
        coverup_changed = self.cover_up()
        merge_changed = self.merge()
        has_changed = coverup_changed or merge_changed
        self.cover_up()
        self.reverse()
        if has_changed:
            self.add_random_digit()
