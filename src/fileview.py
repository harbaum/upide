#
# fileview.py
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

import os, sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from board import Board
from examples import Examples

class FileNode(object):
   def __init__(self, name, size = None): 
      self.name = name
      self.size = size
      self._children = []
      self._parent = None
      self._row = 0
      
   def copy(self):
      d = FileNode(self.name, self.size)
      d._children = self._children
      d._parent = self._parent
      return d
      
   def path(self):
      # check number of parents as we want to ignore the
      # invisible root and the "Board" root
      if self._parent and self._parent._parent and self._parent._parent._parent:
         # this is a regular entry which as a parent, grandparent and grandgrandparent
         path = self._parent.path() + "/" + self.name         
      elif self._parent and self._parent._parent:
         # this is a toplevel regular entry with parent (Board) and grandparent (invisible root)
         path = "/" + self.name
      else:
         # this is either "Board" or invisible root
         path = ""

      return path
      
   def data(self, column):
      if column == FileView.COL_NAME: return self.name;
      elif column == FileView.COL_SIZE: return self.size;
      return None

   def set(self, node):
      # overwrite an entry with a different one (e.g. while renaming)
      # the _row field is not changed and should already be correct as
      # well as the _parent field
      self.name = node.name
      self.size = node.size
      self._children = node._children
      # adjust parent entries of all children
      for c in self._children:
         c._parent = self
      
   def setData(self, column, data):      
      if column == FileView.COL_NAME:
         self.name = data
      elif column == FileView.COL_SIZE:
         self.size = data

   def isDir(self):
      return self.size is None
         
   def columnCount(self):
      return 2 if self.name != "" and (not self.isDir() or len(self._children)) else 1

   def childCount(self):
      return len(self._children)

   def child(self, row):
      if row >= 0 and row < self.childCount():
         return self._children[row]

   def parent(self):
      return self._parent

   def row(self):
      return self._row

   def addChild(self, child):
      child._parent = self
      child._row = len(self._children)
      self._children.append(child)

   def insertChild(self, row, child):
      child._parent = self
      child._row = None
      self._children.insert(row, child)

      # renumber all children from new one up
      for i in range(row, len(self._children)):
         self._children[i]._row = i
         
   def removeChild(self, row):
      self._children.remove(self._children[row])
      # renumber all children afterwards
      for i in range(row, len(self._children)):
         self._children[i]._row = i
      
   def __str__(self):
      return "FileNode {}({}) kids: {}".format(self.name, self.size, self.childCount());
      
