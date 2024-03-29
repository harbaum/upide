#!/usr/bin/env python3
#
# esp_installer.py
# 
# Copyright (C) 2021 Till Harbaum <till@harbaum.org>
# https://github.com/harbaum/upide
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

import sys, io, os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtNetwork import *

import json
from argparse import Namespace
import hashlib
import traceback

ESPROM_BAUD=115200

import platform
import serial.tools.list_ports
import serial, time
import re

import esptool

# run esptool in the background
class EspThread(QThread):
   done = pyqtSignal(bool)
   alert = pyqtSignal(dict)

   def __init__(self, config):
      super().__init__()
      self.config = config

   def resource_path(self, relative_path):
      if hasattr(sys, '_MEIPASS'):
         return os.path.join(sys._MEIPASS, relative_path)
      return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
      
   def md5sum(self, fname, sum):
      hash_md5 = hashlib.md5()
      with open(fname, "rb") as f:
         for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

      sumhex = hash_md5.hexdigest().lower()
      if sumhex != sum.lower():
         print("MD5SUM:", sumhex)
      return sumhex == sum.lower()
           
   def run(self):
      esp = None
      args = None
      vargs = None
      ok = False
      
      try:
         # build the args namespace esptool expects
         args = Namespace()

         # copy all enties from setup file
         for a in self.config["parms"]:
            setattr(args, a, self.config["parms"][a])

         f = self.config["parms"]["addr_filename"]

         # verify md5 sum
         if "tempFile" in self.config:
            fname = self.config["tempFile"]
         else:
            fname = self.resource_path("assets/firmware/"+f[1])
            
         if len(f) > 2 and not self.md5sum(fname, f[2]):
            raise ValueError("MD5 sum verification of firmware file {} failed!".format(f[1]))
            
         # open firmware file
         args.addr_filename = [ (f[0], open(fname, "rb")) ]
         
         esp = esptool.get_default_connected_device(serial_list=[self.config["port"]], port=self.config["port"], initial_baud=ESPROM_BAUD, chip=args.chip, connect_attempts=args.connect_attempts)

         print("Chip is %s" % (esp.get_chip_description()))
         print("Features: %s" % ", ".join(esp.get_chip_features()))
         print("Crystal is %dMHz" % esp.get_crystal_freq())
         esptool.read_mac(esp, args)
         esp = esp.run_stub()

         if args.baud > ESPROM_BAUD:
            esp.change_baud(args.baud)

         esptool.detect_flash_size(esp, args)
         if args.flash_size != 'keep':
            esp.flash_set_parameters(esptool.flash_size_bytes(args.flash_size))

         esptool.write_flash(esp, args)            
         esp.hard_reset()

         esp._port.close()

         ok = True
         
      except Exception as e:
         self.alert.emit( {
            "title": "esptool",
            "message": "Esptool flash error",
            "info": str(e),
            "detail": traceback.format_exc()
         } )

      if esp:
         esp._port.close()

      try:
         if hasattr(args, "addr_filename"):
            args.addr_filename[0][1].close()
      except:
         pass
                                
      self.done.emit(ok)
      
# listen for text output of background processes
class ListenerThread(QThread):
   msg = pyqtSignal(str)
   progress = pyqtSignal(int)
   
   def __init__(self, config = None):
      super().__init__()
      self.config = config
         
   def run(self):
      while not self.config["wfd"].closed:
         try:
            while True:
               line = self.config["rfd"].readline()
               if len(line) == 0: break

               # progress text has the form "Writing at 0xxxxxxxx..(xx %)               
               if line.startswith("Writing"):
                  try:
                     val = int(line.split("(")[1].split("%")[0].strip())
                     self.progress.emit(val)
                  except:
                     pass
               
               self.msg.emit(line)
         except:
            break
         
