import cv2
import numpy as np
import pytesseract as tess
tess.pytesseract.tesseract_cmd = r'c:\Program Files\Tesseract-OCR\tesseract.exe'

LEFT30 = np.s_[510:1353,0:223]
TOP30 = np.s_[180:502,224:1067]

def trim_recursive(frame):
  #https://stackoverflow.com/questions/13538748/crop-black-edges-with-opencv
  if frame.shape[0] == 0:
    return np.zeros((0,0,3))

  # crop top
  if not np.sum(frame[0]):
    return trim_recursive(frame[1:])
  # crop bottom
  elif not np.sum(frame[-1]):
    return trim_recursive(frame[:-1])
  # crop left
  elif not np.sum(frame[:, 0]):
    return trim_recursive(frame[:, 1:])
    # crop right
  elif not np.sum(frame[:, -1]):
    return trim_recursive(frame[:, :-1])
  return frame

def split_rows(I):
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
    rows.append(row)

def split_cols(I):
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
    cols.append(col)

def merge(one, two):
  numbers = []
  i = 0
  j = 0



I = cv2.imread('difficult.png')

red = I[:,:,0]
red = cv2.threshold(red, 180, 255, cv2.THRESH_BINARY)[1]
green = I[:,:,1]
green = cv2.threshold(green, 180, 255, cv2.THRESH_BINARY)[1]

left_1 = red[LEFT30]
left_2 = green[LEFT30]
rows_1 = split_rows(left_1)
rows_2 = split_rows(left_2)
row_labels_1 = []
row_labels_2 = []
#for row in rows_1:
  #row_labels_1.append(tess.image_to_string(row))
#for row in rows_2:
  #row_labels_2.append(tess.image_to_string(row))

top_1 = red[TOP30]
top_2 = green[TOP30]
cols_1 = split_cols(top_1)
cols_2 = split_cols(top_2)
col_labels_1 = []
col_labels_2 = []

for i in range(3,14):
  print(i)
  cv2.imshow("",cols_2[2])
  cv2.waitKey(0)
  print(tess.image_to_string(cols_2[2], config="--psm " + str(i)))
  print("")

#for col in cols_1:
  #col_labels_1.append(tess.image_to_string(col, config="--psm 6"))
#for col in cols_2:
  #col_labels_2.append(tess.image_to_string(col, config="--psm 6"))
#print(col_labels_1)
#print(col_labels_2)
