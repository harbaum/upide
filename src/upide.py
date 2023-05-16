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

import os, sys, time, hashlib
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from board import Board
from fileview import FileView
from console import Console
from editors import Editors
from esp_installer import EspInstaller
import zipfile

class Window(QMainWindow):
   def __init__(self, app, flags):
      super(Window, self).__init__()

      self.flags = flags

      # try to load settings
      self.settings = QSettings('upide', 'settings')
      
      self.initUI()
      app.aboutToQuit.connect(self.on_exit)
      self.sysname = None

   def on_exit(self):
      self.board.close()

   def closeEvent(self, event):
      if self.editors.isModified():      
         qm = QMessageBox()
         ret = qm.question(self,self.tr('Really quit?'),
                           self.tr("Your workspace contains unsaved changes.")+
                           "\n"+self.tr("Really quit?"), qm.Yes | qm.No)
         if ret == qm.No:
            event.ignore();
            return

      # keep any unsaved data ...
      self.settings.setValue('unsaved', self.editors.getUnsaved())
      
      # save window related settings
      self.settings.setValue('window_geometry', self.saveGeometry())
      self.settings.setValue('window_state', self.saveState())
      self.settings.setValue('window_hsplitter', self.hsplitter.saveState())
      self.settings.setValue('window_vsplitter', self.vsplitter.saveState())
      
      # save info about open editors
      self.settings.setValue('editor_open', self.editors.getAll())
      self.settings.setValue('editor_current', self.editors.get_current())
      
      event.accept()

   def resource_path(relative_path):
      if hasattr(sys, '_MEIPASS'):
         return os.path.join(sys._MEIPASS, relative_path)
      return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

   def on_board_request(self, busy):
      # a board request is to be started. Disable all parts of the
      # UI that might interfere with this

      # clear console on command start
      if busy: self.console.clear()
      
      # disable all run buttons during busy. Enable all of them
      # afterwards. One may become a stop button in the meantime.
      self.editors.set_button(None if busy else True)  # hide run buttons

      # show progress bar while busy. This initially shows an
      # "unspecified" busy bar. Once an action starts returning
      # more progress information it may become a percentage bar
      self.progress(busy)

      # Disable all file system interaction while busy
      self.fileview.disable(busy)      
   
   def on_save_done(self, success, data = None):
      self.on_board_request(False)
      self.console.set_button(True)
      if success:
         self.status(self.tr("Saved {}").format(self.code["name"]))
         if self.code["new_file"]:
            # add file to file view
            self.fileview.add(self.code["name"], len(self.code["code"]))
         else:
            # update existing info
            self.fileview.saved(self.code["name"], len(self.code["code"]))
               
         # example extra files have the "no_edit" flag set since they
         # are not supposed to be opened in the editor after being imported
         if not self.code["no_edit"]:
            if self.code["new_file"]:
               # open a editor view for the new file
               self.editors.new(self.code["name"], True, self.code["code"])
            else:
               # update existing editor
               self.editors.saved(self.code["name"], self.code["code"], self.code["user_triggered"])

         # something might have to happen after the file has been saved. E.g.
         # another example file is to be downloaded and saved. This is handled
         # in the callback
         cb = self.code["callback"]
         ctx = self.code["context"]
         self.code = None

         if cb: cb(ctx)
      else:
         self.status(self.tr("Saving aborted with error"));
      
   def on_save_button_clicked(self, name, code):
      self.on_save(name, code, user_triggered = True)

   def on_save(self, name, code, new_file=False, cb=None, ctx = None, no_edit = False, user_triggered = False):
      # There may be further user edits to the file during the process of saving it. This
      # is special as imported files need to update a related editor after the import as
      # the import has probably changed file contents which need to be reflected in the
      # editor. But if this was a user triggered save then things are different and we don't
      # want the edits during the saving to be overwritten with the contents of the recently
      # saved file.      
      self.code = { "name": name, "code": code, "new_file": new_file, "callback": cb,
                    "context": ctx, "no_edit": no_edit, "user_triggered": user_triggered }
      
      # User has requested to save the code he edited
      self.on_board_request(True)
      self.console.set_button(None)
      self.board.cmd(Board.PUT_FILE, self.on_save_done, { "name": name, "code": code } )
      
   def on_code_downloaded(self):
      # code to be run has been downloaded to the board:
      # Thus make all run buttons into stop buttons
      self.editors.set_button(False)
      # and allow the console to react on key presses
      self.console.enable_input(True)

   def on_run_done(self, success, data=None):
      # "run done" means the running program has been stopped
      # so a "stop" timeout may be pending. Cancel that as stop
      # was successful
      if hasattr(self, "stop_timer") and self.stop_timer:
         self.stop_timer.stop()
         self.stop_timer = None
      
      self.on_board_request(False)
      self.console.set_button(True)
      self.console.enable_input(False)
      self.editors.focus() # give focus back to topmost editor
      if success: self.status(self.tr("Code execution successful"));
      else:       self.status(self.tr("Code execution aborted with error"));

   def on_run(self, name, code):
      # User has requested to run the current code
      self.code = { "name": name, "code": code }
      
      self.status(self.tr("Running code ..."));
      self.on_board_request(True)
      self.console.set_button(None)
      self.board.cmd(Board.RUN, self.on_run_done, { "name": name, "code": code } )

   def on_stop_timeout(self):
      # the stop command has run into a timeout. Force the board communication
      # thread to stop.
      self.board.forceStop();
      self.stop_timer = None
      
   def on_stop(self):
      # User has requested to stop the currently running code
      self.editors.set_button(None)
   
      # if may actually not be possible to stop the program as it may
      # have quietly stopped e.g. due to a board reset. So start a one second
      # timeout to cope with this
      self.stop_timer = QTimer()
      self.stop_timer.setSingleShot(True)
      self.stop_timer.timeout.connect(self.on_stop_timeout)
      self.stop_timer.start(1000)
      
      self.board.stop()
      
      # file has been loaded on user request
   def on_file(self, success, result=None):
      self.on_board_request(False)
      self.console.set_button(True)
      self.status()
      if success:
         # loading the new editor automatically raises it         
         if "error" in result:
            self.editors.new(result["name"], result["error"]["scroll_to"], result["code"])
            self.editors.highlight(result["name"], result["error"]["line"],
                                   result["error"]["scroll_to"], result["error"]["msg"])
         else:
            self.editors.new(result["name"], True, result["code"])

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
            # if size is >= 0 this is an existing file, so load it
            self.on_board_request(True)
            self.console.set_button(None)
            self.board.cmd(Board.GET_FILE, self.on_file, { "name": name, "size": size } )
         else:
            # else it's a newly created file
            self.editors.new(name)

   def backup_done(self, ok, msg = ""):
      # TODO: ask user to keep the remaining files
      if len(self.zip_old):
         print("ZIP remains:")
         for f in self.zip_old:
            print("  ", f)
            
      if ok: self.status(self.tr("Backup successful"))
      else:  self.status(self.tr("Backup failed: ") + msg)
      # re-enable UI     
      self.on_board_request(False)
      self.console.set_button(True)

      if self.zip:
         self.zip.close()
         self.zip = None

   def on_backup_file(self, success, ctx):
      if not success:
         # backup failed
         self.backup_done(False, "Board com failed")
         return

      try:
         # write file to zip, but without leading slash
         name = ctx["name"]
         if name.startswith("/"):
            name = name[1:]
         
            # if we got a fresh file, then forget about the old one
            # from the zip
            try:
               self.zip_old.pop(name)
            except:
               pass
               
         with self.zip.open(name, mode='w') as f:
            f.write(ctx["code"])
            f.close()
      except Exception as e:
         self.backup_done(False, str(e))
         return
            
      # backup next file
      self.backup_next_file(ctx["name"])

   def backup_file(self, f):
      if not f:
         # no more file to backup
         self.backup_done(True)
         return

      # get file node
      node = self.fileview.findNode(f)
      if not node:
         # problem getting file node
         print("ERROR getting node for", f)
         self.backup_done(False, "No node")
         return
         
      self.status(self.tr("Backing up {}").format(f.split("/")[-1]))
      self.console.appendFinal(self.tr("Backing up {}").format(f) + "\n", None)
      self.board.cmd(Board.GET_FILE, self.on_backup_file, { "name": f, "size": node.size } )

   def backup_get_old_hash(self, f):
      if f.lstrip("/") in self.zip_old:      
         return hashlib.sha1(self.zip_old[f.lstrip("/")]).digest()

      return None
      
   def backup_next_file(self, cur=None):
      f = self.fileview.get_next_file(cur)

      # check if we work on an existing backup
      if hasattr(self, "hashes") and self.hashes:      
         while f != None and self.backup_get_old_hash(f) == self.hashes[f]:
            self.status(self.tr("Unmodified {}").format(f.split("/")[-1]))
            self.console.appendFinal(self.tr("Unmodified {}").format(f) + "\n", None)
      
            # save existing from old zip
            name = f.lstrip("/")
            with self.zip.open(name, mode='w') as zf:
               zf.write(self.zip_old[name])
               zf.close()
               self.zip_old.pop(name)

            f = self.fileview.get_next_file(f)

      self.backup_file(f)
      
   def on_backup_hash(self, success, hashes=None):
      self.hashes = hashes

      # start backup with first file
      self.backup_next_file()
         
      # user wants to make a full backup
   def on_backup(self):            
      # select a zip file to backup into
      fname = QFileDialog.getSaveFileName(self, self.tr('Create backup'),'.',self.tr("Backup archive (*.zip)"))[0]
      if fname:
         if not fname.lower().endswith(".zip"):
            fname = fname + ".zip"

         # disable gui during backup
         self.on_board_request(True)
         self.console.set_button(None)

         try:
            # try to open zip and retrieve it's contents to allow
            # for SHA1 comparison and omit downloading existing files
            self.zip_old = {}
            try:
               zip = zipfile.ZipFile(fname, 'r')
               files = zip.namelist()

               # read all files into memory
               for file in files:
                  with zip.open(file, 'r') as f:
                     self.zip_old[file] = f.read()
                     f.close()
            
               zip.close()

               # open new zip for writing, overwriting the old one
               self.zip = zipfile.ZipFile(fname, 'w')
            
               # get all hashes from device to check which files are
               # unmodified in the existing backup
               self.status(self.tr("Preparing backup"))
               self.board.cmd(Board.HASH, self.on_backup_hash, self.fileview.number_of_files())
               return
         
            except:
               pass

            self.zip = zipfile.ZipFile(fname, 'w')
         except Exception as e:
            self.backup_done(False, str(e))
            return

         # start backup with first file
         self.hashes = None  # no old backup, so no need for hashes
         f = self.fileview.get_next_file()
         self.backup_file(f)

   def eventFilter(self, obj, event):
      if event.type() == QEvent.MouseButtonRelease:
         index = self.cbox.view().currentIndex().row()
         if self.cbox.itemData(index, Qt.CheckStateRole) == Qt.Checked:
            self.cbox.setItemData(index, Qt.Unchecked, Qt.CheckStateRole)                                  
         else:
            self.cbox.setItemData(index, Qt.Checked, Qt.CheckStateRole)
            
         return True
      
      return super().eventFilter(obj, event)
         
   def restore_done(self, ok):
      if ok: self.status(self.tr("Restoration successful"))
      else:  self.status(self.tr("Restoration failed"))

      if self.zip:
         self.zip.close()
         self.zip = None

      if len(self.restore_files_before) > 0:
         # there are files on the device which were not from the backup. Ask user
         # if the user wants them to be removed
         qm = QMessageBox(QMessageBox.Question, self.tr('Remove remaining files?'),
                          self.tr("There are files remaining on the device which were not part of the backup.")+
                          "\n"+self.tr("Do you want these files to be deleted?"),
                          parent=self)
         qm.setStandardButtons(qm.Yes | qm.No)

         # add a checkbox, so we have a known widget we can replace with something else ..
         qm.setCheckBox(QCheckBox("xyz", qm))
         x = qm.layout().getItemPosition(qm.layout().indexOf(qm.checkBox()))

         # create a combobox made of checkboxes
         self.cbox = QComboBox(qm)
         mod = QStandardItemModel(1,0)
         for i in range(len(self.restore_files_before)):         
            item = QStandardItem(self.restore_files_before[i])
            item.setCheckable(True)
            item.setCheckState(Qt.Checked)
            mod.setItem(i,item)         

         # set use checkboxes for combobox and replace checkbox widget with combobox
         self.cbox.setModel(mod)
         self.cbox.setPlaceholderText(self.tr("Files to delete"))
         self.cbox.setCurrentIndex(-1);
         self.cbox.view().viewport().installEventFilter(self)         
         qm.layout().addWidget(self.cbox, x[0], x[1], x[2], x[3])
         
         if qm.exec_() == qm.Yes:
            # get all filenames from combobox
            for i in range(mod.rowCount()):
               f = self.cbox.itemText(i)
               if self.cbox.itemData(i, Qt.CheckStateRole) == Qt.Checked:
                  self.status(self.tr("Deleting: {}").format(f.split("/")[-1])) 
                  self.console.appendFinal(self.tr("Deleting: {}").format(f) + "\n", None)
                  self.board.rm(f)

                  # close the editor if it existed
                  self.editors.close("/"+f)
                  
               else:
                  self.console.appendFinal(self.tr("Keeping: {}").format(f) + "\n", None)
               
      # once done reload the entire fileview. This will also
      # re-enable the ui and reload open files
      self.board.cmd(Board.LISTDIR, self.on_listdir)
      
   def restore_get_next_file(self, f = None):
      files = self.zip.namelist()
      if not f:
         # no filename give -> restore first file
         idx = -1
      else:
         idx = files.index(f)
         if idx < 0: return None

      while idx+1 < len(files):
         # don't explicitely restore directories. They
         # are implicitely restored via the file names. This
         # should actually never happen with the backup
         # files as they don't explicitely store directories at all
         fname = files[idx+1]
         if not fname.endswith("/"):
            return fname

         idx = idx + 1
         
      return None
         
   def mkdir(self, name):
      try:
         self.board.mkdir(name)
      except Exception as e:
         return False

      return True

   def on_restore_file(self, success, parms):
      if not success:
         self.restore_done(False)
         return

      self.restore_next_file(self.restore_file_name)

   def mkpath(self, path):
      # treat all paths as absolute
      if path.startswith("/"):
         path = path[1:]
      
      # check if whole path exists
      path_parts = path.split("/")[:-1]
      if len(path_parts) > 0:
         # check if path already exists
         for i in range(len(path_parts)):
            check_path = "/" + "/".join(path_parts[:i+1])
            if not self.fileview.exists(check_path):
               if self.mkdir(check_path):
                  self.fileview.add_dir_entry(check_path)
               else:
                  return False
               
      return True      
      
   def restore_file(self, f):
      self.status(self.tr("Restoring {}").format(f.split("/")[-1]))
      self.console.appendFinal(self.tr("Restoring {}").format(f) + "\n", None)

      # check if this file is in list of previous installed files (file was
      # already there) and remove it from that list
      if f in self.restore_files_before:
         self.restore_files_before.remove(f)
   
      if not self.mkpath(f):
         # failed to create directory. Abort restore
         self.restore_done(False)
         return
      
      # full path should now exist, so restore file      
      try:
         with self.zip.open(f, 'r') as infile:
            data = infile.read()
            infile.close()
            self.restore_file_name = f
            self.editors.update("/"+f, data)
            self.board.cmd(Board.PUT_FILE, self.on_restore_file, { "name": f, "code": data } )
      except Exception as e:
         print("restore exception", str(e))
         self.restore_done(False)
         return

      # user wants to import a file from PC
   def on_file_import(self, dir_name):
      fname = QFileDialog.getOpenFileName(self, self.tr('Import file'),'.',self.tr("Any file (*)"))[0]
      if fname:
         # check if the target file already exists
         new_name = dir_name + "/" + os.path.basename(fname)
         if self.fileview.exists(new_name):
            qm = QMessageBox()
            ret = qm.question(self,self.tr('Really overwrite?'),
                              self.tr("A file with that name already exists.")+
                              "\n"+self.tr("Do you really want to overwrite it?"), qm.Yes | qm.No)
            if ret == qm.No:
               return
         
         self.on_import(fname, new_name)

   def on_export_file(self, success, result=None):
      self.on_board_request(False)
      self.console.set_button(True)
      if success:
         with open(result["fname"], mode='wb') as f:
            f.write(result["code"])
            f.close()
            
            self.status(self.tr("Exported {}").format(os.path.basename(result["fname"])))
         
      # user wants to export a file to PC
   def on_file_export(self, name, size):
      fname = QFileDialog.getSaveFileName(self, self.tr('Export file'),name.split("/")[-1],self.tr("Any file (*)"))[0]
      if fname:
         # if the file exists, check if it's a valid file as e.g. directories
         # cannot be overwritten by regular files. This should actually never happen
         # as QFileDialog should not have allowed the user to select anything but
         # a valid file. Thus we just silently stop here
         if os.path.exists(fname) and not os.path.isfile(fname): return
         
         # start by loading the file into memory
         self.on_board_request(True)
         self.console.set_button(None)
         self.board.cmd(Board.GET_FILE, self.on_export_file, { "name": name, "size": size, "fname": fname } )

   def restore_next_file(self, name=None):
      f = self.restore_get_next_file(name)
      skipped = True

      while f != None and skipped:
         # check if file really needs to be restored or if hash still matches
         if hasattr(self, "hashes") and self.hashes:
            # read file from zip to verify hash
            try:
               with self.zip.open(f, 'r') as infile:
                  hash = hashlib.sha1(infile.read()).digest()
                  infile.close()
            except:
               hash = None

            # file is still identical, so don't restore
            if ("/"+f) in self.hashes and hash == self.hashes["/"+f]:
               self.status(self.tr("Unmodified {}").format(f.split("/")[-1]))
               self.console.appendFinal(self.tr("Unmodified {}").format(f) + "\n", None)

               # check if this file is in list of previous installed files (file was
               # already there) and remove it from that list
               if f in self.restore_files_before:
                  self.restore_files_before.remove(f)

               f = self.restore_get_next_file(f)
            else:
               # file is not already there and thus cannot be skipped
               skipped = False
                  
      if f == None:
         # no more file to restore
         self.restore_done(True)
         return
      
      self.restore_file(f)
      
   def on_restore_hash(self, success, hashes=None):
      self.hashes = hashes
      self.restore_next_file()

      # user wants to restore a full backup
   def on_restore(self):            
      # select a zip file to extract backup from
      fname = QFileDialog.getOpenFileName(self, self.tr('Restore backup'),'.',self.tr("Backup archive (*.zip)"))[0]
      if fname:
         if not fname.lower().endswith(".zip"):
            fname = fname + ".zip"

         # save list of currently installed files
         self.restore_files_before = self.fileview.getFileList()
         
         # disable gui during restore
         self.on_board_request(True)
         self.console.set_button(None)

         try:
            self.zip = zipfile.ZipFile(fname, 'r')
         except Exception as e:
            self.restore_done(False)
            return

         self.hashes = None
         self.status(self.tr("Preparing restoration"))
         self.board.cmd(Board.HASH, self.on_restore_hash, len(self.restore_files_before))
            
   def show_exception(self, e):
      # this was an exception forwarded from the target 
      if len(e.args) == 3 and e.args[0] == "exception":
         self.on_error(None, e.args[2].decode("ascii"))
      else:
         self.on_error(None, str(e))
         
      # user wants to create a new directory
   def on_mkdir(self, name):
      try:
         self.board.mkdir(name)
      except Exception as e:
         self.show_exception(e)

   def on_delete(self, name):
      # close tab if present
      self.editors.close(name)
      try:
         self.board.rm(name)
      except Exception as e:
         self.show_exception(e)
         
   def on_example_saved(self, ctx = None):
      # the example has been saved. next check if there are additional
      # files that need to be imported for this example
      self.fileview.example_import_additional_files(ctx)
         
   def on_example_imported(self, name, code, ctx):
      self.on_save(name, code, True, self.on_example_saved, ctx)

   def on_example_file_saved(self, ctx = None):
      print("example file saved", ctx)
      self.fileview.example_file_saved(ctx)
      
   def on_example_file_imported(self, name, data, ctx):
      # this is special as we might need to create parent
      # directories while the example itself is just saved
      # where the user wanted it to be
      if self.mkpath(name):
         self.fileview.add_file_entry(name, len(data))
         self.on_save(name, data, not self.fileview.exists(name), self.on_example_file_saved, ctx, True )
      
   def on_example(self, name, ctx):
      # user has requested an example to be loaded
      self.fileview.requestExample(name, ctx)
      
   def on_import(self, local, name):
      # load the file into memory
      try:
         with open(local, "rb") as f:
            code = f.read()

            # check if this file already exists
            # check if fileview thinks this is something that can
            # be opened in an editor. Set no_edit flag if not
            self.on_save(name, code, not self.fileview.exists(name),
                         no_edit = not self.fileview.is_editable(name))
      except Exception as e:
         self.on_message(self.tr("Import failed:") + "\n\n" + str(e))
      
   def on_rename(self, old, new):
      try:
         self.board.rename(old, new)
         self.editors.rename(old, new)
      except Exception as e:
         self.show_exception(e)

         # if the rename failed then the internal file tree may now be
         # out of sync, so we reload it
         self.select_file = old
         self.board.cmd(Board.LISTDIR, self.on_rename_listdir)

   def on_rename_listdir(self, success, files=None):
      self.on_listdir(success, files)
      # make source file visible again
      self.fileview.select(self.select_file)
      
   def on_message(self, msg):
      msgBox = QMessageBox(QMessageBox.Critical, self.tr("Error"), msg, parent=self)
      msgBox.exec_()

   def on_do_flash(self):
      # user has decided to really flash. So we close the serial connection
      self.board.close()

   def start_rescan(self):
      # close all editor tabs, clear the console and refresh the file view
         
      # disable most gui elements until averything has been reloaded
      self.on_board_request(True)
      self.console.set_button(None)      
      self.editors.closeAll()
      self.fileview.set(None)

      # start scanning for board
      self.progress(None)
      self.board.cmd(Board.SCAN, self.on_scan_result)
      
   def on_firmware(self):
      if EspInstaller.esp_flash_dialog(self.on_do_flash, self.sysname, self.board.getPort(), self):
         self.start_rescan()
      else:
         # flashing may have failed and the user may not want to retry.
         # Thus the serial port may be closed
         if not self.board.board: 
            self.start_rescan()

   def mainWidget(self):
      self.vsplitter = QSplitter(Qt.Vertical)      
      self.hsplitter = QSplitter(Qt.Horizontal)

      # add stuff here
      self.fileview = FileView()
      self.fileview.open.connect(self.on_open)
      self.fileview.delete.connect(self.on_delete)
      self.fileview.mkdir.connect(self.on_mkdir)
      self.fileview.rename.connect(self.on_rename)
      self.fileview.message.connect(self.on_message)
      self.fileview.firmware.connect(self.on_firmware)
      self.fileview.host_import.connect(self.on_import)
      self.fileview.example_import.connect(self.on_example)
      self.fileview.example_imported.connect(self.on_example_imported)
      self.fileview.example_file_imported.connect(self.on_example_file_imported)
      self.fileview.backup.connect(self.on_backup)
      self.fileview.restore.connect(self.on_restore)
      self.fileview.file_import.connect(self.on_file_import)
      self.fileview.file_export.connect(self.on_file_export)
      self.hsplitter.addWidget(self.fileview)
      self.hsplitter.setStretchFactor(0, 1)
      
      self.editors = Editors()
      self.editors.run.connect(self.on_run)
      self.editors.save.connect(self.on_save_button_clicked)
      self.editors.save_bytes.connect(self.on_save_button_clicked)
      self.editors.stop.connect(self.on_stop)
      self.editors.closed.connect(self.fileview.on_editor_closed)
      self.editors.changed.connect(self.fileview.select)
      self.fileview.selection_changed.connect(self.editors.on_select)
      self.hsplitter.addWidget(self.editors)
      self.hsplitter.setStretchFactor(1, 3)

      self.vsplitter.addWidget(self.hsplitter)
      self.vsplitter.setStretchFactor(0, 10)

      # the console is at the bottom
      self.console = Console()
      self.console.interact.connect(self.on_console_interact)
      
      self.vsplitter.addWidget(self.console)
      self.vsplitter.setStretchFactor(1, 1)

      return self.vsplitter

   def on_repl_done(self, status, msg=""):
      # interactive mode has ended (or failed to enter)
      self.on_board_request(False)
      self.console.set_button(True)
      self.status(self.tr("Interactive mode done"))

   def on_interactive(self):
      # interactive mode has successfully been enabled after
      # user request. So show the stop button
      self.console.set_button(False)
      
   def on_console_interact(self, start):
      self.console.set_button(None)
      if start:
         # clicking the console prompt icon starts repl interaction
         self.on_board_request(True)
         self.board.cmd(Board.REPL, self.on_repl_done)
         self.status(self.tr("Interactive mode active"))
      else:
         self.board.stop()
   
   def status(self, str=""):
      self.statusBar().showMessage(str);      

   def on_all_loaded(self):      
      # re-enable UI
      self.on_board_request(False)
      self.console.set_button(True)

      # there may have been unsaved editor windows
      unsaved = self.settings.value('unsaved')
      if unsaved:
         # now open windows for all unsaved data and mark it as modified         
         for f in unsaved:
            # The same file may already be loaded from
            # the device. Close that one first
            if self.editors.exists(f):
               self.editors.close(f)
            
            self.editors.new(f, True, unsaved[f])           
            self.editors.setModified(f)

   def on_loaded(self, success, result=None):
      # open editor window for this file
      if success:
         self.editors.new(result["name"], True, result["code"])
         self.open_next_file(result["filelist"])
      else:
         self.on_all_loaded()         
      
   def open_next_file(self, filelist):
      # no more files to load?
      if not filelist:
         self.on_all_loaded()
         # bring same editor window to front as previously
         self.editors.on_select(self.settings.value('editor_current'))
         return
            
      # try to open first file in list
      size = self.fileview.get_file_size(filelist[0])
      if size == None:
         self.on_all_loaded()
         return

      self.board.cmd(Board.GET_FILE, self.on_loaded, { "name": filelist[0],
                   "size": size, "filelist": filelist[1:], "quiet": True } )
         
   def on_listdir(self, success, files=None):
      if success:
         self.fileview.set(files)
         
         # try to restore all previously open files
         self.open_next_file(self.settings.value('editor_open'))
      
   def on_version(self, success, version):
      # enable soft reset unless some LEGO device was detected. The reboot of the
      # LEGO firmware does not work properly if the device is rebooted in raw_repl
      if not "lego" in version['nodename'].lower():
         self.board.set_soft_reset(True)
      
      # save last successfully used port in settings
      self.settings.setValue('port', self.board.getPort())
      
      self.status(self.tr("{0} connected, MicroPython V{1} on {2}").format(self.board.getPort(), version['release'], version['nodename']));
      self.fileview.sysname(version['nodename'])
      self.sysname = version['nodename']
      self.on_board_request(False)
      self.console.set_button(True)

      # version received, request files
      self.on_board_request(True)
      self.console.set_button(None)
      self.board.cmd(Board.LISTDIR, self.on_listdir)

   def on_retry_dialog_button(self, btn):
      if btn.text() == self.tr("Flash..."):
         # the error is reported in the console
         if EspInstaller.esp_flash_dialog(self.on_do_flash, parent=self):
            # disable most gui elements until averything has been reloaded
            self.on_board_request(True)
            self.console.set_button(None)
      
            # re-start scanning for board
            self.progress(None)
            self.board.cmd(Board.SCAN, self.on_scan_result)
         else:
            # user doesn't want to flash. So there's not much we can do
            self.close()
      
   def on_detect_failed(self):
      self.msgBox = QMessageBox(QMessageBox.Question, self.tr('No board found'),
                           self.tr("No MicroPython board was detected!")+"\n\n"+
                           self.tr("Do you want to flash the MicroPython firmware or retry "
                                   "searching for a MicroPython board?"), parent=self)
      self.msgBox.addButton(self.msgBox.Retry)
      self.msgBox.addButton(self.tr("Flash..."), self.msgBox.YesRole)
      b = self.msgBox.addButton(self.msgBox.Cancel)
      self.msgBox.setDefaultButton(b)
      self.msgBox.buttonClicked.connect(self.on_retry_dialog_button)
      ret = self.msgBox.exec_()

      if ret ==  QMessageBox.Retry:
         self.on_board_request(True)
         self.console.set_button(None)
         self.progress(None)
         self.board.cmd(Board.SCAN, self.on_scan_result)
         return

      if ret ==  QMessageBox.Cancel:
         self.close()
      
   def on_scan_result(self, success, port=None):
      self.status(self.tr("Search done"))
      self.on_board_request(False)
      self.console.set_button(True)

      if success:
         self.on_board_request(True)
         self.console.set_button(None)
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

         # check if it's a user triggered "KeyboardInterrupt"
         user_irq = False
         for l in lines:
            if "KeyboardInterrupt:" in l:
               user_irq = True
         
         # ctrl-c gives a KeyboardInterrupt: which may be confusing since
         # the user has probably pressed the stop button. So replace
         # the message
         lines[i] = lines[i].replace("KeyboardInterrupt:", self.tr("Stopped by user"))

         # file name is <stdin> for the running script itself. Otherwise it's
         # a real filename
         filename = None
         if len(loc[0].strip().split(" ")) > 1:
            filename = loc[0].strip().split(" ")[1].strip("\"")
            # editor expects full path names
            if not filename == "<stdin>" and not filename.startswith("/"):
               filename = "/" + filename

         if filename == "<stdin>": filename = name

         # try to highlight. If that fails since e.g. the file is not loaded
         # in editor yet, then try to load it
         if not self.editors.highlight(filename, errline, not user_irq, "\n".join(lines[i:])):
            size = self.fileview.get_file_size(filename)
            if size is not None and size > 0:
               self.on_board_request(True)
               self.console.set_button(None)
               self.board.cmd(Board.GET_FILE, self.on_file, {
                  "name": filename, "size": size,
                  "error": { "scroll_to":  not user_irq, "line": errline, "msg": "\n".join(lines[i:]) } } )

         # cut the "in <module>" if present. Since the line in question is highlighted,
         # the "in <module>" will not give any additional information
         if loc[2].strip() == "in <module>": loc = loc[:2]
               
         locstr = filename.split("/")[-1] + ", " + ",".join(loc[1:]).strip()+"\n"
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
            
   def open_port_dialog(self):
      # open a port selection dialog if upide is configured not
      # to scan for devices by itself
      
      self.port_dialog = QDialog(self)
      self.port_dialog.setWindowTitle(self.tr("Select port"))
      self.port_dialog.resize(300,1)

      vbox = QVBoxLayout()
      
      # create a dropdown list of serial ports ...
      port_w = QWidget()
      portbox = QHBoxLayout()
      portbox.setContentsMargins(0,0,0,0)
      port_w.setLayout(portbox)
      portbox.addWidget(QLabel(self.tr("Port:")))
      self.port_cbox = QComboBox()
      self.port_cbox.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);
      for p in self.board.getPorts(): self.port_cbox.addItem(str(p), p)

      portbox.addWidget(self.port_cbox, 1)
      vbox.addWidget(port_w)

      button_box = QDialogButtonBox(
         QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
         Qt.Horizontal,
         self.port_dialog
      )

      button_box.accepted.connect(self.port_accept)
      button_box.rejected.connect(self.port_reject)
      vbox.addWidget(button_box)

      self.port_dialog.setLayout(vbox)

      self.port_dialog.setWindowModality(Qt.ApplicationModal)
      self.port = None
      self.port_dialog.exec_()

      self.port_dialog = None

      # user did not select a port. So close the entire app
      if not self.port:
         self.close()
      else:
         # user specified a port. So try to access device there
         self.on_board_request(True)
         self.status(self.tr("Connecting port {}...").format(self.port));
         self.board.cmd(Board.CONNECT, self.on_scan_result, self.port)

   def port_accept(self):
      self.port = self.port_cbox.currentData().device;
      self.port_dialog.close()
      
   def port_reject(self):
      self.port = None
      self.port_dialog.close()

   def on_lost_timer(self):
      qm = QMessageBox()
      ret = qm.question(self, self.tr('Board lost'),
                        self.tr("The connection to the board has been lost!\n"
                                "Do you want to reconnect?"), qm.Yes | qm.No)
      if ret == qm.Yes:
         # user wants to reconnect
         self.progress(None)
         self.board.cmd(Board.SCAN, self.on_scan_result)
      else:
         # user doesn't want to reconnect. So there's not much we can do
         self.close()
      
   def port_lost(self):
      # make sure no unsaved data is lost when closing the editors
      self.settings.setValue('unsaved', self.editors.getUnsaved())
      
      # disable all board interaction
      self.editors.closeAll()
      self.fileview.set(None)
      self.progress(False)
      self.console.set_button(None)
      self.console.clear()
      self.status(self.tr("Connection to board lost"));
      self.board.close()

      # start timer for further processing so processes are stopped
      # before and we don't recurse from one callback into the next etc
      self.lost_timer = QTimer()
      self.lost_timer.setSingleShot(True)
      self.lost_timer.timeout.connect(self.on_lost_timer)
      self.lost_timer.start(1000)
      
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
      self.status(self.tr("Starting ..."));

      # setup board interface
      self.board = Board(self)      
      self.console.input.connect(self.board.input)
      self.board.console.connect(self.on_console)
      self.board.progress.connect(self.progress)
      self.board.error.connect(self.on_error)
      self.board.status.connect(self.status)
      self.board.lost.connect(self.port_lost)
      self.board.interactive.connect(self.on_interactive)
      self.board.code_downloaded.connect(self.on_code_downloaded)

      # start scanning for board
      self.progress(False)
      self.console.set_button(None)

      # restore window position, size and splitter settings
      try:
         self.restoreGeometry(self.settings.value('window_geometry'))
         self.restoreState(self.settings.value('window_state'))
         self.hsplitter.restoreState(self.settings.value('window_hsplitter'))
         self.vsplitter.restoreState(self.settings.value('window_vsplitter'))
      except:
         pass
         
      self.show()

      # scan if the user isn't suppressing this
      if "noscan" in self.flags:
         # ask user for port
         self.timer = QTimer(self)
         self.timer.singleShot(100, self.open_port_dialog)
      else:
         self.on_board_request(True)

         # scan for device. Search first on the port that was successful
         # on a previous run
         self.board.cmd(Board.SCAN, self.on_scan_result,
                  { "port": self.settings.value('port') } )
                        
