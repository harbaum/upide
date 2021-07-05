#
# editors.py
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

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from editor import CodeEditor

class EditorTabs(QTabWidget):
    closed = pyqtSignal(str)
    
    def __init__(self, stack):
        super().__init__()
        self.tabCloseRequested.connect(self.on_tab_close)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.stack = stack

    def get_index_by_file(self, name):
        for i in range(self.count()):
            if self.widget(i).name == name:
                return i

        return None

    def on_tab_close(self, index):
        # check if tab contains modified data
        if self.widget(index).isModified():
            qm = QMessageBox()
            ret = qm.question(self,'Really close?', "This window contains unsaved changes.\nReally close?", qm.Yes | qm.No)
            if ret == qm.No: return

        name = self.widget(index).name
        self.removeTab(index)
        self.closed.emit(name)

        # if no more tabs are left, then bring the
        # label back to front to make it visible
        if self.count() == 0:
            self.stack.show(False)

    def on_modified(self, name, state):
        index = self.get_index_by_file(name)
        if index is not None:
            # if text has been edited set tab color red
            self.tabBar().setTabTextColor(index, Qt.red if state else Qt.black);
            
    def new(self, name, code):
        # check if we already have a tab for that file and just
        # raise it in that case
        index = self.get_index_by_file(name)
        if index is not None:
            self.setCurrentIndex(index)
            return

        # create a new edior view
        editor = CodeEditor(name)
        editor.setCode(code)

        editor.run.connect(self.stack.on_run)
        editor.save.connect(self.stack.on_save)
        editor.modified.connect(self.on_modified)
        editor.stop.connect(self.stack.on_stop)

        # use filename without path as tabs name and make the new tab the
        # active one
        tab = self.addTab(editor, name.split("/")[-1])
        self.setCurrentIndex(tab)
        
    def exists(self, name):
        return self.get_index_by_file(name) != None

    def rename(self, old, new):
        tab = self.get_index_by_file(old)
        if tab is not None:
            self.setTabText(tab, new.split("/")[-1]);
            self.widget(tab).rename(new)
    
    def set_run_mode(self, state, name=None):
        for i in range(self.count()):
            if state: 
                # enable all buttons
                self.widget(i).set_button_mode(True)
            else:
                # make given button a stop button, disable all others        
                if name is not None and self.widget(i).name == name:
                    self.widget(i).set_button_mode(False)
                else:
                    self.widget(i).set_button_mode(None)

    def isModified(self):
        # return true if any of the editor tabs
        # contains modified (unsaved) data
        for i in range(self.count()):
            if self.widget(i).isModified():
                return True

        return False

    def focusTop(self):
        w = self.currentWidget()
        if w is not None:
            w.setFocus()        
    
class Editors(QStackedWidget):
    run = pyqtSignal(str, str)
    save = pyqtSignal(str, str)
    stop = pyqtSignal()
    closed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        # display "no open files" when no tabs are open
        label = QLabel("No open files")
        label.setAlignment(Qt.AlignCenter)
        self.addWidget(label)

        # the tabwidget holds all editor instances
        self.tabs = EditorTabs(self)
        self.tabs.closed.connect(self.on_tab_closed)
        self.addWidget(self.tabs)

    def exists(self, name):
        return self.tabs.exists(name)
        
    def on_stop(self):
        self.stop.emit()
        
    def on_save(self, name, code):
        self.save.emit(name, code)
        
    def on_run(self, name, code):
        # clear any existing error highlight in that editor
        tab = self.tabs.get_index_by_file(name)
        if tab is not None:
            self.tabs.widget(tab).highlight(None)
         
        self.run.emit(name, code)
            
    def show(self, show_editors):
        if show_editors:
            # show the editor tabs
            self.setCurrentIndex(1)
        else:
            # show the info label
            self.setCurrentIndex(0)

    def highlight(self, name, line, message):
        tab = self.tabs.get_index_by_file(name)
        if tab is not None:
            self.tabs.widget(tab).highlight(line-1, message)      

    def new(self, name, code = None):
        # if the tabs aren't in front, then bring them to front now
        self.show(True)
        
        # and request editor tab
        self.tabs.new(name, code)
        
    def set_run_mode(self, state, name=None):
        self.tabs.set_run_mode(state, name)

    def saved(self, name):
        tab = self.tabs.get_index_by_file(name)
        if tab is not None:
            self.tabs.widget(tab).saved()      
                        
    def isModified(self):
        return self.tabs.isModified()

    def close(self, name):
        tab = self.tabs.get_index_by_file(name)
        if tab is not None:
            self.tabs.on_tab_close(tab)

    def on_tab_closed(self, name):
        self.closed.emit(name)

    def rename(self, old, new):
        self.tabs.rename(old, new)
        
    def focus(self):
        # five focus to topmost editor (if there is one)
        if self.tabs.count() != 0:
            self.tabs.focusTop()
