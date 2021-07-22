#
# console.py
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

import sys, os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class Console(QPlainTextEdit):
    input = pyqtSignal(str)
    interact = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setReadOnly(True)
        self.input_enabled = False
        
        font = QFont("Mono", 10)
        font.setStyleHint(QFont.Monospace);
        font.setFixedPitch(True)
        self.setFont(font)

        self.buffer = b""
        self.esc_buffer = ""

        # overlay prompt button
        self.btn_prompt = QPushButton(QIcon(self.resource_path("assets/console_prompt.svg")), "", self)
        self.btn_prompt.setIconSize(QSize(32,32));
        self.btn_prompt.setFlat(True)
        self.btn_prompt.resize(32, 32)
        self.btn_prompt.setStyleSheet("background-color: rgba(255, 255, 255, 0);");
        self.btn_prompt.pressed.connect(self.on_prompt)
        self.interactive = False
        
    def resizeEvent(self, event):
        super().resizeEvent(event)

        # relocate the run and save icons
        self.btn_prompt.move(QPoint(self.width()-56, self.height()-56))

    def enable(self, en):
         self.btn_prompt.setVisible(en)
        
    def on_prompt(self):
        self.clear()
        if not self.interactive:        
            self.interactive = True
            self.input_enabled = True
            self.btn_prompt.setIcon(QIcon(self.resource_path("assets/console_stop.svg")))
            self.interact.emit(True)
        else:
            self.interactive = False
            self.input_enabled = False
            self.btn_prompt.setIcon(QIcon(self.resource_path("assets/console_prompt.svg")))
            self.interact.emit(False)            
        
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath('.'), relative_path)     
    
    def enable_input(self, enable):
        self.input_enabled = enable
        self.setReadOnly(not enable)
        if enable: self.setFocus()

#    def mousePressEvent(self, event: QMouseEvent):
#        self.input_enabled = True
#        self.clicked.emit()
        
    def keyPressEvent(self, event):
        if self.input_enabled:
            key = event.text()
            if key != "":            
                self.input.emit(key)

    def appendFinal(self, str, color):
        # append directly without any further processing
        self.moveCursor(QTextCursor.End)
        if not hasattr(self, 'tf') or not self.tf:
            self.tf = self.currentCharFormat()
        if color:
            tf = self.currentCharFormat()
            tf.setForeground(QBrush(QColor(color)))
            self.textCursor().insertText(str, tf);
        else:
            self.textCursor().insertText(str, self.tf);
        self.ensureCursorVisible()

    def appendWithBS(self, str, color):
        # process backspace
        if "\x08" in str:
            parts = str.split("\x08")
            self.appendFinal(parts[0], color)
            for i in range(len(parts)-1):
                # here is a BS
                self.textCursor().deletePreviousChar()
                
                self.appendFinal(parts[i+1], color)
        else:
            self.appendFinal(str, color)

    def unEsc(self, str):        
        if len(str) < 1: return None  # not enough data to decode
        if str[0] != "[": return str  # not a [ -> just print
        if len(str) < 2: return None  # not enough data to decode
        if str[1].isalpha(): return str[2:] # remove [K
        return str
            
    def append(self, str, color=None):
        # prepend and incomplete esc sequence we may still have
        if self.esc_buffer is not None:
            str = self.esc_buffer + str
            self.esc_buffer = None
                
        # todo: handle special sequences
        # 0x08    BS
        # https://en.wikipedia.org/wiki/ANSI_escape_code#CSIsection
        # 0x1b[K  clear to end of line (sent after BS)

        # check if there are escape sequences in the string
        if "\x1b" in str:        
            strparts = str.split("\x1b")

            # skip everything between ESC and for letter
            if len(strparts[0]) > 0:
                # part before ESC
                self.appendWithBS(strparts[0], color)

            # there are "middle parts"
            if len(strparts) > 2:
                # process everything but the last one directly
                for i in range(len(strparts)-2):
                    self.appendWithBS(self.unEsc(strparts[1+i]))

            # and the rest may potentially be incomplete (yet) ...
            d = self.unEsc(strparts[-1])
            # whole ESC sequence could be removed
            if d is not None:
                self.appendWithBS(d, color)
            else:
                # store incomplete esc sequence
                self.esc_buffer = "\x1b" + strparts[-1]
                    
        else:
            self.appendWithBS(str, color)
            
    def appendBytes(self, b):
        # prepend everything we might still have in buffer
        if len(self.buffer) > 0:
            b = self.buffer + b
            self.buffer = b""
        
        # try to decode bytes
        try:
            # this callback receives single bytes or bytearrays
            # it may happen that e.g. a utf-8 character is on the
            # "border". This causes an decoding exception and the
            # incomplete undecoded part is stored until more data
            # has arrived.
            str = b.decode("utf-8")
            str = str.replace('\r', '').replace('\x04', '')  # filter out \r and \x04
            self.append(str)
        except:
            self.buffer = b