class EspInstaller(QVBoxLayout):
   def __init__(self, parent=None, cb=None, sysname=None, port=None):
      super().__init__(parent)

      self.cb = cb
      self.savedSize = { True: None, False: QSize(480,480) }
      self.retval = False
      self.config = { }
      self.sysname = sysname

      parent.setWindowTitle(self.tr("ESP MicroPython Installer"))

      # download firmware.json from github
      self.manager = QNetworkAccessManager()
      self.manager.finished.connect(self.on_network_finished)
      
      self.req = QNetworkRequest(QUrl("https://raw.githubusercontent.com/harbaum/upide/main/firmware.json"))
      self.reply = self.manager.get(self.req)
   
      # create a dropdown list of serial ports ...
      ports = serial.tools.list_ports.comports()
      port_w = QWidget()
      portbox = QHBoxLayout()
      portbox.setContentsMargins(0,0,0,0)
      port_w.setLayout(portbox)
      portbox.addWidget(QLabel(self.tr("Port:")))
      self.port_cbox = QComboBox()
      self.port_cbox.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);
      for p in ports: self.port_cbox.addItem(str(p), p)

      # pre-select port if known
      if port is not None:
         for p in ports:
            if port == p.device:
               self.port_cbox.setCurrentText(str(p))
      
      portbox.addWidget(self.port_cbox, 1)
      self.addWidget(port_w)

      # ... and one for the board type
      board_w = QWidget()
      boardbox = QHBoxLayout()
      boardbox.setContentsMargins(0,0,0,0)
      board_w.setLayout(boardbox)
      boardbox.addWidget(QLabel(self.tr("Type:")))

      self.type_cbox = QComboBox()
      self.type_cbox.currentTextChanged.connect(self.on_sys_changed)
      boardbox.addWidget(self.type_cbox)
      
      self.board_cbox = QComboBox()
      self.board_cbox.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);
      boardbox.addWidget(self.board_cbox, 1)
      self.erase_flash = QCheckBox(self.tr("Erase all data"))
      boardbox.addWidget(self.erase_flash, 0)

      self.addWidget(board_w)

      # the progress bar and the "Show Details" button
      progress_w = QWidget()
      progressbox = QHBoxLayout()
      progressbox.setContentsMargins(0,0,0,0)
      progress_w.setLayout(progressbox)
      self.progressBar = QProgressBar()
      self.progressBar.setEnabled(False)
      progressbox.addWidget(self.progressBar)   
      self.details_but = QPushButton(self.tr("Show details..."))
      self.details_but.pressed.connect(self.onShowHideDetails)
      progressbox.addWidget(self.details_but)      
      self.addWidget(progress_w)
      
      # the main text view is initially hidden
      self.text = QTextEdit()
      self.text.setHidden(True)
      self.text.setReadOnly(True);
      self.text.setText(self.tr("ESP MicroPython installation tool\n"
                                "Please select the appropriate COM port\n"
                                "and the ESP board type you are using.\n"
                                "Finally click the 'Ok' button."))
      self.addWidget(self.text,1)

      # don't stretch at all if text is visible
      self.addStretch(0)

      self.button_box = QDialogButtonBox(
         QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
         Qt.Horizontal,
         self.parent()
      )

      self.status_label = QLabel("")
      self.button_box.layout().insertWidget(0, self.status_label)
  
      self.button_box.accepted.connect(self.accept)
      self.button_box.rejected.connect(self.reject)
      self.addWidget(self.button_box)            

      # disable gui until firmware.json has been loaded
      self.enable_gui(False)
      
   def on_sys_changed(self, sysname):
      self.board_cbox.clear()
      for f in self.config["firmware"]:
         if f["sysname"].upper() == sysname.upper():
            self.board_cbox.addItem(f["board"], f)
      
   def rootElement(self):
      # if parent is a qdialog, then return that (to be closed etc)
      if isinstance(self.parent(), QDialog):
         return self.parent()         
      
      if self.parent().parent() is not None:
         return self.parent().parent()

      return self.parent()
      
   def accept(self):
      # call callback. This is used to tell the main app to close
      # all connections to the board
      if self.cb: self.cb()
      
      self.retval = True
      self.install_firmware()

   def reject(self):
      self.retval = False
      self.rootElement().close()
      
   def resource_path(self, relative_path):
      if hasattr(sys, '_MEIPASS'):
         return os.path.join(sys._MEIPASS, relative_path)
      return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
      
   def start_redirect(self):
      # connection to server thread to receive data
      # self.listener_thread.done.connect(self.on_bg_done)
      self._stdout = sys.stdout
      self._stderr = sys.stderr
      
      r, w = os.pipe()
      r, w = os.fdopen(r, 'r'), os.fdopen(w, 'w', 1)
      self._r = r
      self._w = w
      sys.stdout = self._w
      sys.stderr = self._w

      self.listener_thread = ListenerThread(
         { "text": self.text_out,
           "wfd": self._w,
           "rfd": self._r
         })
      self.listener_thread.msg.connect(self.text_out);
      self.listener_thread.progress.connect(self.espt_progress);
      self.listener_thread.start()

   def stop_redirect(self):
      self._w.close()
      self.listener_thread.wait()
      self._r.close()
      sys.stdout = self._stdout
      sys.stderr = self._stderr

   def progress(self, perc):
      if perc is None:
         self.progressBar.setEnabled(False)
      else:
         self.progressBar.setEnabled(True)      
         self.progressBar.setValue(perc)
      
   def espt_progress(self, perc):
         self.progress(perc)
      
   def alert(self, data):
      msg = QMessageBox()
      msg.setIcon(QMessageBox.Critical)
      if "title" in data: msg.setWindowTitle(data["title"])
      if "message" in data: msg.setText(data["message"])
      if "info" in data: msg.setInformativeText(data["info"])
      if "detail" in data: msg.setDetailedText(data["detail"])
      msg.exec_()
      
   def windows_full_port_name(self, portname):
      m = re.match("^COM(\d+)$", portname)
      if m and int(m.group(1)) < 10: return portname
      else: return "\\\\.\\{0}".format(portname)

   def get_port(self):
      port = self.port_cbox.currentData().device;
      # On Windows fix the COM port path name for ports above 9 (see comment in
      # windows_full_port_name function).
      if platform.system() == "Windows":
         port = self.windows_full_port_name(port)

      return port

   def on_install_ok(self):
      QMessageBox().information(self.rootElement(),
                                self.tr('Installation done'),
         self.tr("The MicroPython installation finished successfully"),
                                QMessageBox().Ok)
      self.rootElement().close()
            
   def on_esptool_done(self, state):
      self.stop_redirect()
      if state:
         self.status_label.setStyleSheet("color: green;");
         self.status_label.setText(self.tr("Firmware installed successfully"));
      else:
         self.status_label.setStyleSheet("color: red;");
         self.status_label.setText(self.tr("Firmware installation failed"));
         self.enable_gui(True)

      if state:
         self.text_out(self.tr("Waiting for firmware to boot ...\n"))
         self.timer = QTimer()
         self.timer.setSingleShot(True)
         self.timer.timeout.connect(self.on_install_ok)
         self.timer.start(3000)

   def enable_gui(self, enable):
      self.button_box.setEnabled(enable)
      self.port_cbox.setEnabled(enable)
      self.type_cbox.setEnabled(enable)
      self.board_cbox.setEnabled(enable)
      self.erase_flash.setEnabled(enable)
         
   def on_network_progress(self, br, bt):
      if bt: self.text_out("Downloading: " + str(100*br//bt) + "%\n")
      
   def on_network_finished(self, reply):
      config = reply.property("config")

      # a config property is only present if a firmware has been downloaded
      # otherwise this was the download of the firmware.json
      if config:
         if reply.error() == QNetworkReply.NoError:
            # write reply into temporary file
            self.fileTemp = QTemporaryFile()
            self.fileTemp.open()
            config["tempFile"] = self.fileTemp.fileName()         
            self.fileTemp.writeData(reply.readAll())
            self.fileTemp.close()
         
            self.flash(config)
         else:
            self.text_out(self.tr("Download error") + ": " + str(reply.error())+"\n")
            self.text_out(reply.errorString()+"\n")

            self.alert( { "title": self.tr("Download error"), "message": reply.errorString() } )
         
            self.status_label.setStyleSheet("color: red;");
            self.status_label.setText(self.tr("Download failed"));
            self.enable_gui(True)

      else:
         if reply.error() == QNetworkReply.NoError:
            
            # load firmware config
            try:
               self.config["firmware"] = json.loads(str(reply.readAll(), 'utf-8'))
            except:
               self.status_label.setStyleSheet("color: red;");
               self.status_label.setText(self.tr("Download failed"));

               # enable only the cancel button
               self.button_box.setEnabled(True)
               self.button_box.button( QDialogButtonBox.Ok ).setEnabled(False)

               return
            
            # finish gui setup
            
            # find all sysnames in this
            sysnames = [ ]
            for f in self.config["firmware"]:
               if f["sysname"] not in sysnames:
                  sysnames.append(f["sysname"])
               
            # todo: move this out of here
            if self.sysname is not None and self.sysname.upper() not in sysnames:
               if QMessageBox().information(self.rootElement(),
                                            self.tr('Unsupported system'),
                                            self.tr("Your board \"{}\" doesn't seem to be supported by "
                                                    "the ESP flasher. Do you really want to proceed?").format(sysname),
                  QMessageBox().Yes | QMessageBox().No) == QMessageBox().No:
                  self.fail = True      # init has failed
                  return
               
            for s in sysnames: self.type_cbox.addItem(s)
            if self.sysname is not None and self.sysname.upper() in sysnames:
               self.type_cbox.setCurrentText(self.sysname.upper())

            self.enable_gui(True)
         else:
            self.text_out(self.tr("Download error") + ": " + str(reply.error())+"\n")
            self.text_out(reply.errorString()+"\n")

            self.alert( { "title": self.tr("Download error"), "message": reply.errorString() } )
         
            self.status_label.setStyleSheet("color: red;");
            self.status_label.setText(self.tr("Download failed"));

            # enable only the cancel button
            self.button_box.setEnabled(True)
            self.button_box.button( QDialogButtonBox.Ok ).setEnabled(False)
            
   # run esptool in the background with output redirection
   def install_firmware(self):
      self.text.clear();
      self.enable_gui(False)
      self.progress(0)

      self.status_label.setStyleSheet(None);
      self.status_label.setText(self.tr("Flashing firmware"));

      config = { }
      # get flash parameters from gui
      config["parms"] = self.board_cbox.currentData()["parms"]

      # overwrite erase_all setting on user request
      if self.erase_flash.isChecked():
         config["parms"]["erase_all"] = True

      # check if the filename is actually a url and we need to
      # download the file first
      if config["parms"]["addr_filename"][1].lower().startswith("http"):
         self.text_out(self.tr("Downloading ") + str(config["parms"]["addr_filename"][1].split("/")[-1])+"\n")

         # download into a temporary file
         self.req = QNetworkRequest(QUrl(config["parms"]["addr_filename"][1]))
         self.reply = self.manager.get(self.req)
         self.reply.setProperty("config", config)
         self.reply.downloadProgress.connect(self.on_network_progress)
      else:
         self.flash(config)

   def flash(self, config):         
      # get port from gui
      config["port"] = self.get_port()
      self.thread = EspThread(config)

      # connection to server thread to receive data
      self.start_redirect()
      self.thread.alert.connect(self.alert)
      self.thread.done.connect(self.on_esptool_done)
      self.thread.start()

   def text_out(self, str, color=None):
      self.text.moveCursor(QTextCursor.End)
      if not hasattr(self, 'tf') or not self.tf:
         self.tf = self.text.currentCharFormat()
      if color:
         tf = self.text.currentCharFormat()
         tf.setForeground(QBrush(QColor(color)))
         self.text.textCursor().insertText(str, tf);
      else:
         self.text.textCursor().insertText(str, self.tf);

   def on_request_resize(self):
      if self.savedSize[self.text.isHidden()] and self.rootElement():
         self.rootElement().resize(self.savedSize[self.text.isHidden()])
         
   def onShowHideDetails(self):
      # show/hide the text detail box
      self.savedSize[self.text.isHidden()] = self.rootElement().size()
         
      if self.text.isHidden():
         self.text.setHidden(False)         
         self.details_but.setText(self.tr("Hide details..."))
      else:
         self.text.setHidden(True)
         self.details_but.setText(self.tr("Show details..."))
         
      self.shrinktimer = QTimer()
      self.shrinktimer.setSingleShot(True)
      self.shrinktimer.timeout.connect(self.on_request_resize)
      self.shrinktimer.start(10)
         
   def esp_flash_dialog(cb, sysname=None, port=None, parent=None):
      dialog = QDialog(parent)
      dialog.resize(500,140)
      installer = EspInstaller(dialog, cb, sysname, port)
      if hasattr(installer, "fail"): return False
      dialog.setLayout(installer)
      dialog.setWindowModality(Qt.ApplicationModal)
      dialog.exec_()
      return installer.retval
   
if __name__ == '__main__':
   app = QApplication(sys.argv)
   win = QMainWindow()
   esp_widget = QWidget()
   esp_widget.setLayout(EspInstaller(esp_widget))   
   win.setCentralWidget(esp_widget)
   win.resize(400,140)
   win.setWindowTitle("ESP MicroPython Installer")
   win.show()

   sys.exit(app.exec_())
