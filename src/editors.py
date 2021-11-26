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

    def closeAll(self):
        self.clear()
        self.stack.show(False)
    
    def on_tab_close(self, index):
        # check if tab contains modified data
        if self.widget(index).isModified():
            qm = QMessageBox()
            ret = qm.question(self,self.tr('Really close?'),
                              self.tr("This window contains unsaved changes.")+
                              "\n"+self.tr("Really close?"), qm.Yes | qm.No)
            if ret == qm.No: return

        self.closed.emit(self.widget(index).name)
        self.removeTab(index)

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
        # check if it's a directory that is being renamed which
        # in turn may affect the paths of files in open editor tabs
        for tab in range(self.count()):
            # check if the old name is a path prefix of this tab
            if self.widget(tab).name.startswith(old+"/"):
                newname = new + self.widget(tab).name[len(old):]
                self.widget(tab).rename(newname)

        # check if it's a file name of an open tab that has been renamed
        tab = self.get_index_by_file(old)
        if tab is not None:
            self.setTabText(tab, new.split("/")[-1]);
            self.widget(tab).rename(new)
    
    def set_button(self, state):
        for i in range(self.count()):
            self.widget(i).set_button(state)

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
    changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.addWidget(self.splash(self))

        # the tabwidget holds all editor instances
        self.tabs = EditorTabs(self)
        self.tabs.closed.connect(self.on_tab_closed)
        self.tabs.currentChanged.connect(self.on_current_changed)
        self.addWidget(self.tabs)

    def splash(self, parent):
        vbox_w = QWidget(parent)
        vbox = QVBoxLayout()
        vbox_w.setLayout(vbox)

        vbox.addStretch(2)
        
        # title, version, copyright, ...
        title = QLabel("µPIDE", vbox_w)
        font = title.font()
        font.setPointSize(24)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        version = QLabel("V1.0.3", vbox_w)
        version.setAlignment(Qt.AlignCenter)
        vbox.addWidget(version)
        
        detail = QLabel(self.tr("A beginners Micropython IDE"), vbox_w)
        detail.setAlignment(Qt.AlignCenter)
        vbox.addWidget(detail)

        vbox.addStretch(1)

        copyright = QLabel(self.tr("(c) 2021 Till Harbaum <till@harbaum.org>"), vbox_w)
        copyright.setAlignment(Qt.AlignCenter)
        vbox.addWidget(copyright)

        link = QLabel("<a href=\"http://github.com/harbaum/upide\">"+
                      self.tr("{} on Github").format("µPIDE")+"</a>", vbox_w)
        link.setTextFormat(Qt.RichText)
        link.setTextInteractionFlags(Qt.TextBrowserInteraction);
        link.setOpenExternalLinks(True);
        link.setAlignment(Qt.AlignCenter)
        vbox.addWidget(link)

        vbox.addStretch(2)
        
        return vbox_w
        
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
            self.tabs.setCurrentIndex(tab)
            return True

        return False

    def new(self, name, code = None):
        # if the tabs aren't in front, then bring them to front now
        self.show(True)
        
        # and request editor tab
        self.tabs.new(name, code)
        
    def set_button(self, state):
        # set editor button(s) to
        # True=RUN, False=Stop or None
        self.tabs.set_button(state)

    def saved(self, name):
        tab = self.tabs.get_index_by_file(name)
        if tab is not None:
            self.tabs.widget(tab).saved()      
                        
    def isModified(self):
        return self.tabs.isModified()

    def closeAll(self):
        self.tabs.closeAll()
        
    def close(self, name):
        tab = self.tabs.get_index_by_file(name)
        if tab is not None:
            self.tabs.on_tab_close(tab)

    def on_tab_closed(self, name):
        # check if the tab to be closed is currently being run. Stop
        # the running program in that case        
        tab = self.tabs.get_index_by_file(name)
        if tab is not None and tab >= 0:
            if self.tabs.widget(tab).button_mode == False:
                self.stop.emit()
            
        self.closed.emit(name)

    def rename(self, old, new):
        self.tabs.rename(old, new)
        
    def focus(self):
        # five focus to topmost editor (if there is one)
        if self.tabs.count() != 0:
            self.tabs.focusTop()
            
    def on_current_changed(self, tab):
        # user has selected a different tab. Tell fileview to select the
        # corresponding file
        if tab >= 0:
            self.changed.emit(self.tabs.widget(tab).name)
        
    def on_select(self, name):
        # user has selected a different file in the fileview. Raise
        # the matching editor if it exists
        tab = self.tabs.get_index_by_file(name)
        if tab is not None: self.tabs.setCurrentIndex(tab)
