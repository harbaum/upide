#!/usr/bin/env python3
#
# upide.py
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
# Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import os, sys, time
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from board import Board
from fileview import FileView
from console import Console
from editors import Editors
from esp_installer import EspInstaller

class Window(QMainWindow):
   def __init__(self, app):
      super(Window, self).__init__()
      self.initUI()
      app.aboutToQuit.connect(self.on_exit)

   def on_exit(self):
      self.board.close()

   def closeEvent(self, event):
      if self.editors.isModified():      
         qm = QMessageBox()
         ret = qm.question(self,'Really quit?', "Your workspace contains unsaved changes. Really quit?", qm.Yes | qm.No)
         if ret == qm.No:
            event.ignore();
            return

      event.accept()

   def resource_path(self, relative_path):
      if hasattr(sys, '_MEIPASS'):
         return os.path.join(sys._MEIPASS, relative_path)
      return os.path.join(os.path.abspath('.'), relative_path)

   def on_board_request(self, busy):
      # a board request is to be started. Disable all parts of the
      # UI that might interfere with this

      # clear console on command start
      if busy: self.console.clear()
      
      # disable all run buttons during busy. Enable all of them
      # afterwards. One may become a stop button in the meantime.
      self.editors.set_run_mode(not busy)  # disable all run buttons

      # show progress bar while busy. This initially shows an
      # "unspecified" busy bar. Once an action starts returning
      # more progress information it may become a percentage bar
      self.progress(busy)

      # Disable all file system interaction while busy
      self.fileview.disable(busy)      
   
   def on_save_done(self, success = None):
      self.on_board_request(False)
      if success:
         self.status("Saved "+self.code["name"]);
         self.editors.saved(self.code["name"])
         self.fileview.saved(self.code["name"], len(self.code["code"]))
         self.code = None
      else:
         self.status("Saving aborted with error");
      
   def on_save(self, name, code):
      self.code = { "name": name, "code": code }
      
      # User has requested to save the code he edited
      self.on_board_request(True)
      self.board.cmd(Board.PUT_FILE, self.on_save_done, { "name": name, "code": code } )
      
   def on_code_downloaded(self):
      # code to be run has been downloaded to the board:
      # Thus make run button a stop button
      self.editors.set_run_mode(False, self.code["name"])
      # and allow the console to react on key presses
      self.console.enable_input(True)

   def on_run_done(self, success):
      self.on_board_request(False)
      self.console.enable_input(False)
      self.editors.focus() # give focus back to topmost editor
      if success: self.status("Code execution successful");
      else:       self.status("Code execution aborted with error");

   def on_run(self, name, code):
      # User has requested to run the current code
      self.code = { "name": name, "code": code }
      
      self.status("Running code ...");
      self.board.code_downloaded.connect(self.on_code_downloaded)
      self.on_board_request(True)
      self.board.cmd(Board.RUN, self.on_run_done, { "name": name, "code": code } )
      
   def on_stop(self):
      # User has requested to stop the currently running code
      self.board.stop()
      
      # file has been loaded on user request
   def on_file(self, success, result=None):
      self.on_board_request(False)
      if success:
         self.editors.new(result["name"], result["code"])

      # user has triggered a file load
   def on_open(self, name, size):
      # check if this file is already loaded
      if self.editors.exists(name):
         # "new" will bring an existing window to front if it exists which we
         # now know for sure in this case. We don't have to give the code again
         # in this case
         self.editors.new(name)
      else:
         if size >= 0:
            # if size is > 0 this is an existing file, so load it
            self.on_board_request(True)
            self.board.cmd(Board.GET_FILE, self.on_file, { "name": name, "size": size } )
         else:
            # else it's a newly created file
            self.editors.new(name)

      # user wants to create a new directory
   def on_mkdir(self, name):
      try:
         self.board.mkdir(name)
      except Exception as e:
         self.on_error(None, str(e))
      
   def on_delete(self, name):
      # close tab if present
      self.editors.close(name)
      try:
         self.board.rm(name)
      except Exception as e:
         self.on_error(None, str(e))
      
   def on_rename(self, old, new):
      self.editors.rename(old, new)
      try:
         self.board.rename(old, new)
      except Exception as e:
         self.on_error(None, str(e))

   def on_message(self, msg):
      msgBox = QMessageBox(QMessageBox.Critical, "Error", msg, parent=self)
      msgBox.exec_()

   def on_do_flash(self):
      # user has decided to really flash. So we close the serial connection
      self.board.close()
      
   def on_firmware(self):
      if EspInstaller.esp_flash_dialog(self.on_do_flash):

         # close all editor tabs, clear the console and refresh the file view
         
         # disable most gui elements until averything has been reloaded
         self.on_board_request(True)
      
         self.editors.closeAll()

         # start scanning for board
         self.progress(None)
         self.board.cmd(Board.SCAN, self.on_scan_result)

   def mainWidget(self):
      vsplitter = QSplitter(Qt.Vertical)      
      hsplitter = QSplitter(Qt.Horizontal)

      # add stuff here
      self.fileview = FileView()
      self.fileview.open.connect(self.on_open)
      self.fileview.delete.connect(self.on_delete)
      self.fileview.mkdir.connect(self.on_mkdir)
      self.fileview.rename.connect(self.on_rename)
      self.fileview.message.connect(self.on_message)
      self.fileview.firmware.connect(self.on_firmware)
      hsplitter.addWidget(self.fileview)
      hsplitter.setStretchFactor(0, 1)

      self.editors = Editors()
      self.editors.run.connect(self.on_run)
      self.editors.save.connect(self.on_save)
      self.editors.stop.connect(self.on_stop)
      self.editors.closed.connect(self.fileview.on_editor_closed)
      hsplitter.addWidget(self.editors)
      hsplitter.setStretchFactor(1, 10)

      vsplitter.addWidget(hsplitter)
      vsplitter.setStretchFactor(0, 10)

      # the console is at the bottom
      self.console = Console()
      vsplitter.addWidget(self.console)
      vsplitter.setStretchFactor(1, 1)
      
      return vsplitter

   def status(self, str):
      self.statusBar().showMessage(str);      

   def on_listdir(self, success, files=None):
      self.on_board_request(False)
      if success:
         self.fileview.set(files)      
      
   def on_version(self, success, version=None):
      self.status(self.board.getPort() + " connected, MicroPython V{} on {}".format(version[2], version[0]));
      self.fileview.sysname(version[0])
      self.on_board_request(False)

      # version received, request files
      self.on_board_request(True)
      self.board.cmd(Board.LISTDIR, self.on_listdir)

   def on_retry_dialog_button(self, btn):
      if btn.text() == "Flash...":
         # the error is reported in the console
         if EspInstaller.esp_flash_dialog(self.on_do_flash, self):
            # disable most gui elements until averything has been reloaded
            self.on_board_request(True)
      
            # re-start scanning for board
            self.progress(None)
            self.board.cmd(Board.SCAN, self.on_scan_result)
         else:
            # user doesn't want to flash. So there's not much we can do
            self.close()
      
   def on_detect_failed(self):
      self.msgBox = QMessageBox(QMessageBox.Question, 'No board found',
                           "No MicroPython board was detected! "+
                           "Do you want to flash the MicroPython firmware or retry "+
                           "searching for a MicroPython board?", parent=self)
      self.msgBox.addButton(self.msgBox.Retry)
      self.msgBox.addButton("Flash...", self.msgBox.YesRole)
      b = self.msgBox.addButton(self.msgBox.Cancel)
      self.msgBox.setDefaultButton(b)
      self.msgBox.buttonClicked.connect(self.on_retry_dialog_button)
      ret = self.msgBox.exec_()

      if ret ==  QMessageBox.Retry:
         self.on_board_request(True)
         self.progress(None)
         self.board.cmd(Board.SCAN, self.on_scan_result)
         return

      if ret ==  QMessageBox.Cancel:
         self.close()
      
   def on_scan_result(self, success):
      self.status("Search done")
      self.on_board_request(False)

      if success:
         self.on_board_request(True)
         self.board.cmd(Board.GET_VERSION, self.on_version)
      else:
         # trigger failure dialog via timer to not block the gui
         # with the following dialogs
         self.timer = QTimer()
         self.timer.setSingleShot(True)
         self.timer.timeout.connect(self.on_detect_failed)
         self.timer.start(500)
         
   def on_console(self, a):
      self.console.appendBytes(a)
      
   def on_error(self, name, msg):
      # assume the error message is an exception and try to parse
      # it as such. If that fails just display the message as
      # red text in the console
      
      lines = msg.replace('\r', '').split("\n")

      # ignore line 0:  Traceback (most recent call last):
      # parse line 1..:   File "<stdin>", line 4, in <module>
      # output rest:    ImportError: no module named \'timex\''

      i = 1
      try:
         # jump to last line starting with "file"
         while lines[i].strip().lower().startswith("file"):
            i = i+1

         # extract line number and use that to highlight the line
         # in the editor
         loc = lines[i-1].split(",")
         errline = int(loc[1].strip().split(" ")[1].strip())

         # ctrl-c gives a KeyboardInterrupt: which may be confusing since
         # the user has probably pressed the stop button. So replace
         # the message
         lines[i] = lines[i].replace("KeyboardInterrupt:", "Stopped by user")
         
         self.editors.highlight(name, errline, "\n".join(lines[i:]))
                                
         locstr = name.split("/")[-1] + ", " + ",".join(loc[1:]).strip()+"\n"
         self.console.append(locstr, color="darkred")
         self.console.append("\n".join(lines[i:]), color="darkred")
      except:
         # unable to parse error. Just display the entire message
         self.console.append("\n".join(lines), color="red")

   def progress(self, val=False):
      # val can be False, None/<0 or 0..100
      if val is False:
         self.progressBar.setVisible(False)
      else:
         self.progressBar.setVisible(True)
         if val is None or val < 0:
            self.progressBar.setMaximum(0)
         else:
            if val > 100: raise RuntimeError("PROEX " + str(val))      
            self.progressBar.setMaximum(100)
            self.progressBar.setValue(val)            

   def initUI(self):
      self.setWindowTitle("µPIDE - Micropython IDE")

      # add a progress bar to the status bar. This will be used to
      # indicate that the board is being communicated with
      self.progressBar = QProgressBar()
      self.progressBar.setFixedWidth(128)
      self.progressBar.setFixedHeight(16)
      self.progress(False)
      self.statusBar().addPermanentWidget(self.progressBar);
      
      self.setCentralWidget(self.mainWidget())
      self.resize(640,480)
      self.status("Starting ...");

      # setup board interface
      self.board = Board()      
      self.console.input.connect(self.board.input)
      self.board.console.connect(self.on_console)
      self.board.progress.connect(self.progress)
      self.board.error.connect(self.on_error)
      self.board.status.connect(self.status)

      # start scanning for board
      self.progress(None)
      self.on_board_request(True)
      self.board.cmd(Board.SCAN, self.on_scan_result)

      self.show()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   a = Window(app)
   sys.exit(app.exec_())
