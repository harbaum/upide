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
        self.btn_prompt = QPushButton(self)
        self.btn_prompt.setIconSize(QSize(32,32));
        self.btn_prompt.setFlat(True)
        self.set_button(None)
        self.btn_prompt.resize(32, 32)
        self.btn_prompt.setStyleSheet("background-color: rgba(255, 255, 255, 0);");
        self.btn_prompt.pressed.connect(self.on_prompt)
        self.interactive = False

        self.savedCursor = None

    def insertFromMimeData(self, mimedata):
        # make sure pasted text goes through the device
        self.input.emit(mimedata.text())
        
    def resizeEvent(self, event):
        super().resizeEvent(event)

        # relocate the run and save icons
        self.btn_prompt.move(QPoint(self.width()-56, self.height()-56))

    def set_button(self, mode):
        self.btn_prompt.setVisible(mode != None)
        if mode == False:
            self.interactive = True
            self.btn_prompt.setToolTip(self.tr("Leave interactive mode"));
            self.btn_prompt.setIcon(QIcon(self.resource_path("assets/console_stop.svg")))
        elif mode == True:
            self.interactive = False
            self.btn_prompt.setToolTip(self.tr("Enter interactive mode"));
            self.btn_prompt.setIcon(QIcon(self.resource_path("assets/console_prompt.svg")))
        
    def on_prompt(self):
        self.clear()
        self.enable_input(not self.interactive)        
        if not self.interactive:
            self.set_button(False)
            self.interact.emit(True)
        else:
            self.interactive = False
            self.interact.emit(False)            
        
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    
    def enable_input(self, enable):
        self.input_enabled = enable
        self.setReadOnly(not enable)
        if enable: self.setFocus()

    def keyPressEvent(self, event):
        special = { Qt.Key_Up:     "\033[A",
                    Qt.Key_Down:   "\033[B",
                    Qt.Key_Right:  "\033[C",
                    Qt.Key_Left:   "\033[D",
                    Qt.Key_Home:   "\033[1~",
                    Qt.Key_Delete: "\033[3~",
                    Qt.Key_End:    "\033[4~",
        }
        
        # print("KEY:", event.key(), event.text().encode())
            
        if self.input_enabled:
            if event.key() in special:
                self.input.emit(special[event.key()])
                return
        
            key = event.text()
            if key != "":
                # print("text:", key)
                self.input.emit(key)

    def setText(self, str, tf):
        # delete as many characters as would be inserted to
        # implement some overwrite
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(str))
        cursor.removeSelectedText()
        cursor.insertText(str, tf);
                
    def appendFinal(self, str, color):
        # append directly without any further processing
        if not hasattr(self, 'tf') or not self.tf:
            self.tf = self.currentCharFormat()
        if color:
            tf = self.currentCharFormat()
            tf.setForeground(QBrush(QColor(color)))
            self.setText(str, tf)
        else:
            self.setText(str, self.tf)
        self.ensureCursorVisible()

    def appendWithCR(self, str, color):
        # check for return in string and go to end of line first
        # so no linebreak is inserted
        if "\n" in str:
            parts = str.split("\n")
            self.appendWithBS(parts[0], color)
            for i in range(1, len(parts)):
                # jump to end of line
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.MoveAnchor)
                self.setTextCursor(cursor)
                
                self.appendWithBS("\n" + parts[i], color)
        else:
            self.appendWithBS(str, color)
        
    def appendWithBS(self, str, color):
        
        # process backspace
        if "\x08" in str:
            parts = str.split("\x08")
            self.appendFinal(parts[0], color)
            for i in range(len(parts)-1):
                # here is a BS
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor)
                self.setTextCursor(cursor)
            
                # self.textCursor().deletePreviousChar()
                self.appendFinal(parts[i+1], color)
        else:
            self.appendFinal(str, color)

    def unEsc(self, str):
        if len(str) < 1: return None  # not enough data to decode
        if str[0] != "[": return str  # not a [ -> just print
        if len(str) < 2: return None  # not enough data to decode

        # a complete esc sequence consists of ESC[<num><char>
        # parse <num> if present
        i = 1
        num = None
        while i < len(str) and str[i].isdigit():
            if num == None: num = 0
            num = (num * 10) + int(str[i])
            i = i + 1

        # no more chars after number
        if i >= len(str): return None
            
        if str[i] == 'K':
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.setTextCursor(cursor)
        elif str[i] == 'D':
            if num is None: num = 1
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, num)
            self.setTextCursor(cursor)
        else:
            print(">>>>>>>>>>>>>>> unsupported ESC", str[i], num)
            
        return str[i+1:]

#    def mouseDoubleClickEvent(self, event):
#        print("suppressing mouse double click event")
                
#    def mouseClickEvent(self, event):
#        print("suppressing mouse click event")

#    def mousePressEvent(self, event):
#        print("suppressing mouse press event")

    def append(self, str, color=None):        
        # prepend and incomplete esc sequence we may still have
        if self.esc_buffer is not None:
            str = self.esc_buffer + str
            self.esc_buffer = None

        # check if there are escape sequences in the string
        if "\033" in str:        
            strparts = str.split("\033")

            # output everything before first esc
            if len(strparts[0]) > 0:
                # part before ESC
                self.appendWithCR(strparts[0], color)

            # there are "middle parts"
            if len(strparts) > 2:
                # process everything but the last one directly
                for i in range(len(strparts)-2):
                    d = self.unEsc(strparts[1+i])
                    if d is not None:
                        self.appendWithCR(d, color)

            # and the rest may potentially be incomplete (yet) ...
            d = self.unEsc(strparts[-1])
            # whole ESC sequence could be removed
            if d is not None:
                self.appendWithCR(d, color)
            else:
                # store incomplete esc sequence
                self.esc_buffer = "\033" + strparts[-1]
        else:
            self.appendWithCR(str, color)
            
    def appendBytes(self, b):
        # prepend everything we might still have in buffer
        if len(self.buffer) > 0:
            b = self.buffer + b
            self.buffer = b""

        if len(b) == 0: return

        # the user may have moved the cursor using the mouse. Undo
        # that and restore the cursor position micropython expects
        if self.savedCursor:
            self.setTextCursor(self.savedCursor)
            self.savedCursor = None
        
        # try to decode bytes
        try:
            # this callback receives single bytes or bytearrays
            # it may happen that e.g. a utf-8 character is on the
            # "border". This causes an decoding exception and the
            # incomplete undecoded part is stored until more data
            # has arrived.
            msg = b.decode("utf-8")
            msg = msg.replace('\r', '').replace('\x04', '')  # filter out \r and \x04
            self.append(msg)
        except Exception as e:
            # decoding failed, probably since the contents isn't valid utf-8
            print("Console decoding failed #1", str(e))

            # Check if the message can be decoded without the last character.
            try:
                msg = b[:-1].decode("utf-8")
                msg = msg.replace('\r', '').replace('\x04', '')  # filter out \r and \x04
                self.append(msg)
                
                self.buffer = b[-1]  # keep last byte in buffer
            except Exception as e:
                print("Console decoding failed #2", str(e))
                # if that also fails, decode as ascii
                try:                    
                    msg = b.decode("iso-8859-1")
                    msg = msg.replace('\r', '').replace('\x04', '')  # filter out \r and \x04
                    self.append(msg)
                except Exception as e:
                    # and finally ignore everything ...
                    print("Console decoding finally failed", str(e))

        # save cursor
        self.savedCursor = self.textCursor()
