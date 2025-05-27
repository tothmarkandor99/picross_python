from dataclasses import dataclass
from typing import Literal, Sequence
import cv2
import numpy as np
import pytesseract as tess
import subprocess
from pathlib import Path
from time import sleep
from TouchHandler import TouchHandler
from math import sqrt
from sklearn.cluster import KMeans
from tqdm import tqdm

SKIP_GRAB_SCREENSHOT = False

current_directory = Path(__file__).parent
temp_path = current_directory.parent / "temp"
temp_path.mkdir(exist_ok=True)
lib_path = current_directory.parent / "lib"

# Image area constants
NUMBER_ROW_HEIGHT_30 = 25.375
YELLOW = np.array([0, 207, 221])  # BGR order
BLACK = np.array([0, 0, 0])  # BGR order
WHITE = np.array([255, 255, 255])  # BGR order

# Helper functions


def is_color(pixel, color, threshold=1000.0):
    return ((color - pixel) ** 2).mean() < threshold


def detect_board_size(IMAGE):
    GRAY = cv2.cvtColor(IMAGE, cv2.COLOR_BGR2GRAY)
    MONO = cv2.threshold(GRAY, 180, 255, cv2.THRESH_BINARY)[1]
    contours, _ = cv2.findContours(MONO, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # filter axis-aligned rectangles
    contours = [contour for contour in contours if len(contour) == 4]
    contours_data = [
        {
            "area": cv2.contourArea(contour),
            "contour": contour,
            "is_small_cluster": False,
        }
        for contour in contours
    ]
    contours_data = [c for c in contours_data if c["area"] != 0.0]

    # cluster contours by area
    areas = np.array([c["area"] for c in contours_data])
    km = KMeans(n_clusters=2)
    km.fit(areas.reshape(-1, 1))

    # remove small clusters
    cluster_sizes = np.bincount(km.labels_)
    for i, size in enumerate(cluster_sizes):
        if size < 15:
            for j, label in enumerate(km.labels_):
                if label == i:
                    contours_data[j]["is_small_cluster"] = True

    cell_contours_data = [c for c in contours_data if not c["is_small_cluster"]]
    cell_contours = [c["contour"] for c in cell_contours_data]

    # calculate board size
    cells = len(cell_contours)
    side = int(sqrt(cells))
    if side * side != cells:
        raise Exception("Warning: not square board")

    # calculate board area
    hull = cv2.convexHull(np.concatenate(cell_contours))
    top_left_x = hull[hull[:, :, 0].argmin()][0][0]
    top_left_y = hull[hull[:, :, 1].argmin()][0][1]
    bottom_right_x = hull[hull[:, :, 0].argmax()][0][0]
    bottom_right_y = hull[hull[:, :, 1].argmax()][0][1]

    return side, [top_left_x, top_left_y, bottom_right_x, bottom_right_y]


def digits_to_numbers(input_text, colors, fullcolor):
    try:
        if len(input_text) > len(colors):
            raise Exception("Warning: too few colors")
        elif len(input_text) < len(colors):
            raise Exception("Warning: too many colors")
        else:
            numbers = []
            second_number = False
            for index, char in enumerate(input_text):
                if char.isdigit():
                    color = colors[index]
                    if second_number and color == "yellow":
                        last_number = numbers.pop()
                        numbers.append(last_number * 10 + int(char))
                        second_number = False
                    elif second_number and not color == "yellow":
                        raise Exception(
                            "Warning: yellow number not followed by yellow number"
                        )
                    elif not second_number and color == "white":
                        numbers.append(int(char))
                    elif not second_number and color == "yellow":
                        numbers.append(int(char))
                        second_number = True
                else:
                    raise Exception("Warning: non-numeric character")
    except Exception as e:
        message = e.args
        print(message)
        cv2.imshow("row_preview", fullcolor)
        cv2.waitKey(1)
        input_text = input().split(" ")
        numbers = [int(i) for i in input_text]

    return numbers


NumberColorType = Literal["yellow", "white"]


def row_to_colors(row: np.ndarray, row_fullcolor) -> list[NumberColorType]:
    """Extracts colors from a row of numbers. If there are n numbers, there will be n colors.

    Cast a ray at the middle of the row to find first number. Then find rightmost pixel of the number using 2D flood fill.
    Cast another ray from the rightmost pixel to find the next number.
    """

    colors: list[NumberColorType] = []

    scan_x = 0  # start from the left
    while scan_x < row.shape[1]:
        # find first black pixel
        while (
            scan_x < row.shape[1]
            and not np.equal(row[:, scan_x], BLACK).all(axis=1).any()
        ):
            scan_x += 1

        if scan_x >= row.shape[1]:  # end of row reached
            break
        else:  # number found
            num_y = 0
            while not np.array_equal(row[num_y, scan_x], BLACK):
                num_y += 1

            visited: set[tuple[int, int]] = set()
            remaining: set[tuple[int, int]] = set()
            rightmost_x = scan_x

            # find rightmost pixel of the number using flood fill
            remaining.add((scan_x, num_y))
            while len(remaining) > 0:
                x, y = remaining.pop()
                if (x, y) in visited:
                    continue
                visited.add((x, y))

                if x > rightmost_x:
                    rightmost_x = x

                # check neighbors
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        ny, nx = y + dy, x + dx
                        if (
                            (dy == 0 and dx == 0)  # skip self
                            or ((nx, ny) in visited)  # skip already visited
                            or not (0 <= ny < row.shape[0])
                            or not (0 <= nx < row.shape[1])  # skip out of bounds
                        ):
                            continue

                        if np.array_equal(row[ny, nx], BLACK):
                            remaining.add((nx, ny))

            # check if yellow or white
            visited_is_yellow = [
                is_color(row_fullcolor[y, x], YELLOW) for x, y in visited
            ]
            if sum(visited_is_yellow) > len(visited) / 2:
                colors.append("yellow")  # likely yellow
            else:
                colors.append("white")  # likely white

            scan_x = rightmost_x + 1  # move to the next pixel after the number

    return colors


def row_to_text(I, fullcolor):
    colors = row_to_colors(I, fullcolor)

    input_text = list(tess.image_to_string(I, config="--psm 6").replace("\n", ""))

    numbers = digits_to_numbers(input_text, colors, fullcolor)

    return numbers


def split_rows(fullcolor):
    I = fullcolor[:, :, 1]
    I = cv2.threshold(I, 180, 255, cv2.THRESH_BINARY)[1]

    rows = []
    top = 0
    bottom = 0
    while True:
        while np.sum(I[bottom]) == 0:
            bottom += 1
            if bottom >= I.shape[0] - 1:
                return rows
        top = bottom
        while np.sum(I[bottom]) != 0:
            bottom += 1
        row = 255 - np.zeros([bottom - top + 10, I.shape[1]], dtype=np.uint8)
        row[5 : 5 + bottom - top, :] = 255 - I[top:bottom, :]
        row = np.stack([row, row, row], axis=2)

        row_fullcolor = np.zeros([bottom - top + 10, I.shape[1], 3], dtype=np.uint8)
        row_fullcolor[5 : 5 + bottom - top, :, :] = fullcolor[top:bottom, :, :]

        cv2.imshow("1", row)
        cv2.waitKey(1)

        rows.append(row_to_text(row, row_fullcolor))


@dataclass
class DigitInfo:
    value: int
    contour: Sequence[cv2.typing.MatLike]
    center: tuple[float, float]
    top: int
    bottom: int


def split_cols(fullcolor, side: int) -> list[list[int]]:
    I = fullcolor[:, :, 1]
    I = cv2.threshold(I, 150, 255, cv2.THRESH_BINARY)[1]

    debug_img(I, "mono")

    cols_digit_infos: list[list[DigitInfo]] = [[] for _ in range(side)]

    # find digit contours
    contours, hierarchy = cv2.findContours(I, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = [contour for contour in contours if len(contour) != 4]

    padding = 3
    for i, contour in enumerate(tqdm(contours)):
        if hierarchy[0][i][3] != -1:
            # skip contours that are children of other contours
            continue

        # extract each digit into a separate image

        # draw parent contour with white
        x, y, w, h = cv2.boundingRect(contour)
        digit_contour = contour - np.array([[x - padding, y - padding]])
        digit = np.zeros((h + padding * 2, w + padding * 2), np.uint8)
        cv2.drawContours(digit, [digit_contour], -1, (255, 255, 255), -1)

        # draw child contours with black
        next_child_index = hierarchy[0][i][2]
        while next_child_index != -1:
            child_contour = contours[next_child_index] - np.array(
                [[x - padding, y - padding]]
            )
            cv2.drawContours(digit, [child_contour], -1, (0, 0, 0), -1)
            next_child_index = hierarchy[0][next_child_index][0]

        # recognize
        try:
            text = tess.image_to_string(
                digit, config="--psm 10 digits"
            )  # psm 10 for single character
            text = text.strip()
            number = int(text)
        except ValueError:
            # dilate digit to make it more recognizable
            dilated_digit = cv2.dilate(digit, np.ones((2, 2), np.uint8), iterations=1)

            # dilated digit too fat, try to recognize without dilation
            text = tess.image_to_string(
                dilated_digit, config="--psm 10 digits"
            )  # psm 10 for single characters
            text = text.strip()
            number = int(text)

        # find center of the digit
        M = cv2.moments(contour)
        center = (
            M["m10"] / M["m00"],  # x coordinate of the center
            M["m01"] / M["m00"],  # y coordinate of the center
        )
        # determine column index
        column_index = int(center[0] / (fullcolor.shape[1] / side))
        debug_img(digit, f"digit_{column_index}_{len(cols_digit_infos[column_index])}")

        cols_digit_infos[column_index].append(
            DigitInfo(
                value=number,
                contour=digit_contour,
                center=center,
                top=y,
                bottom=y + h,
            )
        )

    cols = []
    for col_digit_infos in cols_digit_infos:
        col = []

        # sort digits by their center y coordinate
        col_digit_infos.sort(key=lambda d: d.center[1])

        # if two consecutive digits are in the same row, they form a two-digit number
        i = 0
        while i < len(col_digit_infos):
            if i == len(col_digit_infos) - 1:
                # last digit, no next digit to compare
                col.append(col_digit_infos[i].value)
            else:
                digit_info = col_digit_infos[i]
                next_digit_info = col_digit_infos[i + 1]
                if (
                    next_digit_info.top
                    <= digit_info.center[1]
                    <= next_digit_info.bottom
                ):
                    # two-digit number, leftmost digit is the first one
                    if digit_info.center[0] < next_digit_info.center[0]:
                        col.append(digit_info.value * 10 + next_digit_info.value)
                    else:
                        col.append(next_digit_info.value * 10 + digit_info.value)

                    i += 1  # skip next digit, because it was already processed

                else:
                    # single digit
                    col.append(digit_info.value)

            i += 1

        cols.append(col)

    return cols


def cell_to_coordinates_30(left, top):
    cellsize = (BOTTOMRIGHT_X_30 - TOPLEFT_X_30) / 30.0
    x = int(TOPLEFT_X_30 + cellsize / 2.0 + left * cellsize)
    y = int(TOPLEFT_Y_30 + cellsize / 2.0 + top * cellsize)
    return x, y


def grab_screenshot(to_path: Path):
    """Take screenshot of the device and save it to the specified path.

    Args:
        to_path (Path): The path where the screenshot will be saved as screen.png.
    """
    adb_path = current_directory.parent / "lib/adb/adb.exe"
    subprocess.run([adb_path, "devices"])
    subprocess.run(
        [
            adb_path,
            "shell",
            "screencap",
            "-p",
            "/sdcard/screen.png",
        ]
    )
    subprocess.run([adb_path, "pull", "/sdcard/screen.png"], cwd=to_path)


def debug_img(img: np.ndarray, name: str = "debug"):
    """Save a debug image to the temp path with the specified name."""
    cv2.imwrite(str(temp_path / f"{name}.png"), img)


if not SKIP_GRAB_SCREENSHOT:
    grab_screenshot(temp_path)

screenshot_path = temp_path / "screen.png"
IMAGE = cv2.imread(str(screenshot_path))

# Detect board size
side, [TOPLEFT_X_30, TOPLEFT_Y_30, BOTTOMRIGHT_X_30, BOTTOMRIGHT_Y_30] = (
    detect_board_size(IMAGE)
)
LEFT30 = np.s_[TOPLEFT_Y_30:0, BOTTOMRIGHT_Y_30:TOPLEFT_X_30]
TOP30 = np.s_[TOPLEFT_X_30:1000, BOTTOMRIGHT_X_30:TOPLEFT_Y_30]

pass

# Prepare image area arrays
LEFT = IMAGE[TOPLEFT_Y_30:BOTTOMRIGHT_Y_30, 0:TOPLEFT_X_30]
debug_img(LEFT, "left")

TOP = IMAGE[230:TOPLEFT_Y_30, TOPLEFT_X_30:BOTTOMRIGHT_X_30]
debug_img(TOP, "top")

# Open .mk file
problem_path = temp_path / "solve.nin"
with open(problem_path, "w") as f:
    f.write(f"{side} {side}\n")

    # Process left area (rows)
    rows = split_rows(LEFT)
    rowsum = 0
    for row in rows:
        for num in row:
            rowsum += num

    # Prepare top area (cols)
    cols = split_cols(TOP, side)
    colsum = 0
    for col in cols:
        for num in col:
            colsum += num

    # Write to file and wait for solution
    for row in rows:
        for num in row:
            f.write(str(num) + " ")
        f.write("\n")
    f.write("#\n")
    for col in cols:
        for num in col:
            f.write(str(num) + " ")
        f.write("\n")

if len(rows) != 30 or len(cols) != 30 or rowsum != colsum:
    if len(rows) != 30:
        print("Too few rows: " + str(len(rows)))
    if len(cols) != 30:
        print("Too few columns: " + str(len(cols)))
    if rowsum != colsum:
        print("Row sum is " + str(rowsum))
        print("Column sum is " + str(colsum))
    print("Waiting for manual fix...")
    input()

# Run solver
solver_path = lib_path / "picross-solver" / "bin" / "picross_solver_cli.exe"
solver_output = subprocess.check_output([solver_path, problem_path]).decode("utf-8")

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

# Touch black cells on device
with TouchHandler() as touch_handler:
    for y, row in enumerate(solution):
        for x, is_checked in enumerate(row):
            if is_checked:
                x_coord, y_coord = cell_to_coordinates_30(x, y)
                touch_handler.add_touch(x_coord, y_coord)
                sleep(0.15)
                print("#", end="", flush=True)
            else:
                print(".", end="", flush=True)
        print("")

print("Puzzle solved")
