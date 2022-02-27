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

import pyboard, serial, sys
import serial.tools.list_ports
import time

import threading
import binascii
from queue import Queue
import ast

class Board(QObject):
   code_downloaded = pyqtSignal()  # callback when code has been downloaded but not yet run
   console = pyqtSignal(bytes)     # data has arrived from console output
   progress = pyqtSignal(int)      # control progress bar (can be <0 or 0..100)
   error = pyqtSignal(str, str)
   status = pyqtSignal(str)
   lost = pyqtSignal()
   interactive = pyqtSignal()
   
   # commands
   SCAN = 1
   GET_VERSION = 2
   LISTDIR = 3
   GET_FILE = 4
   PUT_FILE = 5
   RUN = 6
   REPL = 7
   CONNECT = 8    # on user request with noscan

   def __init__(self, parent=None):
      super().__init__(parent)
      self.board = None  # not connected yet
      self.worker_thread = None
      self.queue = Queue()
      self.interact = False

      # start a timer for frequent event queue polling
      self.timer = QTimer()
      self.timer.timeout.connect(self.on_timer)
      self.timer.start(20)  # poll at 50 Hz

   def send_console(self, str):
      self.queue.put( ( "console",  str ) )
      
   def send_status(self, msg):
      self.queue.put( ( "status", msg ) )
       
   def send_progress(self, val):
      self.queue.put( ( "progress", val ) )
       
   def send_result(self, success, res=None):       
      self.queue.put( ( "result", ( success, res ) ) )
      
   def func_probe_all(self, ports):
      for port in ports:
         self.send_status(self.tr("Checking port {}").format(port.device))
         res = self.probe(port.device)
         if res:
            self.board = res
            self.send_result( True, res.serial.port )
            return

      # no board found at all
      self.send_result(False)
      
   def probe(self, device):
      # start a probe thread with timeout            
      board = pyboard.Pyboard(device)

      # Set a write timeout. This is needed during scan if
      # we try to probe a device which would not accept any data.
      board.serial.write_timeout = 1
      # Set a read timeout. This is needed for most
      # non-micropython devices during probe
      board.serial.timeout = 1
        
      try:
         board.enter_raw_repl()
      except Exception as e:
         print("1st probe error: "+str(e), "retrying...")

         try:
            board.enter_raw_repl()
         except Exception as e:
            print("2nd probe error: "+str(e))
            
            board.close()
            return None

      # print("repl done")
      board.exit_raw_repl()
      return board

   def func_wrapper(self, *args):
      try:
         # args is a tuple of function and another tuple with its arguments
         args[0](*args[1])
      except Exception as e:
         print("Exception", str(e))
         
         # something has failed. check if the serial connection is lost
         try:
            # make sure we call the super class to trigger
            # hardware problems
            self.board.serial.super().inWaiting()
         except:
            # port seems to be lost
            self.queue.put( ("lost",) )
            return

         if not str(e): e = "Unknown exception"
         
         # must have been something else. Just report it
         self.queue.put( ("exception", ("", str(e) )))
         self.send_result(False)         
            
   def do_in_thread(self, func, args=None):
      """ run worker thread in the background to do the board
      communication """
      
      # Check if thread is already active. This should
      # never happen
      if self.worker_thread:
         raise Exception("Worker already running")

      # start worker thread to do the actual job ...
      self.worker_thread = threading.Thread(target=self.func_wrapper, args=(func,args if args else tuple()))

      self.worker_thread.start()
      
   def on_timer(self):
      # frequently poll the worker queue for results
      
      while not self.queue.empty():
         msg = self.queue.get()

         # message from worker thread to be displayed in the status bar
         if msg[0] == "status":
            self.status.emit(msg[1])
         
         if msg[0] == "progress":
            self.progress.emit(msg[1])
            
         if msg[0] == "exception":
            self.error.emit(msg[1][0], msg[1][1])
            
         if msg[0] == "console":
            self.console.emit(msg[1])

         if msg[0] == "downloaded":
            self.code_downloaded.emit()
            
         if msg[0] == "interactive":
            self.interactive.emit()
            
         if msg[0] == "lost":
            self.worker_thread = None
            self.lost.emit()
            
         # check if the command has sent a result ...
         if msg[0] == "result":
            # invoke callback if present
            self.worker_thread = None
            if self.cb: self.cb(msg[1][0], msg[1][1])

   def scan(self):
      ports = serial.tools.list_ports.comports()
      # probe all ports in background thread
      self.do_in_thread(self.func_probe_all, ( ports, ))
      
   def reply_handle_line_ast(self, line = None):
      if line != None:
         line = line.replace('\r', '')
         if line == "": return
        
         self.result = ast.literal_eval(line)
       
   def reply_parser(self, data = None, line_parser = None):
      # reply_parser collects data returned from micropython.
      
      # if the parser is called without any data at all then
      # the buffer is to be flushed
      if data is None:
         self.reply_buffer = b''
         self.result = None
         return

      # append data to buffer
      self.reply_buffer += data

      # check if data contains a complete line
      if b'\n' in self.reply_buffer:            
         line, self.reply_buffer = self.reply_buffer.split(b'\n', 1)
         line_parser(line.decode("utf-8"))
            
      # x04 in buffer (should) means that this is the end of the message
      if b'\x04' in self.reply_buffer:
         line, self.reply_buffer = self.reply_buffer.split(b'\x04', 1)
         if len(line): line_parser(line.decode("utf-8"))                
         line_parser()

   def reply_parser_ast(self, data = None):
      self.reply_parser(data, self.reply_handle_line_ast)

   def input(self, data):
      # forward and keyboard input directly to the board
      self.board.serial.write(data.encode("utf-8"))

   def func_version(self):
      # print a ast.eval parsable dict
      self.func("import os\r"
             "o = os.uname()\r"
             "v = { 'sysname': o.sysname, 'nodename': o.nodename, "
                   "'release': o.release, 'version': o.version, "
                   "'machine': o.machine }\r"
             "print(v)")

   def version(self):
      self.do_in_thread(self.func_version)

   def func(self, cmd):
      self.reply_parser()           # reset parser
      self.board.enter_raw_repl()
      self.board.exec_(cmd, data_consumer=self.reply_parser_ast)
      self.board.exit_raw_repl()
      self.send_result(True, self.result)
      
   def func_ls(self):
      # recursively scan all files. The result should be a single line
      # of parsable python, so it can be eval'uated on PC side
      self.func(
         "import uos\n"
         "def list(d):\n"
         " print('[',end='')\n"
         " first=True\n"
         " for f in uos.ilistdir(d if d else '/'):\n"
         #  make sure we have a comma before anything but the first entry
         "  if first: first=False\n"
         "  else:     print(',',end='')\n"
         "  print('(\"{}\",'.format(f[0]), end='')\n"
         "  if f[1]&0x4000: list(d+'/'+f[0])\n"
         "  else: print('{}'.format(f[3] if len(f)>3 else 0), end='')\n"
         "  print(')', end='')\n"
         " print(']',end='')\n"
         "list('')\n"
      )

   def ls(self):
      self.do_in_thread(self.func_ls)

   def func_get(self, src, size, reply_parms, chunk_size=256):
      self.reply_parser()           # reset parser
      self.board.enter_raw_repl()

      self.board.exec_("f=open('%s','rb')\nr=f.read" % src)
      result = bytearray()
      while True:
         data = bytearray()
         self.board.exec_("print(r(%u))" % chunk_size, data_consumer=lambda d: data.extend(d))
         assert data.endswith(b"\r\n\x04")
         try:
            data = ast.literal_eval(str(data[:-3], "ascii"))
            if not isinstance(data, bytes):
               raise ValueError("Not bytes")
         except (UnicodeError, ValueError) as e:
            raise pyboard.PyboardError("fs_get: Could not interpret received data: %s" % str(e))
         if not data:
            break
         
         result += data
         self.send_progress(100 * len(result) // size)

      self.board.exec_("f.close()")
      
      self.board.exit_raw_repl()
      reply_parms["code"] = result   # add data read to reply
      self.send_result(True, reply_parms )
      
   def func_get_old(self, name, size, reply_parms):
      self.reply_parser()           # reset parser
      self.board.enter_raw_repl()
      
      # transfer data "binhexlified" to make sure even binary
      # data can be passed without problems
      print("get file", name);
      command  = ("import sys, ubinascii\n"
                  "with open('{0}', 'rb') as infile:\n"
                  " while True:\n"
                  "  result = infile.read(32)\n"
                  "  if result == b'': break\n"
                  "  sys.stdout.write(ubinascii.hexlify(result))\n").format(name)
        
      data = self.board.exec_(command)
      self.board.exit_raw_repl()
   
      reply_parms["code"] = binascii.unhexlify(data)
      self.send_result(True, reply_parms )
            
   def get(self, name, size, reply_parms):
      self.progress.emit(0)
      self.status.emit(self.tr("Reading {}".format(name.split("/")[-1])))
      self.do_in_thread(self.func_get, ( name, size, reply_parms ) )
       
   def func_put(self, all_data, dest, chunk_size=256):
      self.reply_parser()           # reset parser
      self.board.enter_raw_repl()
      size = len(all_data)
      sent = 0
      
      self.board.exec_("f=open('%s','wb')\nw=f.write" % dest)
      while True:
         if all_data != None and len(all_data) > chunk_size:
            data = all_data[0:chunk_size]
            all_data = all_data[chunk_size:]
         else:
            data = all_data
            all_data = None
         
         if not data: break
         self.board.exec_("w(" + repr(data) + ")")
         sent += len(data)
         self.send_progress(100 * sent // size)
      self.board.exec_("f.close()")

      self.board.exit_raw_repl()
      self.status.emit("")     # clear status 
      self.send_result(True)   # TOOD: add parms
       
   def put(self, data, name):
      self.progress.emit(0)
      self.status.emit(self.tr("Writing {}".format(name.split("/")[-1])))
      self.do_in_thread(self.func_put, ( data, name ))

   def func_run(self, name, code):
      self.reply_parser()           # reset parser
      self.board.enter_raw_repl()
      
      self.board.exec_raw_no_follow(code)
      self.queue.put( ( "downloaded", ) )

      try:
         ret, ret_err = self.board.follow(None, self.send_console)
         if ret_err:
            # device side reported an exception
            self.queue.put( ( "exception", (name, ret_err.decode("utf-8")) ) )
      except Exception as e:
         # host side reported an exception
         ret_err = str(e)
         self.queue.put( ( "exception", (name, ret_err) ) )
         
      self.board.exit_raw_repl()
      self.send_result(not ret_err, None)
      
   def run(self, name, code):
      self.do_in_thread(self.func_run, ( name, code ))
      
   def stop(self):
      if self.interact:
         # stop the repl process
         self.interact = False
      else:         
         # stop a (user) code by sending ctrl-c
         self.board.serial.write(b"\r\x03")

   def forceStop(self):
      self.board._interrupt = True
      
   def replDo(self, cmd):
      self.board.enter_raw_repl()
      self.board.exec_(cmd)
      self.board.exit_raw_repl()
      
   def rm(self, filename):
      """Remove the specified file or directory."""
      self.replDo( (
        "import os\n"
        "try:\n"
        " os.remove('{0}')\n"
        "except:\n"
        " os.rmdir('{0}')\n").format(filename))
           
   def mkdir(self, filename):
      """Crete a directory."""
      self.replDo( "import os\nos.mkdir('{0}')\n".format(filename) )

   def rename(self, old, new):
      """Rename the specified file or directory. Copy it if renaming fails"""
      self.replDo( (
        "import os\n"
        "try:\n" 
        " os.rename('{0}', '{1}')\n" 
        "except:\n" 
        " with open('{2}', 'rb') as src, open('{3}', 'wb') as dst:\n" 
        "  while True:\n" 
        "   buffer = src.read(256)\n" 
        "   if not buffer:\n" 
        "    break\n" 
        "   dst.write(buffer)\n" 
        " os.remove('{4}')\n" ).format(old, new, old, new, old))

   def func_interactive(self):
      # try to interrupt the board
      self.board.serial.write(b"\r\x03")      
      time.sleep(0.1)
      self.board.serial.read(self.board.serial.inWaiting())
      
      self.board.serial.write(b"\r")
      time.sleep(0.1)
      self.board.serial.read(self.board.serial.inWaiting())
      
      # Since µP 1.14 the LEGO spike does not respond with the
      # "more information ..." message to CTRL-B. Earlier versions of its firmware did ...
      self.board.serial.write(b"\x02")      
      data = self.board.read_until(1, b"\r\n>>> ")
      if data.endswith(b"\r\n>>> "):
         self.interact = True
         self.queue.put( ( "interactive", True ) )  # tell console that we are now interactive

         # cut any leading newlines
         while data.startswith(b"\r\n"):
            data = data[2:]
         
         self.send_console(data)
         
         while self.interact:
            num = self.board.serial.inWaiting()
            if num > 0:
               self.send_console(self.board.serial.read(num))
            time.sleep(0.01)
      else:
         raise RuntimeError(self.tr("Failed to enter repl"))

      self.send_result(True)
      
   def start_interactive(self):
      self.do_in_thread(self.func_interactive)

   def func_connect(self, port):
      self.board = self.probe(port)
      self.send_result(self.board != None)
      
   def connect(self, port):
      self.do_in_thread(self.func_connect, (port,))
      
   def cmd(self, cmd, cb, parms = None):
      self.progress.emit(-1)

      self.cb = cb   # save callback for later usage
      
      if cmd == Board.SCAN:
         self.scan()
      
      elif cmd == Board.GET_VERSION:
         self.version()

      elif cmd == Board.LISTDIR:
         self.ls()

      elif cmd == Board.GET_FILE:
         # all parms are returned with the callback so the receiving
         # side knows what to do with it
         self.get(parms["name"], parms["size"], parms)
         
      elif cmd == Board.PUT_FILE:
         self.put(parms["code"], parms["name"])

      elif cmd == Board.RUN:
         self.run(parms["name"], parms["code"])

      elif cmd == Board.REPL:
         self.start_interactive()
         
      elif cmd == Board.CONNECT:
         self.connect(parms)
         
   def getPort(self):
      try:
         port = self.board.serial.port
      except:
         port = "<unknown>"
         
      return port

   def getPorts(self):
      return serial.tools.list_ports.comports() 
   
   def close(self):
      if self.interact:
         self.interact = False
         time.sleep(.1)
         
      # kill any running thread
      if self.worker_thread:
         try:
            self.worker_thread.join(1)
         except:
            pass

      if self.board:
         self.board.close()
         self.board = None