class FileModel(QAbstractItemModel):
   def __init__(self, nodes):
      super().__init__()
      self._root = nodes

      # Translate asset paths to useable format for PyInstaller
   def resource_path(self, relative_path):
      if hasattr(sys, '_MEIPASS'):
         return os.path.join(sys._MEIPASS, relative_path)
      return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

   def headerData(self, section, orientation, role):
      if role == Qt.DisplayRole and orientation == Qt.Horizontal:
         return [ "Name", "Size" ][section]
      return QAbstractTableModel.headerData(self, section, orientation, role)

   def getNode(self, index):
      if not index or not index.isValid():
         return self._root
      else:
         return index.internalPointer()      
   
   def insertRows(self, row, count, _parent=QModelIndex()):
      self.beginInsertRows(_parent, row, row+count-1)
      for i in range(count):
         self.getNode(_parent).insertChild(row+i, FileNode(None) )
      self.endInsertRows();
      return True
   
   def removeRows(self, row, count, _parent=QModelIndex()):
      self.beginRemoveRows(_parent, row, row+count-1);
      for i in range(count):
         self.getNode(_parent).removeChild(row+i)
      self.endRemoveRows()
      return True

   def rowCount(self, index):
      if index.isValid():
         return index.internalPointer().childCount()
      return self._root.childCount()
   
   def index(self, row, column, _parent=QModelIndex()):
      if not _parent or not _parent.isValid():
         parent = self._root
      else:
         parent = _parent.internalPointer()

      if not QAbstractItemModel.hasIndex(self, row, column, _parent):
         return QModelIndex()

      child = parent.child(row)
      if child:
         return QAbstractItemModel.createIndex(self, row, column, child)
      else:
         return QModelIndex()

   def parent(self, index):
      if index.isValid():
         p = index.internalPointer().parent()
         if p:
            return QAbstractItemModel.createIndex(self, p.row(), 0, p)
      return QModelIndex()

   def columnCount(self, index):
      if index.isValid():
         return index.internalPointer().columnCount()
      return self._root.columnCount()

   def path(self, index):
      if not index.isValid():
         return None

      return index.internalPointer().path()

   def setData(self, index, value, role):
      if not index.isValid():
         return False

      if role == Qt.DisplayRole:
         self.getNode(index).setData(index.column(), value)
         self.dataChanged.emit(index, index)
         return True

      return False
         
   def data(self, index, role):
      if not index.isValid():
         return None

      node = self.getNode(index)
      
      if role == Qt.ToolTipRole and  node.data(FileView.COL_SIZE) == -2:
         return 'This filesystem is defective!'
         
      if index.column() == FileView.COL_NAME and role == Qt.DecorationRole:
         # no size? -> folder
         if node.data(FileView.COL_SIZE) is None:
            return QWidget().style().standardIcon(getattr(QStyle, "SP_DirIcon"))
         elif node.data(FileView.COL_SIZE) == -2:
            return QIcon(self.resource_path("assets/broken.svg"))
         elif node.data(FileView.COL_NAME).endswith(".py"):
            return QIcon(self.resource_path("assets/python.svg"))
         else:
            return QWidget().style().standardIcon(getattr(QStyle, "SP_FileIcon"))
    
      if role == Qt.DisplayRole:
         return node.data(index.column())
      
      return None

   def supportedDropActions(self):
      return Qt.MoveAction

   def flags(self, index):
      if not index.isValid(): return Qt.NoItemFlags

      node = index.internalPointer()

      # root cannot be dragged
      if node.path() == "":
         return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled
         
      if not node.isDir():
         # regular files cannot be dropped upon
         return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled;

      # directories can
      return Qt.ItemIsEnabled | Qt.ItemIsSelectable | \
         Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

class ItalicDelegate(QStyledItemDelegate):
   # files that are not yet present on the device have size -1 and
   # are displayed in italics
   def paint(self, painter, option, index):
      if index.siblingAtColumn(FileView.COL_SIZE).data(Qt.DisplayRole) == -1:
         option.font.setItalic(True)
      if index.siblingAtColumn(FileView.COL_SIZE).data(Qt.DisplayRole) == -2:
         option.palette.setColor(QPalette.Text, QColor(255, 0, 0))
      QStyledItemDelegate.paint(self, painter, option, index)