if __name__ == '__main__':
   # get own name. If name contains "noscan" then don't do
   # a automatic scan but ask for a port instead
   flags = [ ]
   if "noscan" in os.path.splitext(os.path.basename(sys.argv[0]))[0].lower():
      flags.append("noscan")

   # pybricks is too limited to support it in uPIDE. It has no os modules ...
   # if "pybricks_ble" in os.path.splitext(os.path.basename(sys.argv[0]))[0].lower():
   #   flags.append("pybricks_ble")

   app = QApplication(sys.argv)
   app_icon = QIcon()
   app_icon.addFile(Window.resource_path('assets/icon_16x16.png'), QSize(16,16))
   app_icon.addFile(Window.resource_path('assets/icon_24x24.png'), QSize(24,24))
   app_icon.addFile(Window.resource_path('assets/icon_32x32.png'), QSize(32,32))
   app_icon.addFile(Window.resource_path('assets/icon_48x48.png'), QSize(48,48))
   app_icon.addFile(Window.resource_path('assets/icon_256x256.png'), QSize(256,256))
   app.setWindowIcon(app_icon)
   
   tr = QTranslator()
   tr.load(QLocale.system().name(), Window.resource_path("assets/i18n"))
   app.installTranslator(tr)
   
   a = Window(app, flags)
   sys.exit(app.exec_())
