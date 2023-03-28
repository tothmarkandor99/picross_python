import socket
import pathlib
from subprocess import call
import sys
from time import sleep
import subprocess
import keyboard
import random
import binascii

def encode_touch_action_down(x, y):
  width = 1080
  height = 2160

  control_message = bytearray()
  control_message.append(0x02) # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
  control_message.append(0x00) # AKEY_EVENT_ACTION_DOWN
  control_message += bytearray((0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)) # pointer id
  control_message += bytearray(x.to_bytes(4, byteorder='big')) # x
  control_message += bytearray(y.to_bytes(4, byteorder='big')) # y
  control_message += bytearray(width.to_bytes(2, byteorder='big')) # width
  control_message += bytearray(height.to_bytes(2, byteorder='big')) # height
  control_message += bytearray((0xff, 0xff)) # pressure
  control_message += bytearray((0x00, 0x00, 0x00, 0x01)) # AMOTION_EVENT_BUTTON_PRIMARY (action button)
  
  return control_message

def encode_touch_action_up(x, y):
  width = 1080
  height = 2160

  control_message = bytearray()
  control_message.append(0x02) # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
  control_message.append(0x01) # AKEY_EVENT_ACTION_UP
  control_message += bytearray((0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)) # pointer id
  control_message += bytearray(x.to_bytes(4, byteorder='big')) # x
  control_message += bytearray(y.to_bytes(4, byteorder='big')) # y
  control_message += bytearray(width.to_bytes(2, byteorder='big')) # width
  control_message += bytearray(height.to_bytes(2, byteorder='big')) # height
  control_message += bytearray((0x00, 0x00)) # pressure
  control_message += bytearray((0x00, 0x00, 0x00, 0x01)) # AMOTION_EVENT_BUTTON_PRIMARY (action button)
  
  return control_message

current_directory = str(pathlib.Path(__file__).parent.resolve()) + "/"

call([current_directory + "../lib/adb/adb.exe", "devices"])

subprocess.Popen([current_directory + "../lib/adb/adb.exe", "reverse", "--remove-all"])
HOST = "127.0.0.1"
PORT = 27183
subprocess.Popen([current_directory + "../lib/adb/adb.exe", "reverse", "localabstract:scrcpy", f"tcp:{PORT}"])

call([current_directory + "../lib/adb/adb.exe", "shell", "rm", "-rf", "/data/local/tmp/scrcpy-server.jar"])
call([current_directory + "../lib/adb/adb.exe", "push", current_directory + "../lib/scrcpy/scrcpy-server", "/data/local/tmp/scrcpy-server.jar"])

subprocess.Popen([
  current_directory + "../lib/adb/adb.exe",
  "shell",
  "CLASSPATH=/data/local/tmp/scrcpy-server.jar",
  "app_process",
  "/",
  "com.genymobile.scrcpy.Server",
  "1.25",
  "log_level=verbose",
  "max_size=0",
  "bit_rate=1",
  "max_fps=0",
  "lock_video_orientation=-1",
  "tunnel_forward=false",
  "send_frame_meta=false",
  "control=true",
  "display_id=0",
  "show_touches=false",
  "stay_awake=false",
  "power_off_on_close=false",
  "clipboard_autosync=false"
]
,stdout=subprocess.DEVNULL
)

sleep(2)

def randomlocation():
  x = random.randint(352, 552)
  y = random.randint(524, 724)
  return x, y

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
  s.bind((HOST, PORT))
  s.listen()
  s.accept()
  control_conn, control_addr = s.accept()
  with control_conn:
    print(f"Connected by {control_addr}")
    x, y = randomlocation()
    print(binascii.hexlify(encode_touch_action_down(x, y)))
    print("(down event) sending bytes: ", len(encode_touch_action_down(x, y)))
    print("(down event) sent bytes: ", control_conn.send(encode_touch_action_down(x, y)))
    sleep(1)
    print(binascii.hexlify(encode_touch_action_up(x, y)))
    print("(up event) sending bytes: ", len(encode_touch_action_up(x, y)))
    print("(up event) sent bytes: ", control_conn.send(encode_touch_action_up(x, y)))
    sleep(1)
  s.close()
