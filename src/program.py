from pathlib import Path
from time import sleep

from board_reader import BoardReader
from solver import Solver
from touch_handler import TouchHandler

board_reader = BoardReader()
rows, cols = board_reader.run()
temp_path = Path(__file__).parent / "temp"
temp_path.mkdir(exist_ok=True)
problem_path = temp_path / "problem.nin"
board_reader.print_to_file(problem_path, rows, cols)

solver = Solver()
solution = solver.solve(problem_path, len(rows))

with TouchHandler() as touch_handler:
    for y, row in enumerate(solution):
        for x, is_checked in enumerate(row):
            if is_checked:
                x_coord, y_coord = board_reader.cell_to_coordinates_30(x, y)
                touch_handler.add_touch(x_coord, y_coord)
                sleep(0.15)
                print("#", end="", flush=True)
            else:
                print(".", end="", flush=True)
        print("")

print("Puzzle solved")
