import sys
from copy import deepcopy

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self): # очищение данных self.domains(начальная чистка)
        for i in self.domains:
            st = set()
            for j in self.domains[i]:
                if i.length != len(j):
                    st.add(j)
            self.domains[i].difference_update(st)

    def revise(self, var, value, previous_domains): # 1) очищение данных self.domains
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        domains = deepcopy(previous_domains)
        for i in domains:
            if i == var:
                continue
            try:
                domains[i].remove(value)
            except KeyError:
                pass
        neighbors = self.crossword.neighbors(var)
        for neighbor in neighbors:
            index_x, index_y = self.crossword.overlaps[var, neighbor]
            for j in previous_domains[neighbor]:
                if j[index_y] != value[index_x]:
                    domains[neighbor].remove(j)
        return domains


    def ac3(self, arcs=None, new_domain=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if not arcs:
            arcs = {}
            new_domain = self.domains.copy()
        if self.assignment_complete(arcs):
            self.domains = arcs
            return True
        new_explore_var = self.select_unassigned_variable(arcs, new_domain)
        if new_explore_var is None:
            return False
        for value in self.order_domain_values(new_explore_var, new_domain):
            arcs[new_explore_var] = value
            if self.ac3(arcs, self.revise(new_explore_var, value, new_domain)):
                return True
        return False





    def assignment_complete(self, assignment): # 2) проверка на согласованность
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        if len(assignment) != len(self.crossword.variables):
            return False
        for i in assignment:
            if len(assignment[i]) == 1:
                return False
        return True

    def consistent(self, assignment): # 3) проверка на согласованность
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for i in assignment:
            k = 1 if i.direction == Variable.DOWN else 0
            for j in self.crossword.neighbors(i):
                both_pos = self.crossword.overlaps[i, j]
                if assignment[i][k] != assignment[j][1-k]: # check
                    return False
        return True


    def order_domain_values(self, var, assignment): # 4) сортировка значений одной переменной
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        neighbors = self.crossword.neighbors(var)
        dictionary = {}
        for i in assignment[var]:
            count = 0
            for neighbor in neighbors:
                index_x, index_y = self.crossword.overlaps[var, neighbor]
                for j in assignment[neighbor]:
                    if j[index_y] != i[index_x]:
                        count += 1
            dictionary[i] = count
        return sorted(dictionary, key=dictionary.get) # check

    def select_unassigned_variable(self, assignment, new_domain): # 5) возвращает переменную veriable,
        # наиболее подходящую
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        keys = set(new_domain.keys()).difference(assignment.keys())
        mini = 10**5
        znach = None
        for key in keys:
            if len(new_domain[key]) <= mini:
                mini = len(new_domain[key])
                if znach:
                    if len(self.crossword.neighbors(znach)) < len(self.crossword.neighbors(key)):
                        znach = key
                else:
                    znach = key
        return znach



    def backtrack(self, assignment):
        return self.domains


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
