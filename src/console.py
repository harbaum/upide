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

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class Console(QPlainTextEdit):
    def __init__(self):
        super().__init__()

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setReadOnly(True)

        font = QFont("Mono", 10)
        font.setStyleHint(QFont.Monospace);
        font.setFixedPitch(True)
        self.setFont(font)

        self.buffer = b""

    def append(self, str, color=None):
        self.moveCursor(QTextCursor.End)
        if not hasattr(self, 'tf') or not self.tf:
            self.tf = self.currentCharFormat()
        if color:
            tf = self.currentCharFormat()
            tf.setForeground(QBrush(QColor(color)))
            self.textCursor().insertText(str, tf);
        else:
            self.textCursor().insertText(str, self.tf);
            
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
