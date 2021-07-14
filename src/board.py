#
# board.py
# 
# Copyright (C) 2021 Till Harbaum <till@harbaum.org>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301 USA.from PyQt5.QtCore import *
#

from PyQt5.QtCore import *

import serial
import serial.tools.list_ports
import sys, time

import textwrap
import binascii
import ast

from queue import Queue

# 1: CTRL-A -- on a blank line, enter raw REPL mode
# 2: CTRL-B -- on a blank line, enter normal REPL mode
# 3: CTRL-C -- interrupt a running program
# 4: CTRL-D -- on a blank line, do a soft reset of the board
# 5: CTRL-E -- on a blank line, enter paste mode

class BoardThread(QThread):
   def __init__(self, board, cmd_code, parms = None):
      super().__init__()
      self.board = board
      self.board.cmd_code = cmd_code   # store a copy in board
      self.cmd_code = cmd_code
      self.parms = parms
      self.len = 0
      self.percent = 0

   def send_status(self, msg):
      self.board.queue.put( (Board.STATUS, msg))

   def file_progress(self, b):
      self.len += len(b)
      # 50 * ... because the file is being transferred in hex which
      # doubles the number of bytes to be transferred
      percent = 50 * self.len // self.parms["size"]
      if self.percent != percent:
         self.percent = percent
         self.board.queue.put( (Board.PROGRESS, percent ) )
      
   def run_output(self, b):
      self.board.queue.put( (Board.CONSOLE, b) )

   def run(self):
      result = None

      try:
         if self.cmd_code == Board.SCAN:
            self.board.detect(self.send_status)
            self.board.queue.put( (Board.RESULT, True) )       
         elif self.cmd_code == Board.GET_VERSION:
            result = self.board.getVersion()
            self.board.queue.put( (Board.RESULT, True, result) )       
         elif self.cmd_code == Board.LISTDIR:
            result = self.board.listDir()
            self.board.queue.put( (Board.RESULT, True, result) )       
         elif self.cmd_code == Board.PUT_FILE:
            self.board.putFile(self.parms["name"], self.parms["code"])
            self.board.queue.put( (Board.RESULT, True ) )       
         elif self.cmd_code == Board.GET_FILE:
            result = {
               "code": self.board.getFile(self.parms["name"], self.file_progress),
               "name": self.parms["name"]
            }
            self.board.queue.put( (Board.RESULT, True, result) )       
         elif self.cmd_code == Board.RUN:
            self.board.run(self.parms["code"], self.run_output)
            self.board.queue.put( (Board.RESULT, True ) )       
         else:
            print("Unexpected command", self.cmd_code)
            self.board.queue.put( (Board.RESULT, False, "Unexpected command" ))
      except:
         # report failure
         print("Exception in BoardTread():", sys.exc_info())
         self.board.queue.put( (Board.RESULT, False ))
         
         # report error in console
         name = self.parms["name"] if self.cmd_code == Board.RUN else None
         errmsg = sys.exc_info()[1]
         if isinstance(errmsg, int) and len(sys.exc_info()) > 1:
            errmsg = sys.exc_info()[2]
         
         print("Report:", str(errmsg))
         self.board.queue.put( (Board.ERROR, name, str(errmsg)) )

      self.board.cmd_code = None
      
class Serial(serial.Serial):
   def __init__(self, device):
      super().__init__(device, 115200, interCharTimeout=1, write_timeout=5)
      self._buffer = b""

   def readUntil(self, timeout, seq, callback = None):
      # there may already be data in the buffer which should go with
      # the callback
      if callback:
         # the final marker may already be in the buffer as well
         if seq in self._buffer: callback(self._buffer[:self._buffer.find(seq)])         
         else:                   callback(self._buffer)
      
      # read until a given sequence is found or if a timeout is reached
      start = time.time()
      while (timeout == 0 or time.time() - start < timeout ) and not seq in self._buffer:
         time.sleep(0.01)
         data = self.poll()
         
         # feed everything read into callback (e.g. used for program print output
         # while waiting for EOF         
         if data is not None and callback is not None:
            # WARNING: This really only works for single char seq as a longer sequence
            # may be split over several data chunks and may not be detected. EOF is a
            # single character, so this is fine here
            if seq in data: callback(data[:data.find(seq)])
            else:           callback(data)

      # remove everything up to detected pattern from buffer
      if seq in self._buffer:
         data = self._buffer[:self._buffer.find(seq)]
         self._buffer = self._buffer[self._buffer.find(seq)+len(seq):]
         return ( True, data )

      return ( False, None )

   def write(self, data):
      try:
         return super().write(data)
      except serial.SerialException as e:
         print("Serial write exception", e)
         raise RuntimeError("Serial write failed")

      # an exception may also happen in the read. However, chances are
      # high they'll happen here as the USB/serial port likely broke
      # while the user wasn't communicating with the board. So the most
      # likely case for a serial error is the first byte being written
      # for a new command.
      
      # todo: try to re-open port and re-send data
      
   
   def poll(self):
      try:
         # read all available data into the buffer
         if self.inWaiting() > 0:
            data = super().read(self.inWaiting())
            print("RX:", data)
            self._buffer = self._buffer + data
            return data
      except serial.SerialException as e:
         print("Serial read exception", e)
         raise RuntimeError("Serial read failed")
      
      return None         

   # return a given number of bytes
   def read(self, num):
      while len(self._buffer) < num:
         self.poll()

      v = self._buffer[:num]
      self._buffer = self._buffer[num:]
      return v
        
