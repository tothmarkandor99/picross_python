from pathlib import Path
import subprocess

class Solver:
    def __init__(self):
        self.lib_path = Path(__file__).parent / "lib"
        self.temp_path = self.lib_path / "temp"
        self.temp_path.mkdir(exist_ok=True)

        # Run solver
        self.solver_path = self.lib_path / "picross-solver" / "bin" / "picross_solver_cli.exe"

    def solve(self, problem_path, side):
        solver_output = subprocess.check_output([self.solver_path, problem_path]).decode("utf-8")

        # Read solution
        solution_text = []
        lines = solver_output.splitlines()
        for i, line in enumerate(lines):
            if "Solution nb 1" in line:
                solution_text = lines[i + 1 : i + 1 + side]
                break

        solution = []
        for y, line in enumerate(solution_text):
            solution.append([])
            for x, char in enumerate(line):
                if char == "#":
                    solution[len(solution) - 1].append(True)
                else:
                    solution[len(solution) - 1].append(False)

        return solution