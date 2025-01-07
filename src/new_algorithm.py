import cv2
import numpy as np
import pytesseract as tess
from subprocess import call
import subprocess
from pathlib import Path
from time import sleep
from TouchHandler import TouchHandler
from math import sqrt

current_directory = Path(__file__).parent

# Image area constants
LEFT30 = np.s_[510:1353, 0:223]
TOP30 = np.s_[180:502, 220:1077]
TOPLEFT_X_30 = 240
TOPLEFT_Y_30 = 524
BOTTOMRIGHT_X_30 = 1055
BOTTOMRIGHT_Y_30 = 1337
NUMBER_ROW_HEIGHT_30 = 25.375
YELLOW = np.array([0, 207, 221])  # BGR order
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
        {"area": cv2.contourArea(contour), "contour": contour} for contour in contours
    ]
    contours_data.sort(key=lambda x: x["area"], reverse=True)

    # find contours with similar area
    area_prev = contours_data[0]["area"]
    count = 0
    max_count = 0
    max_count_interval = [0, 0]
    can_stop = False
    for i, contour in enumerate(contours_data):
        area = contour["area"]
        delta = abs(area - area_prev)
        if delta < 50:
            count += 1
            if count >= 100:
                can_stop = True
            if count > max_count:
                max_count = count
                max_count_interval = [i - count, i]
        else:
            if can_stop:
                break
            count = 0
        area_prev = area
    cell_contours_data = contours_data[
        max_count_interval[0] : max_count_interval[1] + 1
    ]
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


def row_to_colors(row):
    single_pixel_row = row[int(row.shape[0] * 0.77), :, :]
    colors = []

    color = "black"
    for pixel in single_pixel_row:
        if is_color(pixel, YELLOW):
            if color != "yellow":
                colors.append("yellow")
            color = "yellow"
        elif is_color(pixel, WHITE):
            if color != "white":
                colors.append("white")
            color = "white"
        else:
            color = "black"
    return colors


def row_to_text(I, fullcolor):
    colors = row_to_colors(fullcolor)

    input_text = list(tess.image_to_string(I, config="--psm 6").replace("\n", ""))

    numbers = digits_to_numbers(input_text, colors, fullcolor)

    return numbers


def col_to_colors(col):

    colors = []

    while True:
        has_number = False

        pixel_row_index = int(
            NUMBER_ROW_HEIGHT_30 * 0.6 + len(colors) * NUMBER_ROW_HEIGHT_30
        )
        if pixel_row_index >= col.shape[0]:
            break
        single_pixel_row = col[-pixel_row_index, :, :]

        for pixel in single_pixel_row:
            if is_color(pixel, YELLOW):
                has_number = True
                colors.append("yellow")
                break
            elif is_color(pixel, WHITE):
                has_number = True
                colors.append("white")
                break

        if not has_number:
            break

    colors.reverse()

    # Duplicate yellow, because it's double digit
    colors = [
        color for color in colors for _ in (range(2) if color == "yellow" else range(1))
    ]
    return colors


def col_to_text(I, fullcolor):
    threshold = cv2.threshold(
        cv2.cvtColor(I, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY
    )[1]
    contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = [contour for contour in contours if len(contour) != 4]
    content_area = cv2.boundingRect(np.concatenate(contours))
    I = I[
        max(0, content_area[1] - 1) : min(
            I.shape[0], content_area[1] + content_area[3] + 1
        ),
        max(0, content_area[0] - 1) : min(
            I.shape[1], content_area[0] + content_area[2] + 1
        ),
    ]
    fullcolor = fullcolor[
        max(0, content_area[1] - 1) : min(
            fullcolor.shape[0], content_area[1] + content_area[3] + 1
        ),
        max(0, content_area[0] - 1) : min(
            fullcolor.shape[1], content_area[0] + content_area[2] + 1
        ),
    ]
    colors = col_to_colors(fullcolor)

    input_text = list(tess.image_to_string(I, config="--psm 6").replace("\n", ""))

    numbers = digits_to_numbers(input_text, colors, fullcolor)

    return numbers


def split_rows(I, fullcolor):
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


def split_cols(I, fullcolor):
    cols = []
    left = 0
    right = 0
    while True:
        while np.sum(I[:, right]) == 0:
            right += 1
            if right >= I.shape[1] - 1:
                return cols
        left = right
        while np.sum(I[:, right]) != 0:
            right += 1
        col = 255 - np.zeros([I.shape[0], right - left + 10], dtype=np.uint8)
        col[:, 5 : 5 + right - left] = 255 - I[:, left:right]
        col = np.stack([col, col, col], axis=2)

        col_fullcolor = np.zeros([I.shape[0], right - left + 10, 3], dtype=np.uint8)
        col_fullcolor[:, :, :] = fullcolor[:, left - 5 : right + 5, :]

        cols.append(col_to_text(col, col_fullcolor))


def cell_to_coordinates_30(left, top):
    cellsize = (BOTTOMRIGHT_X_30 - TOPLEFT_X_30) / 30.0
    x = int(TOPLEFT_X_30 + cellsize / 2.0 + left * cellsize)
    y = int(TOPLEFT_Y_30 + cellsize / 2.0 + top * cellsize)
    return x, y


# Load image from device screen
adb_path = current_directory.parent / "lib/adb/adb.exe"
call([adb_path, "devices"])
call(
    [
        adb_path,
        "shell",
        "screencap",
        "-p",
        "/sdcard/screen.png",
    ]
)
temp_path = current_directory.parent / "temp"
temp_path.mkdir(exist_ok=True)
call([adb_path, "pull", "/sdcard/screen.png"], cwd=temp_path)
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
LEFT_MONO = LEFT[:, :, 1]
LEFT_MONO = cv2.threshold(LEFT_MONO, 180, 255, cv2.THRESH_BINARY)[1]

TOP = IMAGE[230:TOPLEFT_Y_30, TOPLEFT_X_30:BOTTOMRIGHT_X_30]
cv2.imwrite(str(temp_path / "debug.png"), TOP)
TOP_MONO = TOP[:, :, 1]
TOP_MONO = cv2.threshold(TOP_MONO, 180, 255, cv2.THRESH_BINARY)[1]

# Open .mk file
problem_path = temp_path / "solve.nin"
with open(problem_path, "w") as f:
    f.write("30 30\n")

    # Process left area (rows)
    rows = split_rows(LEFT_MONO, LEFT)
    rowsum = 0
    for row in rows:
        for num in row:
            rowsum += num

    # Prepare top area (cols)
    cols = split_cols(TOP_MONO, TOP)
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
call(["bash", "solve.sh"])

# Read solution
solution_path = temp_path / "solution.txt"
with open(solution_path, "r") as f:
    solution = []
    for y, line in enumerate(f):
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