class Board(QObject):
   code_downloaded = pyqtSignal()    
   console = pyqtSignal(bytes)
   progress = pyqtSignal(int)
   error = pyqtSignal(str, str)
   status = pyqtSignal(str)

   # commands
   SCAN = 1
   GET_VERSION = 2
   LISTDIR = 3
   GET_FILE = 4
   PUT_FILE = 5
   RUN = 6
   
   # message code used by the thread
   CODE_DOWNLOADED = 1
   RESULT = 2
   STATUS = 3
   PROGRESS = 4
   CONSOLE = 5
   ERROR = 6
            
   def __init__(self):
      super().__init__()
      print("Board init");
      self.serial = None
      self.cmd_code = None
      self.thread_running = False

      self.queue = Queue()
      
      # create a listener timer which frequently polls the
      # queue to the worker threads for messages
      self.timer = QTimer()
      self.timer.timeout.connect(self.on_timer)
      self.timer.start(100)  # poll at 10 Hz
      
   def on_timer(self):
      # check if thread is still running
      if self.thread:
         if self.thread.isFinished():
            self.thread = None
            self.done()
      
      # read messages from thread out of queue and convert them
      # into qt signals
      while not self.queue.empty():
         msg = self.queue.get()

         if msg[0] == Board.CONSOLE:
            self.console.emit(msg[1])
         elif msg[0] == Board.CODE_DOWNLOADED:
            self.code_downloaded.emit()
         elif msg[0] == Board.PROGRESS:
            self.progress.emit(msg[1])
         elif msg[0] == Board.ERROR:
            self.error.emit(msg[1], msg[2])
         elif msg[0] == Board.STATUS:
            self.status.emit(msg[1])
         elif msg[0] == Board.RESULT:
            # board command result is handled by command specific
            # callback handlers
            if self.result_cb is not None:
               cb = self.result_cb
               self.result_cb = None

               # return bool success and optional some result value
               if len(msg) == 2: cb(msg[1])
               else:             cb(msg[1], msg[2])
         else:
            print("Unhandled message from thread:", msg)
            
   # start a board thread to run command in the background
   def cmd(self, cmd, cb, parms = None):
      print("Board", cmd, cb, parms)
      self.result_cb = cb
      self.thread = BoardThread(self, cmd, parms)
      if cmd == Board.GET_FILE: self.progress.emit(0)
      else:                     self.progress.emit(-1)
      self.thread.start()

   def done(self):
      print("thread done");
      
   def sendCtrl(self, code):
      codes = { 'a': b'\x01', 'b': b'\x02', 'c': b'\x03',
                'd': b'\x04', 'e': b'\x05' }
        
      if self.serial.write(b'\r'+codes[code]) != 2:
         return False

      time.sleep(0.1)
      return True

   def stop(self):
      # stop a (user) code by sending ctrl-c
      self.sendCtrl('c')
    
   def run(self, cmd, cb = None):
      result = self.replDo(cmd, cb)
      # if the result is just a string, then everything is fine
      if result is not None and isinstance(result, str):
         return result.strip();

      return None

   def listDir(self):
      # a file entry in unformatted flash looks like
      # \xff\xff\xff\xff\xff\xff\xff\xff.\xff\xff\xff
      
      command  = """
            import os
            def listdir(path):
                try:
                    children = os.listdir(path)
                except OSError:
                    try:
                        size = os.stat(path)[6]
                        return size
                    except:
                        return -2
                else:
                    files = [ ]
                    for child in children:
                        # catch broken entries on unformatted pyboard
                        if child.encode()[0] == 255:
                            return -2

                        if path == '/': path = ''
                        files.append([ child, listdir(path + '/' + child)])
                    return files

            print(listdir("/"))
        """

      # entries returning a negative size are reported broken. This e.g. happens
      # if the pyboard is not properly formatted
      result = self.replDo(command)
      print("DIR:", ast.literal_eval(result))

      # check if the file system contains errors (-2)
      # my pyboard did not contain a valid filesystem at delivery. This could have
        
      return ast.literal_eval(result)

   def getFile(self, name, progress_cb=None):
      # transfer data "binhexlified" to make sure even binary
      # data can be passed without problems
      print("get file", name);
      command  = """
            import sys, ubinascii
            with open('{0}', 'rb') as infile:
                while True:
                    result = infile.read(32)
                    if result == b'': break
                    sys.stdout.write(ubinascii.hexlify(result))
      """.format(name)
        
      data = self.replDo(command, progress_cb)
      return binascii.unhexlify(data).decode("utf-8")
   
   def putFile(self, name, data):
      command  = """
        with open('{0}', 'wb') as f:\n""".format(name)

      # data is "put" in chunks
      size = len(data)
      for i in range(0, size, 64):
         chunk = repr(data[i : i + min(64, size - i)])
         command += "            f.write({0})\n".format(chunk)

      print("command:", command)
      self.replDo(command)

   def rm(self, filename):
      """Remove the specified file or directory."""
      command = """
        import os
        try:
            os.remove('{0}')
        except:
            os.rmdir('{0}')
        """.format(filename)
      self.replDo(command)
           
   def mkdir(self, filename):
      """Crete a directory."""
      command = """
        import os
        os.mkdir('{0}')
        """.format(filename)
      self.replDo(command)
           
   def rename(self, old, new):
      print("board rename", old, new)
      """Rename the specified file or directory."""
      command = """
        import os
        try:
          os.rename('{0}', '{1}')
        except:
          with open('{2}', 'rb') as src, open('{3}', 'wb') as dst:
            while True:
              buffer = src.read(32)
              if not buffer: 
                break
              dst.write(buffer)
          os.remove('{4}') 
        """.format(old, new, old, new, old)
      self.replDo(command)
      
   def getVersion(self):
      result = self.replDo("import os\rfor i in os.uname(): print( i )")
      if result is not None:
         return result.splitlines()
      
      return [ "<unknown>", "", "", "", "" ]

   def replPrepare(self):
      self.sendCtrl('a')
      return self.serial.readUntil(1, b"CTRL-B to exit\r\n>")[0]
   
   def replDo(self, cmd, callback=None):
      print("replDo", textwrap.dedent(cmd));
        
      if not self.replPrepare():
         # repl could not be entered, try to ctrl-c
         self.interrupt()
         if not self.replPrepare():
            raise RuntimeError("Error: Board not responding to command!")
      
      result = None

      self.serial.write(textwrap.dedent(cmd).encode('utf-8'))

      # cmd code has been sent by BoardThread
      if self.cmd_code == Board.RUN:
         print("downloaded")
         self.queue.put( (Board.CODE_DOWNLOADED, ))
            
      # send ctrl-d and wait for "ok"
      self.sendCtrl('d')
      if self.serial.readUntil(1, b"OK")[0] == True:
         # read until first EOF. This may take very long if the application
         # is running. So we wait forever ...
         result = self.serial.readUntil(0, b"\x04", callback)   # long timeout for many files
         if result[0]:
            result = result[1].decode('utf-8')

            # expect error and second EOF
            err = self.serial.readUntil(1,b"\x04")
            if err[0] and len(err[1]):
               self.sendCtrl('b')
               raise RuntimeError(err[1].decode('utf-8').strip())
         else:
            result = None
        
      self.sendCtrl('b')
      return result

   def interrupt(self):
      # send ctrl-c twice to get into a known state
      if not self.sendCtrl('c'):
         print("Writing ctrl-c failed")
         return False            
            
      print("ctrl-c sent");
      self.sendCtrl('c')
      print("ctrl-c sent");

      # try to find a prompt in reply
      if not self.serial.readUntil(2, b">>> ")[0]:
         print("No prompt")
         return False            

      return True
   
   def probe(self):
      print("Probing", self.serial.port)

      # stop any running program
      if not self.interrupt():
         return False

      # try to enter repl 
      if not self.replPrepare():
         return False
         
      self.sendCtrl('b')
      return True
        
   def open(self, device):
      try:
         print("trying to open", device)
         self.serial = Serial(device)
      except IOError:
         print("failed to open", device);
         self.serial = None
         return False

      # probe for uP
      try:
         if self.probe():
            return True
         else:
            # self.sendCtrl('d')  # this resets the ftduino32 :-(
            self.sendCtrl('b')

            # retry once
            if self.probe():
               return True
      except:
         print("Exception when probing", sys.exc_info());
        
      self.serial.close()
      self.serial = None
      return None

   def isConnected(self):
      return self.serial is not None

   def getPort(self):
      if self.serial is None: return "<none>"
      return self.serial.port
                
   def detect(self, cb=None):
      print("Trying to auto detect");
        
      ports = serial.tools.list_ports.comports()
      for port in ports:
         print("Checking port", port)
         if cb: cb("Checking port {}".format(port.device))
         if self.open(port.device):
            return
            
      raise RuntimeError("No board found!")

   def input(self, data):
      # forward and keyboard input directly to the board
      if self.serial is not None:
         self.serial.write(data.encode("utf-8"))
   
   def close(self):
      if self.serial is not None:
         self.serial.close()
         self.serial = None

      if self.thread:
         print("waiting for thread to end")
         while not self.thread.isFinished():
            time.sleep(.1);
