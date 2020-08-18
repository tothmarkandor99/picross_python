import cv2
import numpy as np
from subprocess import call

# Image area constants
LEFT30 = np.s_[510:1353,0:223]
TOP30 = np.s_[180:502,224:1067]
TOPLEFT_X_30 = 240
TOPLEFT_Y_30 = 524
BOTTOMRIGHT_X_30 = 1055
BOTTOMRIGHT_Y_30 = 1337 # lEET
YELLOW = np.array([255, 237, 0])

def touch_30(left, top):
  x = TOPLEFT_X_30 + int(left * (BOTTOMRIGHT_X_30 - TOPLEFT_X_30) / 29.0)
  y = TOPLEFT_Y_30 + int(top * (BOTTOMRIGHT_Y_30 - TOPLEFT_Y_30) / 29.0)
  call(["adb", "shell", "input", "tap" , str(x) , str(y)])

# Read solution
FILE_SOL = open("solution.txt", "r")
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

print("Puzzle solved")
