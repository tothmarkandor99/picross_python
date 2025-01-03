import cv2
import numpy as np
import pytesseract as tess
from subprocess import call
import pathlib
import os

# tess.pytesseract.tesseract_cmd = r'c:\Program Files\Tesseract-OCR\tesseract.exe'

current_directory = str(pathlib.Path(__file__).parent.resolve()) + "/"

print(current_directory)

# Image area constants
LEFT30 = np.s_[510:1353, 0:223]
TOP30 = np.s_[180:502, 220:1077]
TOPLEFT_X_30 = 240
TOPLEFT_Y_30 = 524
BOTTOMRIGHT_X_30 = 1055
BOTTOMRIGHT_Y_30 = 1337
YELLOW = np.array([0, 237, 255])  # BGR order


# Helper functions
def row_to_text(I, fullcolor):
    # If fullcolor has yellow pixels, prompt the user, otherwise use tesseract with --psm 6
    has_yellow = False
    minmse = 10000000
    # cv2.imshow("1", fullcolor)
    # cv2.waitKey(0)
    for row in fullcolor:
        for pixel in row:
            minmse = min(minmse, ((YELLOW - pixel) ** 2).mean())
            if ((YELLOW - pixel) ** 2).mean() < 1000.0:
                has_yellow = True
                break
        if has_yellow:
            break
    if has_yellow:
        cv2.imshow("row_preview", fullcolor)
        cv2.waitKey(1)
        input_text = input().split(" ")
    else:
        input_text = list(tess.image_to_string(I, config="--psm 6"))
    print(input_text)
    for char in input_text:
        if not char.isdigit():
            cv2.imshow("row_preview", fullcolor)
            cv2.waitKey(1)
            input_text = input().split(" ")
            break
    input_int = [int(i) for i in input_text]
    return input_int


def col_to_text(I, fullcolor):
    # If fullcolor has yellow pixels, prompt the user, otherwise use tesseract with --psm 6
    has_yellow = False
    for row in fullcolor:
        for pixel in row:
            if ((YELLOW - pixel) ** 2).mean() < 1000.0:
                has_yellow = True
                break
        if has_yellow:
            break
    if has_yellow:
        cv2.imshow("1", fullcolor)
        cv2.waitKey(1)
        input_text = input().split(" ")
    else:
        input_text = list(tess.image_to_string(I, config="--psm 6").replace("\n", ""))
    print(input_text)
    for char in input_text:
        if not char.isdigit():
            cv2.imshow("1", fullcolor)
            cv2.waitKey(1)
            input_text = input().split(" ")
            break
    input_int = [int(i) for i in input_text]
    return input_int


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

        rows.append(row_to_text(row, row_fullcolor))
    cv2.destroyAllWindows()


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
    cv2.destroyAllWindows()


def touch_30(left, top):
    x = TOPLEFT_X_30 + int(left * (BOTTOMRIGHT_X_30 - TOPLEFT_X_30) / 29.0)
    y = TOPLEFT_Y_30 + int(top * (BOTTOMRIGHT_Y_30 - TOPLEFT_Y_30) / 29.0)
    call(
        [current_directory + "../lib/adb/adb", "shell", "input", "tap", str(x), str(y)]
    )


# Load image from device screen
call([current_directory + "../lib/adb/adb.exe", "devices"])
call(
    [
        current_directory + "../lib/adb/adb",
        "shell",
        "screencap",
        "-p",
        "/sdcard/screen.png",
    ]
)
call([current_directory + "../lib/adb/adb", "pull", "/sdcard/screen.png"])
os.replace(
    str(pathlib.Path().resolve()) + "/screen.png",
    current_directory + "../temp/screen.png",
)
IMAGE = cv2.imread(current_directory + "../temp/screen.png")

# Prepare image area arrays
LEFT = IMAGE[LEFT30]
LEFT_MONO = LEFT[:, :, 1]
LEFT_MONO = cv2.threshold(LEFT_MONO, 180, 255, cv2.THRESH_BINARY)[1]

TOP = IMAGE[TOP30]
TOP_MONO = TOP[:, :, 1]
TOP_MONO = cv2.threshold(TOP_MONO, 180, 255, cv2.THRESH_BINARY)[1]

# Open .mk file
FILE = open(current_directory + "../temp/solve.mk", "w")
FILE.write("30 30\n")

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
        FILE.write(str(num) + " ")
    FILE.write("\n")
FILE.write("#\n")
for col in cols:
    for num in col:
        FILE.write(str(num) + " ")
    FILE.write("\n")
FILE.close()

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
FILE_SOL = open("solution.txt", "r")
solution = []
for y, line in enumerate(FILE_SOL):
    solution.append([])
    for x, char in enumerate(line):
        if char == "X":
            solution[len(solution) - 1].append(True)
        else:
            solution[len(solution) - 1].append(False)
FILE_SOL.close()

# Touch black cells on device
for y, row in enumerate(solution):
    for x, is_checked in enumerate(row):
        if is_checked:
            touch_30(x, y)
            print("X", end="", flush=True)
        else:
            print(".", end="", flush=True)
    print("")

print("Puzzle solved")