class FileView(QTreeView):
   COL_NAME = 0
   COL_SIZE = 1
   
   message = pyqtSignal(str)   
   open = pyqtSignal(str, int)   
   mkdir = pyqtSignal(str)   
   delete = pyqtSignal(str)   
   rename = pyqtSignal(str, str)   
   firmware = pyqtSignal()
   host_import = pyqtSignal(str, str)
   example_import = pyqtSignal(str, dict)
   example_imported = pyqtSignal(str, bytes, dict)
   example_file_imported = pyqtSignal(str, bytes, dict)
   selection_changed = pyqtSignal(str)
   backup = pyqtSignal()
   restore = pyqtSignal()
   file_import = pyqtSignal(str)
   file_export = pyqtSignal(str, int)
   
   def __init__(self):
      super().__init__()
      self.rootname = self.tr("Board")
   
      self.setExpandsOnDoubleClick(False)
      self.setHeaderHidden(True)
      
      # https://stackoverflow.com/questions/782255/pyqt-and-context-menu
      self.contextMenu = QMenu(self);
      self.firmwareAction = QAction(self.tr("Firmware..."), self.contextMenu);
      self.firmwareAction.triggered.connect(self.on_context_firmware)
      self.contextMenu.addAction(self.firmwareAction);      
      self.backupMenu = self.contextMenu.addMenu(self.tr("Backup"))      
      self.backupAction = QAction(self.tr("Create..."), self.backupMenu);
      self.backupAction.triggered.connect(self.on_context_backup)
      self.backupMenu.addAction(self.backupAction);
      self.restoreAction = QAction(self.tr("Restore..."), self.backupMenu);
      self.restoreAction.triggered.connect(self.on_context_restore)
      self.backupMenu.addAction(self.restoreAction);
      self.newMenu = self.contextMenu.addMenu(self.tr("New"))      
      self.newAction = QAction(self.tr("File..."), self.newMenu);
      self.newAction.triggered.connect(self.on_context_new)
      self.newMenu.addAction(self.newAction);
      self.newDirAction = QAction(self.tr("Directory..."), self.newMenu);
      self.newDirAction.triggered.connect(self.on_context_new_dir)
      self.newMenu.addAction(self.newDirAction);
      self.newImportAction = QAction(self.tr("Import from PC..."), self.newMenu);
      self.newImportAction.triggered.connect(self.on_context_import)
      self.newMenu.addAction(self.newImportAction);
      self.openAction = QAction(self.tr("Open"), self.contextMenu);
      self.openAction.setDisabled(True)
      self.openAction.triggered.connect(self.on_context_open)
      self.contextMenu.addAction(self.openAction);
      self.renameAction = QAction(self.tr("Rename..."), self.contextMenu);
      self.renameAction.setDisabled(True)
      self.renameAction.triggered.connect(self.on_context_rename)
      self.contextMenu.addAction(self.renameAction);
      self.deleteAction = QAction(self.tr("Delete..."), self.contextMenu);
      self.deleteAction.setDisabled(True)
      self.deleteAction.triggered.connect(self.on_context_delete)
      self.contextMenu.addAction(self.deleteAction)
      self.exportAction = QAction(self.tr("Export to PC..."), self.newMenu);
      self.exportAction.triggered.connect(self.on_context_export)
      self.contextMenu.addAction(self.exportAction);
      
      self.setContextMenuPolicy(Qt.CustomContextMenu);
      self.customContextMenuRequested.connect(self.on_context_menu)
      
      self.setAcceptDrops(True)
      self.setDragDropMode(QAbstractItemView.InternalMove)
      self.setDragEnabled(True)
      self.dragNode = None

      # load examples
      self.examplesMenu = None
      self.examples = Examples()
      self.examples.loaded.connect(self.on_examples_loaded)
      self.examples.imported.connect(self.on_example_imported)
      self.examples.file_imported.connect(self.on_example_file_imported)
      self.examples.scan()

   def get_file_size(self, name):
      node = self.findNode(name)
      if node is None: return None
      return node.size
      
   def on_context_example(self, action):
      # check if a file of that name exists
      fullname = self.context_entry[0] + "/" + action.property("filename").split("/")[-1]
      if self.exists(fullname):
         self.message.emit(self.tr("A file or directory with that name already exists"));
         return

      # import the example
      context = { "filename": action.property("filename"),
                  "local":    action.property("local"),
                  "files":    action.property("files") }
      self.example_import.emit(fullname, context)

   def examplesInstall(self, menu, examples):
      for e in examples:
         example = examples[e]
         desc = example["description"]
         
         # check if action exists
         action = None
         for a in menu.actions():
            if a.text() == desc:
               action = a

         if "children" in example:
            # only install action if it does not exist yet
            if not action:               
               self.examplesInstall(menu.addMenu(desc), example["children"])
            else:
               self.examplesInstall(action.menu(), example["children"])
         else:
            if not action:
               action = QAction(desc, menu)
               action.setDisabled(False)
               menu.addAction(action)

            action.setProperty("filename", e)
            action.setProperty("local", example["local"])
            if "files" in example: action.setProperty("files", example["files"])
      
   def on_examples_loaded(self, examples):
      # integrate examples into context menu
      if not self.examplesMenu:
         self.examplesMenu = self.contextMenu.addMenu(self.tr("Examples"))
         self.examplesMenu.triggered.connect(self.on_context_example)

      # add entries
      self.examplesInstall(self.examplesMenu, examples)

   def on_example_imported(self, name, code, context):
      # code/data has been imported and needs to be saved
      self.example_imported.emit(name, code, context)
      
   def on_example_file_imported(self, name, code, context):
      # example extra file has been imported and needs to be saved
      self.example_file_imported.emit(name, code, context)
      
   def example_file_saved(self, ctx):
      # example extra file has been saved, continue with next file
      self.examples.import_additional_files(ctx)
      
   def requestExample(self, name, prop):
      return self.examples.requestImport(name, prop)

   def example_import_additional_files(self, context):
      self.examples.import_additional_files(context)
   
   def sysname(self, name):
      self.rootname = name
      
   def findNode(self, name, path = "", node = None):
      if node is None:
         node = self.model()._root.child(0)

      for ci in range(node.childCount()):
         child = node.child(ci)
         if name.startswith(path+"/"+child.name+"/"):
            return self.findNode(name, path+"/"+child.name, child)

         if name == path+"/"+child.name:
            return child   

      return None
            
   def exists(self, name):
      # check if a file with this name already exists
      return self.findNode(name) is not None

   def expand_(self, model, name, parent = QModelIndex()):
      for r in range(model.rowCount(parent)):
         index = model.index(r, 0, parent);
         lname = model.data(index, 0);
         # check if this is the directory we are searching for
         if len(name) > 0 and lname == name[0] and model.hasChildren(index):
            self.expand(index)
            if len(name) > 1:
               self.expand_(model, name[1:], index)

   def expandPath(self, name):
      self.expand_(self.model(), (self.rootname + name).split("/"))

   # get modelindex for a named entry
   def getIndex(self, model, name, parent = QModelIndex()):
      for r in range(model.rowCount(parent)):
         index = model.index(r, FileView.COL_NAME, parent);

         if model.data(index, Qt.DisplayRole) == name[0]:
            if len(name) == 1:
               return index
         
            # check if we should enter this directory
            if len(name) > 1 and model.hasChildren(index):
               return self.getIndex(model, name[1:], index)
               
   def isValidFilename(self, name):
      not_allowed = "\\/:*\"<>|"
      if name == "": return False
      if any(i in not_allowed for i in name): return False
      return True
   
   def on_context_new_dir(self):
      name, ok = QInputDialog.getText(self, self.tr('New directory'), self.tr('Enter new directory name:'))
      if not ok: return

      # check if this is a valid name
      if not self.isValidFilename(name):
         self.message.emit(self.tr("The directory name must not be empty and must not contain the characters \\,/,:,*,\",<,> or |"));
         return

      # create full path name
      fullname = self.context_entry[0] + "/" + name
      
      # check if file already exists
      if self.exists(fullname):
         self.message.emit(self.tr("A file or directory with that name already exists"));
         return

      # add a new row
      self.add_dir_entry(fullname)
      
      # and create the directory
      self.mkdir.emit(self.context_entry[0] + "/" + name)

   def add_file_entry(self, name, size = -1):
      # check if entry already exists
      if not self.exists(name):
         self.addToModel(self.model(), (self.rootname + name).split("/"), [ name.split("/")[-1], size ])      
      
   def add_dir_entry(self, name):
      self.add_file_entry(name, None)

   def fileInputDialog(self):
      dlg = QDialog(self)
      dlg.setWindowTitle(self.tr('New file'))
      dlg.resize(300,1)
      vbox = QVBoxLayout()
      
      vbox.addWidget(QLabel(self.tr('Enter new file name:')))
      
      hboxW = QWidget()
      hbox = QHBoxLayout()
      hbox.setContentsMargins(0,0,0,0)
      hboxW.setLayout(hbox)

      lineedit = QLineEdit()
      hbox.addWidget(lineedit)
      # create a dropdown list of supported file types
      type_cbox = QComboBox()
      for p in self.EDITABLE_TYPES:
         type_cbox.addItem(p[1], p[0][0])
         
      hbox.addWidget(type_cbox)
      vbox.addWidget(hboxW)
      
      button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dlg )
      button_box.accepted.connect(dlg.accept)
      button_box.rejected.connect(dlg.reject)
      vbox.addWidget(button_box)
      
      dlg.setLayout(vbox)

      dlg.setWindowModality(Qt.ApplicationModal)
      lineedit.setFocus()
      retval = ( None, False )
      if dlg.exec_() == QDialog.Accepted:
         retval = ( lineedit.text() + "." + type_cbox.currentData(), True )
         
      dlg.deleteLater()
      return retval
    
   def on_context_new(self):
      name, ok = self.fileInputDialog()
      if not ok: return

      if not self.isValidFilename(name):
         self.message.emit(self.tr("The file name must not be empty and must not contain the characters \\,/,:,*,\",<,> or |"));
         return

      # create full path name
      fullname = self.context_entry[0] + "/" + name
      
      # check if file already exists
      if self.exists(fullname):
         self.message.emit(self.tr("A file or directory with that name already exists"));
         return

      # add a new row
      self.add_file_entry(fullname)
      
      # and open an (empty) editor window
      self.open.emit(self.context_entry[0] + "/" + name, -1)
      
   def on_context_import(self):
      self.file_import.emit(self.context_entry[0])
            
   def on_context_export(self):
      self.file_export.emit(self.context_entry[0], self.context_entry[1])
      
   def on_context_firmware(self):
      self.firmware.emit()

   def get_next_file(self, name = None, node = None, path = ""):
      if node == None:
         node = self.model()._root.child(0)
         self.return_next_name = (name == None)         
         
      for ci in range(node.childCount()):
         child = node.child(ci)
         
         # return first match if no name was given
         if child.size != None and self.return_next_name:
            return path+"/"+child.name
         
         if name == path+"/"+child.name:
            self.return_next_name = True

         # decent into subdirs
         if child.size == None:
            r = self.get_next_file(name, child, path+"/"+child.name)
            if r != None: return r 

      return None
      
   def on_context_backup(self):
      self.backup.emit()
      
   def on_context_restore(self):
      self.restore.emit()
            
   def on_context_open(self):
      self.open.emit(self.context_entry[0], self.context_entry[1])
      
   def on_context_rename(self):
      # cut file name from full path
      oldname = self.context_entry[0].split("/")[-1]
      # seperate into basename and extension if present
      if len(oldname.split(".")) > 1:
         ext = oldname.split(".")[-1]
         oldname = ".".join(oldname.split(".")[:-1])
      else:
         ext = None

      name, ok = QInputDialog.getText(self, 'Rename file', 'Enter new file name:',
                                      QLineEdit.Normal, oldname)
      if not ok: return

      # check if this is a valid name
      if name == "":
         self.message.emit(self.tr("The file name must not be empty!"));
         return

      # re-append file extension if present
      if ext is not None:
         name = name + "." + ext
      
      # check if file already exists. Build a full new name for that from
      # the path of the old one and the new name
      pathparts = self.context_entry[0].split("/")[:-1]
      pathparts.append(name)
      fullname = "/".join(pathparts)
      if self.exists(fullname):
         self.message.emit(self.tr("A file with that name already exists"));
         return False
      
      # get a copy of the old entry
      entry = self.findNode(self.context_entry[0]).copy()

      self.removeFromModel(self.model(), (self.rootname + self.context_entry[0]).split("/"))
      self.addToModel(self.model(), (self.rootname + fullname).split("/"), [ name, 0 ])      

      # update entry (so directories get their children back)
      entry.name = name
      self.findNode(fullname).set(entry)      

      # keep selection on renamed object
      self.select(fullname)

      # and finally request the actual rename
      self.rename.emit(self.context_entry[0], fullname)

   def store(self, model, parent, index, obj):
      # create a new (unset) row
      model.insertRow(index, parent)
      # and set data in that row
      model.setData(model.index(index, FileView.COL_NAME, parent),\
                    obj[0], Qt.DisplayRole)
      model.setData(model.index(index, FileView.COL_SIZE, parent),\
                    obj[1], Qt.DisplayRole)
      
      self.expand(parent)
               
   def addToModel(self, model, name, obj, parent = QModelIndex()):
      if len(name) == 1:
         # iterate over all children to find the one to insert before
         for r in range(model.rowCount(parent)):
            index = model.index(r, FileView.COL_NAME, parent);
            name = model.data(model.index(r, FileView.COL_NAME, parent), Qt.DisplayRole);

            if name > obj[0]:
               self.store(model, parent, r, obj)
               return

         # no item to insert before, so append
         self.store(model, parent, model.rowCount(parent), obj)
         return
      else:         
         # iterate over all children
         for r in range(model.rowCount(parent)):
            index = model.index(r, FileView.COL_NAME, parent);
            size = model.data(model.index(r, FileView.COL_SIZE, parent), Qt.DisplayRole);

            # check if we should enter this directory (size == None -> isdir)
            # We cannot check with hasChildren here as we also want to
            # handle empty directories
            if model.data(index, Qt.DisplayRole) == name[0] and len(name) > 1 and size == None:
               self.addToModel(model, name[1:], obj, index)        
               
   # remove item from model
   def removeFromModel(self, model, name, parent = QModelIndex()):
      for r in range(model.rowCount(parent)):
         index = model.index(r, FileView.COL_NAME, parent);

         if model.data(index, Qt.DisplayRole) == name[0]:
            if len(name) == 1:
               model.removeRow(r, parent)
               return
         
            # check if we should enter this directory
            if len(name) > 1 and model.hasChildren(index):
               self.removeFromModel(model, name[1:], index)        

   def remove(self, fullname):
      # get only the path
      path = "/".join(fullname.split("/")[:-1])
      name = fullname.split("/")[-1]
            
      # Instead of updating the entire tree view just remove the row
      self.removeFromModel(self.model(), (self.rootname + fullname).split("/"))
               
   def on_context_delete(self):
      qm = QMessageBox()
      ret = qm.question(self, self.tr('Really delete?'), self.tr("Do you really want to delete {} from the board?").format(self.context_entry[0].split("/")[-1]), qm.Yes | qm.No)
      if ret == qm.Yes:
         self.remove(self.context_entry[0])
         self.delete.emit(self.context_entry[0])

   # file types supported by editors
   EDITABLE_TYPES = [
      ( [ "py", "mpy" ], "Python" ), ( [ "html", "htm" ], "HTML"), ( ["css"], "CSS"),
      ( ["txt"], "Text"), ( ["json"], "JSON"), ( ["js"], "Javascript") ]
         
   def is_editable(self, name):
      # files ending with .py, .html, .css, .txt or .json can be opened/edited
      for t in self.EDITABLE_TYPES:
         if name.split(".")[-1].lower() in t[0]:
            return True

      return False
         
   def on_context_menu(self, point):
      # column 0 is the file name
      index = self.indexAt(point).siblingAtColumn(FileView.COL_NAME)
      if index.isValid():
         # column 1 is the file size
         size = index.siblingAtColumn(FileView.COL_SIZE).data(Qt.DisplayRole)
         name = index.model().path(index)
         self.context_entry = (name, size)

         self.setCurrentIndex(index)
      
         # only the root entry has the firmware entry ...
         self.firmwareAction.setVisible(size == None and name == "")
         # ... and also the backup
         self.backupMenu.menuAction().setVisible(size == None and name == "")
         
         # size is "None" for directories

         # everything but the root dir and unsaved new files can be renamed
         self.renameAction.setEnabled(name != "" and (size == None or size >= 0))

         # all files can be exported
         self.exportAction.setVisible(size != None and size >= 0)
         
         # new files can be created for directories
         self.newMenu.menuAction().setVisible(size == None)
         if self.examplesMenu: self.examplesMenu.menuAction().setVisible(size == None)

         # the open entry is visible for all regular files but only some can be edited
         self.openAction.setVisible(size != None)
         self.openAction.setEnabled(size != None and self.is_editable(name))

         # delete is a little more complex you cannot delete
         # - the root directory
         # - directories which aren't empty
         # - newly created yet unsaved files
         if size is None and (name == "" or self.findNode(name).childCount() > 0):
            self.deleteAction.setEnabled(False)
         elif size != None and size < 0:
            self.deleteAction.setEnabled(False)
         else:
            self.deleteAction.setEnabled(True)
         
         self.contextMenu.exec_(self.viewport().mapToGlobal(point));

   def mouseDoubleClickEvent(self, event):
      if event.button() == Qt.LeftButton:
         # only files have a size
         index = self.indexAt(event.pos()).siblingAtColumn(FileView.COL_NAME)
         if index.isValid():
            size = index.siblingAtColumn(FileView.COL_SIZE).data(Qt.DisplayRole)
            if isinstance(size, int):
               name = index.model().path(index)
               if self.is_editable(name):
                  self.open.emit(name, size)
                  
   def updateModel(self, model, name, new_name, new_size, parent = QModelIndex()):
      # and update entry in model
      for r in range(model.rowCount(parent)):
         index = model.index(r, FileView.COL_NAME, parent);
         lname = model.data(index, Qt.DisplayRole);

         if lname == name[0]:
            if len(name) == 1:
               # update size if requested ...
               if new_size is not None:
                  size_index = index.siblingAtColumn(FileView.COL_SIZE)
                  model.setData(size_index, new_size, Qt.DisplayRole)
               # ... or name
               if new_name is not None:
                  name_index = index.siblingAtColumn(FileView.COL_NAME)
                  model.setData(name_index, new_name, Qt.DisplayRole)
         
            # check if we should enter this directory
            if len(name) > 1 and model.hasChildren(index):
               self.updateModel(model, name[1:], new_name, new_size, index)        
                  
   def saved(self, name, size):
      # update size of entry in file list
      entry = self.findNode(name)
      if entry != None:
         entry.size = size

      self.updateModel(self.model(), (self.rootname + name).split("/"), None, size)      
                  
   def getItems(self, files, path):
      items = [ ]
      for f in files:
         filename = path + "/" + f[0]
         if isinstance(f[1], int):
            node = FileNode(f[0], f[1])
         else:
            node = FileNode(f[0])
            for s in self.getItems(f[1], filename):
               node.addChild(s)
         items.append(node)
      return items
      
   def set(self, files):
      # invisible root item
      root = FileNode("")

      if files != None:
         rootdir = FileNode(self.rootname)
         root.addChild(rootdir)
         for i in self.getItems(files, ""):
            rootdir.addChild(i)
      
      model = FileModel(root)
      self.setModel(model)
      self.setItemDelegate(ItalicDelegate(self))

      # expand root
      self.expandPath("")

      self.selectionModel().selectionChanged.connect(self.onSelectionChanged)

   def onSelectionChanged(self, sel, desel):
      if len(sel.indexes()) > 0:
         index = sel.indexes()[0]
         if index.isValid():
            self.selection_changed.emit(index.internalPointer().path())

   def disable(self, d):
      self.setDisabled(d)

   def on_editor_closed(self, name):
      # only remove file from tree if it's not yet physically written back
      f = self.findNode(name)
      if f != None and f.size == -1:
         self.remove(name)
      
   # ------------- drag'n drop ralated -----------------

   def eventNode(self, event):
      index = self.indexAt(event.pos())
      if not index.isValid():
         return None

      return index.internalPointer()

   def isDraggable(self, event):
      node = self.eventNode(event)
      if node is None: return False
      
      # root cannot be dragged
      if node.path() == "":
         return False

      # newly created file cannot be dragged before
      # being saved to flash
      if node.size == -1:
         return False
      
      return True
   
   def isDroppable(self, event):
      node = self.eventNode(event)
      if node is None: return False

      # check if this is the current parent node of dragNode as
      # dropping on the current parent is not useful
      if event.source() == self and self.dragNode is not None:
         if self.dragNode._parent == node:
            return False

         # check if user is trying to drop a directory into itself
         # or one of its own subdirectories
         if node.isDir():
            # trying to drop into itself?
            if node.path() == self.dragNode.path():
               return False

            # trying to drop into a subdir of self?
            if node.path().startswith(self.dragNode.path()+"/"):
               return False
         
      return node.isDir()

   def mousePressEvent(self, event: QMouseEvent):
      if event.button() == Qt.LeftButton:
         # print("mouse down on", self.eventNode(event))
         if self.isDraggable(event):
            self.dragNode = self.eventNode(event)

            #drag = QDrag(self)
            #mimeData = QMimeData()
            #mimeData.setText("Inhalt!!!");
            #drag.setMimeData(mimeData);
            # drag->setPixmap(iconPixmap);
            #dropAction = drag.exec()  # Qt.CopyAction
         else:
            self.dragNode = None

         self.dropNode = None
      super().mousePressEvent(event)
            
   def dragEnterEvent(self, event: QDragEnterEvent):
      # print("dragEnterEvent()", event)
      self.selectionModel().clear()
      if event.source() == self and self.dragNode is not None:
         super().dragEnterEvent(event)
      else:
         event.acceptProposedAction()
         self.dropNode = None
         
   def dragMoveEvent(self, event):
      # print("dragMoveEvent()", event)
      if self.eventNode(event) != self.dropNode:
         self.dropNode = self.eventNode(event)
         self.selectionModel().clear()
         if self.isDroppable(event):
            index = self.indexAt(event.pos())
            self.selectionModel().select(index, \
                 QItemSelectionModel.Rows | QItemSelectionModel.Select)

   def dropEvent(self, event):
      # print("dropEvent()", event)

      self.selectionModel().clear()
      if self.isDroppable(event):
         if event.source() != self:
            # no dragnode set means that the dragging came from the outside
            #print("Proposed:", event.proposedAction(), Qt.CopyAction)
            #print("Mime formats:", event.mimeData().formats())
            #print("Mime url:", event.mimeData().urls())
            #print("Mime text:", event.mimeData().text())

            if len(event.mimeData().urls()) > 0:            
               url = event.mimeData().urls()[0]
               if url.isLocalFile():
                  src_name = url.toLocalFile()
                  fullname = self.eventNode(event).path() + "/" + os.path.basename(src_name)

                  # print("Import", src_name, "to", fullname)

                  # check if the target file already exists
                  if self.exists(fullname):
                     self.message.emit(self.tr("A file with that name already exists"));
                     return

                  self.host_import.emit(src_name, fullname)
                  
         else:
            # build target name
            fullname = self.eventNode(event).path() + "/" + self.dragNode.name;
            if self.exists(fullname):
               self.message.emit(self.tr("A file or directory with that name already exists"));
               return

            # get a copy of the old entry
            entry = self.findNode(self.dragNode.path()).copy()         
            self.removeFromModel(self.model(), (self.rootname + self.dragNode.path()).split("/"))
            self.addToModel(self.model(), (self.rootname + fullname).split("/"), [ self.dragNode.name, 0 ])      

            # update entry (so directories get their children back)
            self.findNode(fullname).set(entry)      

            # keep selection on renamed object
            self.select(fullname)

            # and finally request the actual rename
            self.rename.emit(self.dragNode.path(), fullname)

   def select(self, fullname):
      self.setCurrentIndex(self.getIndex(self.model(), (self.rootname + fullname).split("/")))
            
   def add(self, fullname, length):
      name = fullname.split("/")[-1]
      # add new file to tree
      self.addToModel(self.model(), (self.rootname + fullname).split("/"), [ name, length ])
      # and select it
      self.select(fullname)
