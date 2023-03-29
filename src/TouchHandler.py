import socket
import pathlib
from time import sleep
import subprocess
import threading
import queue

class TouchHandler:
  """
  TouchHandler sends touch events to the Android device. It uses the scrcpy server to do so.
  Only one instance of TouchHandler can be used at a time. Only one connected device is supported.

  Example:
  >>> with TouchHandler() as touch_handler:
  >>>   touch_handler.touch(100, 100)
  """

  def __run_worker(self):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      s.bind((self.host, self.port))
      s.listen()
      video_conn, _ = s.accept()
      control_conn, _ = s.accept()
      with video_conn:
        with control_conn:
          video_conn.setblocking(False)
          while self.worker_running:
            # while True:
            #   a = video_conn.recv(4096)
            #   if (len(a) < 4096):
            #     break

            try:
              (x, y) = self.touch_queue.get(True, 0.5)
              control_conn.send(self.__encode_touch_action_down(x, y))
              control_conn.send(self.__encode_touch_action_up(x, y))
              self.touch_queue.task_done()
            except queue.Empty:
              pass

  def __init__(self, width=1080, height=2160, host="127.0.0.1", port=27183):
    self.current_directory = str(pathlib.Path(__file__).parent.resolve()) + "/"

    self.width = width
    self.height = height
    self.host = host
    self.port = port
    
    self.touch_queue = queue.Queue()

  def __enter__(self):
    subprocess.call([self.current_directory + "../lib/adb/adb.exe", "devices"])

    subprocess.Popen([self.current_directory + "../lib/adb/adb.exe", "reverse", "--remove-all"])
    subprocess.Popen([self.current_directory + "../lib/adb/adb.exe", "reverse", "localabstract:scrcpy", f"tcp:{self.port}"])

    subprocess.call([self.current_directory + "../lib/adb/adb.exe", "shell", "rm", "-rf", "/data/local/tmp/scrcpy-server.jar"])
    subprocess.call([self.current_directory + "../lib/adb/adb.exe", "push", self.current_directory + "../lib/scrcpy/scrcpy-server", "/data/local/tmp/scrcpy-server.jar"])

    self.server_process = subprocess.Popen([
      self.current_directory + "../lib/adb/adb.exe",
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

    self.worker_running = True
    worker_thread = threading.Thread(target=self.__run_worker)
    worker_thread.start()
    
    return self
 
  def __exit__(self, type, value, traceback):
    self.touch_queue.join()
    self.worker_running = False
    sleep(1) # wait for worker to finish
    self.server_process.kill()
    subprocess.call([self.current_directory + "../lib/adb/adb.exe", "shell", "am", "kill", "com.genymobile.scrcpy.Server"])

  def add_touch(self, x, y):
    """
    Queue a touch event to be sent to the device.
    """
    self.touch_queue.put((x, y))

  def __encode_touch_action_down(self, x, y):
    control_message = bytearray()
    control_message.append(0x02) # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
    control_message.append(0x00) # AKEY_EVENT_ACTION_DOWN
    control_message += bytearray((0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE)) # pointer id
    control_message += bytearray(x.to_bytes(4, byteorder='big')) # x
    control_message += bytearray(y.to_bytes(4, byteorder='big')) # y
    control_message += bytearray(self.width.to_bytes(2, byteorder='big')) # width
    control_message += bytearray(self.height.to_bytes(2, byteorder='big')) # height
    control_message += bytearray((0xff, 0xff)) # pressure
    control_message += bytearray((0x00, 0x00, 0x00, 0x01)) # AMOTION_EVENT_BUTTON_PRIMARY (action button)
    return control_message

  def __encode_touch_action_up(self, x, y):
    control_message = bytearray()
    control_message.append(0x02) # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
    control_message.append(0x01) # AKEY_EVENT_ACTION_UP
    control_message += bytearray((0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE)) # pointer id
    control_message += bytearray(x.to_bytes(4, byteorder='big')) # x
    control_message += bytearray(y.to_bytes(4, byteorder='big')) # y
    control_message += bytearray(self.width.to_bytes(2, byteorder='big')) # width
    control_message += bytearray(self.height.to_bytes(2, byteorder='big')) # height
    control_message += bytearray((0x00, 0x00)) # pressure
    control_message += bytearray((0x00, 0x00, 0x00, 0x00)) # none
    return control_message

