import cv2
import numpy as np
import pytesseract as tess
from subprocess import call
import pathlib
import os
import time

current_directory = str(pathlib.Path(__file__).parent.resolve()) + "/"

print(current_directory)

# Image area constants
LEFT30 = np.s_[510:1353,0:223]
TOP30 = np.s_[180:502,220:1077]
TOPLEFT_X_30 = 240
TOPLEFT_Y_30 = 524
BOTTOMRIGHT_X_30 = 1055
BOTTOMRIGHT_Y_30 = 1337
YELLOW = np.array([0, 207, 221]) # BGR order
WHITE = np.array([255, 255, 255]) # BGR order

# Helper functions

def is_color(pixel, color, threshold = 1000.0):
  return ((color - pixel)**2).mean() < threshold

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
            raise Exception("Warning: yellow number not followed by yellow number")
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
  single_pixel_row = row[int(row.shape[0] * 0.77),:,:]
  colors = []

  color = "black"
  for pixel in single_pixel_row:
    if (is_color(pixel, YELLOW)):
      if (color != "yellow"):
        colors.append("yellow")
      color = "yellow"
    elif (is_color(pixel, WHITE)):
      if (color != "white"):
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
  NUMBER_ROW_HEIGHT_30 = 25.375

  colors = []

  while True:
    has_number = False
    
    pixel_row_index = int(NUMBER_ROW_HEIGHT_30 * 0.6 + len(colors) * NUMBER_ROW_HEIGHT_30)
    single_pixel_row = col[-pixel_row_index,:,:]

    for pixel in single_pixel_row:
      if (is_color(pixel, YELLOW)):
        has_number = True
        colors.append("yellow")
        break
      elif (is_color(pixel, WHITE)):
        has_number = True
        colors.append("white")
        break

    if(not has_number):
      break

  colors.reverse()

  # Duplicate yellow, because it's double digit
  colors = [color for color in colors for _ in (range(2) if color == "yellow" else range(1))]
  return colors
  
def col_to_text(I, fullcolor):
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
    row = 255-np.zeros([bottom-top+10, I.shape[1]],dtype=np.uint8)
    row[5:5+bottom-top,:] = 255 - I[top:bottom,:]
    row = np.stack([row, row, row],axis=2)
    
    row_fullcolor = np.zeros([bottom-top+10, I.shape[1], 3],dtype=np.uint8)
    row_fullcolor[5:5+bottom-top,:,:] = fullcolor[top:bottom,:,:]
    
    cv2.imshow("1", row)
    cv2.waitKey(1)

    rows.append(row_to_text(row, row_fullcolor))
  cv2.destroyAllWindows()

def split_cols(I, fullcolor):
  cols = []
  left = 0
  right = 0
  while True:
    while np.sum(I[:,right]) == 0:
      right += 1
      if right >= I.shape[1] - 1:
        return cols
    left = right
    while np.sum(I[:,right]) != 0:
      right += 1
    col = 255-np.zeros([I.shape[0], right-left+10],dtype=np.uint8)
    col[:,5:5+right-left] = 255 - I[:,left:right]
    col = np.stack([col, col, col],axis=2)
    
    col_fullcolor = np.zeros([I.shape[0], right-left+10, 3],dtype=np.uint8)
    col_fullcolor[:,:,:] = fullcolor[:,left - 5:right + 5,:]
    
    cols.append(col_to_text(col, col_fullcolor))
  cv2.destroyAllWindows()

def touch_30(left, top):
  x = TOPLEFT_X_30 + int(left * (BOTTOMRIGHT_X_30 - TOPLEFT_X_30) / 29.0)
  y = TOPLEFT_Y_30 + int(top * (BOTTOMRIGHT_Y_30 - TOPLEFT_Y_30) / 29.0)
  call([current_directory + "../lib/adb/adb", "shell", "input", "tap" , str(x) , str(y)])

# Load image from device screen
# call([current_directory + "../lib/adb/adb.exe", "devices"])
# call([current_directory + "../lib/adb/adb", "shell", "screencap", "-p" , "/sdcard/screen.png"])
# call([current_directory + "../lib/adb/adb", "pull", "/sdcard/screen.png"])
# os.replace(str(pathlib.Path().resolve()) + "/screen.png", current_directory + "../temp/screen.png")
IMAGE = cv2.imread(current_directory + '../temp/screen.png')

# Prepare image area arrays
LEFT = IMAGE[LEFT30]
LEFT_MONO = LEFT[:,:,1]
LEFT_MONO = cv2.threshold(LEFT_MONO, 180, 255, cv2.THRESH_BINARY)[1]

TOP = IMAGE[TOP30]
TOP_MONO = TOP[:,:,1]
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
FILE_SOL = open(current_directory + "../temp/solution.txt", "r")
solution = []
for y, line in enumerate(FILE_SOL):
  solution.append([])
  for x, char in enumerate(line):
    if char == 'X':
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
