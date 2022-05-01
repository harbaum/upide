#
# editor.py
# 
# Copyright (C) 2021-2022 Till Harbaum <till@harbaum.org>
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

class MinimalRegExp(QRegExp):
    def __init__(self, rule):
        super().__init__(rule)
        self.setMinimal(True)
            
class Highlighter(QSyntaxHighlighter):
    """ common highlighter class """
    
    def style(color, style=''):
        """Return a QTextCharFormat with the given attributes.
             """
        _color = QColor()
        _color.setNamedColor(color)
   
        _format = QTextCharFormat()
        _format.setForeground(_color)
        if 'bold' in style:
            _format.setFontWeight(QFont.Bold)
        if 'italic' in style:
            _format.setFontItalic(True)
        if 'underline' in style:
            _format.setFontUnderline(True)
   
        return _format
    
    STYLES = {
        # common styles
        'comment': style('darkRed'),
        'keyword': style('darkBlue'),
        'string': style('darkMagenta'),
        'number': style('darkGreen'),

        # styles not used by all highligters
        'brace': style('#404040'), # Python, JS, HTML, JSON
        'attribute': style('brown'), # HTML
        'heading': style('darkGreen', 'underline'), # HTML
        'title': style('darkGreen', 'bold underline' ), # HTML
        'alien': style('Grey', 'italic' ), # HTML
        'operator': style('darkRed'), # Python, JS
        'funcclass': style('darkcyan'), # JS, Python (def)
        'self': style('black', 'italic'), # Python, JS (this)
    }

    def parse_rules(self, rules):
        """ parse rules and make non-greedy regex from them """
        self.rules = [(MinimalRegExp(pat), index, fmt) for (pat, index, fmt) in rules]

    def parse_strings(self, strings):
        """ parse string rules and make non-greedy regex from them """
        return [ ( (MinimalRegExp(start[0]), start[1] ),
                   (MinimalRegExp(end[0]) if end[0] else None, end[1] ),
                   fmt, flags)
                 for (start, end, fmt, flags) in strings]
    
    def handle_strings(self, text, skip):
        """ check for string begins """        
        first_match = None
        # check for first string pattern to match, return None if none matches
        for s in range(len(self.strings)):
            expression = self.strings[s][0][0]      # start expression
            nth = self.strings[s][0][1]             # start nth
            index = expression.indexIn(text, skip)  # check for start rule
            if index >= 0:
                index = expression.pos(nth)         # same es indexIn if nth == 0
                length = len(expression.cap(nth))
                if not first_match or index < first_match[1]:
                    first_match = ( s, index, length )

        return first_match

    def skip_string(self, text, rule, offset):
        """ skip over a string. The start has been detected
        now the end is being searched for """
        
        expression = self.strings[rule][1][0]   # end expression
        if not expression: return None          # no expression at all
        nth = self.strings[rule][1][1]
        endmatch = expression.indexIn(text, offset, QRegExp.CaretAtOffset)
        if endmatch < 0: return None            # no match
        return ( expression.pos(nth), len(expression.cap(nth)) )
    
    def highlightBlock(self, text):
        self.setCurrentBlockState(0)

        string_areas = [ ]
        offset = 0
        
        # handle multiline continuations
        state = self.previousBlockState()
        if state > 0:
            rule = state - 1   # rules start with index 0
            # check for multiline string end
            skip = self.skip_string(text, rule, 0)  # returns (start, len) of end marker
            if skip == None:
                # no end here -> whole line is string and multiline continues
                self.setFormat(0, len(text), self.strings[rule][2]) 
                self.setCurrentBlockState(rule+1)
                return
            else:
                # multiline ends here
                pindex, plength = skip   # start and length of end pattern                
                pend = pindex if self.strings[rule][3] & 2 else pindex+plength                

                self.setFormat(0, pend, self.strings[rule][2])
                string_areas.append( (0, pend-1) )
                    
                offset = pindex + plength
                
        # first handle all string like patterns as the exclude their
        # matches from further processing
        s = self.handle_strings(text, offset)
        while s:
            rule, index, length = s
            # found a string like pattern, try to find matching end in same line
            skip = self.skip_string(text, rule, index + length)  # rule, index + length
            # does string end match? -> multiline string
            if skip == None:
                # exclude start pattern of requested
                if self.strings[rule][3] & 2: index += length

                # format and mark as string
                self.setFormat(index, len(text)-index, self.strings[rule][2])
                string_areas.append( (index,len(text)-1) )

                if self.strings[rule][3] & 1:
                    self.setCurrentBlockState(rule+1)
                    
                s = None
            else:
                # string end does match -> single line string
                pindex, plength = skip   # start and length of end pattern                

                # exclude start and end pattern if requested
                if self.strings[rule][3] & 2:
                    self.setFormat(index+length, pindex-(index+length), self.strings[rule][2]) 
                    string_areas.append( (index+length,pindex-1) )
                else:
                    self.setFormat(index, pindex+plength-index, self.strings[rule][2]) 
                    string_areas.append( (index,pindex+plength-1) )

                # check for further strings
                s = self.handle_strings(text, pindex+plength)

        # implement all regular patterns
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)
            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)              
                length = len(expression.cap(nth))
                # check if this is within a string and should thus
                # be ignored
                ok = True
                for area in string_areas:
                    if index+length > area[0] and index <= area[1]:
                        ok = False

                if ok: self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
  
class HtmlHighlighter(Highlighter):
    def __init__( self, parent):
        super().__init__( parent )

        rules = [
            # Numeric literals
            (r'\b[+-]?[0-9]+\b', 0, self.STYLES['number']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+\b', 0, self.STYLES['number']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?\b', 0, self.STYLES['number']),
            
            ( r"<!\bDOCTYPE\b.*>", 0, self.STYLES['comment']),

            # attributes
            ( r"\b([a-zA-Z_][a-zA-Z_0-9\.]*)\b\s*=", 1, self.STYLES['attribute']),

            # heading text
            ( r"<h([0-9])[^>]*>(.*)</h\1>", 2, self.STYLES['heading']),
            
            # title
            ( r"<title[^>]*>(.*)</title>", 1, self.STYLES['title']),

            # add opening rule
            (r'<\b([a-zA-Z_][a-zA-Z_0-9\.]*)\b[^>]*>', 1, self.STYLES['keyword']),
            # add closing rule
            (r'</\b([a-zA-Z_][a-zA-Z_0-9\.]*)\b[^>]*>', 1, self.STYLES['keyword']),
        ]

        rules += [(r'%s' % b, 0, self.STYLES['brace'])
                  for b in [ '[<>]', '<!', '</', '/>' ]]
        
        self.parse_rules(rules)

        # string/multiline patterns
        self.strings = self.parse_strings( [
            # "" and '' strings
            ( (r'"', 0), (r'(?:^|[^\\])(")', 1), self.STYLES['string'], 0),
            ( (r"'", 0), (r"(?:^|[^\\])(')", 1), self.STYLES['string'], 0),
            # <!-- comment -->
            ( (r'<!--',0), (r'-->',0), self.STYLES["comment"], 1),
            # <script> </script>
            ( ('<script[^>]*>', 0), ('</script[^>]*>', 0), self.STYLES["alien"], 3 ),
            # <style> </style>
            ( ('<style[^>]*>', 0), ('</style[^>]*>', 0), self.STYLES["alien"], 3 ),
        ] )
        
class CssHighlighter(Highlighter):
    def __init__( self, parent):
        super().__init__( parent )

        UNITS = r'cm|mm|in|px|pt|pc|em|ex|ch|rem|vw|vh|vmin|vmax|%|s'
        
        rules = [
            # Numeric literals
            (r'\b([+-]?[0-9]+)('+UNITS+r')?\b', 0, self.STYLES['number']),
            (r'((\b[+-]?0[xX])|#)[0-9A-Fa-f]+\b', 0, self.STYLES['number']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?\b', 0, self.STYLES['number']),

            (r'\b([\w-.]*)\s*:', 1, self.STYLES['keyword']),
            
            # single line /* */ comment
            (r'/\*.*\*/', 0, self.STYLES['comment']),
            # // comment
            (r'//.*$', 0, self.STYLES['comment']),
        ]
        
        self.parse_rules(rules)

        # string patterns
        self.strings = self.parse_strings( [
            # "" string
            ( (r'"', 0), (r'(?:^|[^\\])(")', 1), self.STYLES['string'], 0),
            # '' string
            ( (r"'", 0), (r"(?:^|[^\\])(')", 1), self.STYLES['string'], 0),
            # // comment, not multiline capable
            ( (r"//", 0), (None, 0), self.STYLES['comment'], 0),
            # /* */ comment, multiline capable
            ( (r"/\*", 0), (r"\*/", 0), self.STYLES['comment'], 1),
        ] )
        
class JsHighlighter(Highlighter):
    def __init__( self, parent):
        super().__init__( parent )

        keywords = [
            "await", "break", "case", "catch", "class", "const", "continue",
            "debugger", "default", "delete", "do", "else", "enum", "export",
            "extends", "false", "finally", "for", "function", "if", "implements",
            "import", "in", "instanceof", "interface", "let", "new", "null",
            "package", "private", "protected", "public", "return", "super",
            "switch", "static", "throw", "try", "true", "typeof", "var", "void",
            "while", "with", "yield" ]
					 
        # javascript operators
        operators = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<' ]
        
        rules = [
            (r'\bthis\b', 0, self.STYLES['self']),

            # 'function' followed by an identifier
            (r'\bfunction\b\s*(\w+)\b', 1, self.STYLES['funcclass']),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)\b', 1, self.STYLES['funcclass']),
            
            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, self.STYLES['number']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, self.STYLES['number']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, self.STYLES['number']),
        ]

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, self.STYLES['keyword'])
                  for w in keywords]
        rules += [(r'%s' % o, 0, self.STYLES['operator'])
                  for o in operators]
        rules += [(r'%s' % b, 0, self.STYLES['brace'])
                  for b in [ '\{', '\}', '\(', '\)', '\[', '\]' ] ]
   
        self.parse_rules(rules)

        # string patterns
        self.strings = self.parse_strings( [
            # "" string
            ( (r'"', 0), (r'(?:^|[^\\])(")', 1), self.STYLES['string'], 0),
            # '' string
            ( (r"'", 0), (r"(?:^|[^\\])(')", 1), self.STYLES['string'], 0),
            # // comment, not multiline capable
            ( (r"//", 0), (None, 0), self.STYLES['comment'], 0),
            # /* */ comment, multiline capable
            ( (r"/\*", 0), (r"\*/", 0), self.STYLES['comment'], 1),
        ] )
        
class JsonHighlighter(Highlighter):
    def __init__( self, parent):
        super().__init__( parent )

        rules = [
            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, self.STYLES['number']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, self.STYLES['number']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, self.STYLES['number']),
        ]

        rules += [(r'%s' % b, 0, self.STYLES['brace'])
                  for b in [ '\{', '\}', '\(', '\)', '\[', '\]' ] ]
   
        self.parse_rules(rules)

        # string patterns
        self.strings = self.parse_strings( [
            # "" string followed by :
            ( (r'(".*)"\s*:', 1), (r'"', 0), self.STYLES['keyword'], 0),
            # "" string
            ( (r'"', 0), (r'(?:^|[^\\])(")', 1), self.STYLES['string'], 0),
            # '' string
            ( (r"'", 0), (r"(?:^|[^\\])(')", 1), self.STYLES['string'], 0),
        ] )
        
class PythonHighlighter(Highlighter):
    def __init__( self, parent):
        super().__init__( parent )
 
        keywords = [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield',
            'None', 'True', 'False' ]
            
        operators = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<' ]
        
        rules = [
            # 'self'
            (r'\bself\b', 0, self.STYLES['self']),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)\W', 1, self.STYLES['funcclass']),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)\W', 1, self.STYLES['funcclass']),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, self.STYLES['number']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, self.STYLES['number']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, self.STYLES['number']),
        ]

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, self.STYLES['keyword']) for w in keywords]
        rules += [(r'%s' % o, 0, self.STYLES['operator']) for o in operators]
        rules += [(r'%s' % b, 0, self.STYLES['brace'])
                  for b in [ '\{', '\}', '\(', '\)', '\[', '\]' ] ]
            
        self.parse_rules(rules)
        
        # string patterns
        self.strings = self.parse_strings( [
            # Double-quoted comment or string
            ( (r'"""', 0), (r'(?:^|[^\\])(""")', 1), self.STYLES['comment'], 1),
            # end ", but not \", not multiline capable
            ( (r'"', 0), (r'(?:^|[^\\])(")', 1), self.STYLES['string'], 0),
            # Single-quoted comment or string
            ( (r"'''", 0), (r"(?:^|[^\\])(''')", 1), self.STYLES['comment'], 1),
            # end ', but not \', not multiline capable
            ( (r"'", 0), (r"(?:^|[^\\])(')", 1), self.STYLES['string'], 0),
            # regular # comments, not multiline capable
            ( (r"#", 0), (None, 0), self.STYLES['comment'], 0),
        ] )
    
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return Qsize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    run = pyqtSignal(str, str)
    save = pyqtSignal(str, str)
    stop = pyqtSignal()
    modified = pyqtSignal(str, bool)
    
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.code = ""
        self.error = None
        self.lineNumberArea = LineNumberArea(self)
        self.setMouseTracking(True)
        
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        
        self.updateLineNumberAreaWidth(0)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        font = QFont("Mono", 10)
        font.setStyleHint(QFont.Monospace);
        font.setFixedPitch(True)
        self.setFont(font)

        # use syntax highlighter on python files
        if self.isPython():
            self.highlighter = PythonHighlighter(self.document())
        elif self.isHtml():
            self.highlighter = HtmlHighlighter(self.document())
        elif self.isCss():
            self.highlighter = CssHighlighter(self.document())
        elif self.isJs():
            self.highlighter = JsHighlighter(self.document())
        elif self.isJson():
            self.highlighter = JsonHighlighter(self.document())

        # overlay run button
        if self.isPython():
            self.btn_run = QPushButton(QIcon(self.resource_path("assets/editor_run.svg")), "", self)
            self.btn_run.setIconSize(QSize(32,32));
            self.btn_run.setFlat(True)
            self.btn_run.resize(32, 32)
            self.btn_run.setStyleSheet("background-color: rgba(255, 255, 255, 0);");
            self.btn_run.pressed.connect(self.on_run)
        
        # overlay save button
        self.btn_save = QPushButton(QIcon(self.resource_path("assets/editor_save.svg")), "", self)
        self.btn_save.setIconSize(QSize(32,32));
        self.btn_save.setFlat(True)
        self.btn_save.resize(32, 32)
        self.btn_save.setStyleSheet("background-color: rgba(255, 255, 255, 0);");
        self.btn_save.pressed.connect(self.on_save)
        self.btn_save.setToolTip(self.tr("Save this code") + " (CTRL-S)");
        self.btn_save.setHidden(True)
        
        self.set_button(True)

        # some extra keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.on_save)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.on_search)
        if self.isPython():
            QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.on_run)

        # start a timer to track modifications at a low rate of max 10Hz to
        # reduce work load a little bit
        self.timer = None
        self.code_is_modified = False
        self.textChanged.connect(self.on_edit)

        self.setTabStopDistance(4 * self.fontMetrics().width(' ')) 

    def endsWith(self, exts):
        return self.name.split(".")[-1].lower() in exts
        
    def isPython(self):
        return self.endsWith( [ "py", "mpy" ] )
        
    def isHtml(self):
        return self.endsWith( [ "htm", "html" ] )

    def isCss(self):
        return self.endsWith( [ "css" ] )

    def isJs(self):
        return self.endsWith( [ "js" ] )

    def isJson(self):
        return self.endsWith( [ "json" ] )

    def isModified(self):
        return self.code_is_modified
        
    def checkModified(self):
        return self.text() != self.code
        
    def on_edit(self):
        # check for text change
        if self.timer is None:
            self.timer = QTimer(self)
            self.timer.singleShot(100, self.on_timer)

    def on_timer(self):
        self.timer = None
        m = self.checkModified()
        if m != self.code_is_modified:
            self.updateModifyState(m)

    def updateModifyState(self, m):
        self.code_is_modified = m
        self.modified.emit(self.name, m)

        # the user may be editing the file while it's running and while
        # the board is busy.
        if self.button_mode:
            self.btn_save.setHidden(not m)
        
        # if edited clear any error highlight
        if m: self.highlight(None)        
            
    def setCode(self, code):
        if code is not None:
            # convert to text
            code = code.decode("utf-8")
            # the editor works internally with \n only
            code = code.replace('\r', '')        
            self.code = code   # save code
            self.setPlainText(code)
        else:
            self.code = None
        
    def set_button(self, mode):
        # True = run, False = stop, None = disabled
        self.button_mode = mode
        if mode == True:
            if self.isPython():
                self.btn_run.setHidden(False)
                self.btn_run.setIcon(QIcon(self.resource_path("assets/editor_run.svg")))
                self.btn_run.setToolTip(self.tr("Run this code") + " (CTRL-R)");
            self.btn_save.setHidden(not self.checkModified())
        elif mode == False:
            if self.isPython():
                self.btn_run.setHidden(False)
                self.btn_run.setIcon(QIcon(self.resource_path("assets/editor_stop.svg")))
                self.btn_run.setToolTip(self.tr("Stop running code") + " (CTRL-R)");
            self.btn_save.setHidden(True)  # cannot save while running
        else:
            if self.isPython():
                self.btn_run.setHidden(True)
            self.btn_save.setHidden(True)

    def event(self, event):
        if self.error is not None and event.type() == QEvent.ToolTip:
            if self.cursorForPosition(event.pos()).blockNumber() == self.error["line"]:
                QToolTip.showText(event.globalPos(), self.error["msg"]);
            else:
                QToolTip.hideText();
                
            return True

        return QPlainTextEdit.event(self, event)

    def on_do_search(self):
        pattern = self.searchedit.text()
        if pattern and not self.find(pattern):
            # nothing found, set cursor to begin of document and
            # try again
            textCursor = self.textCursor()
            textCursor.movePosition(QTextCursor.Start)
            self.setTextCursor(textCursor)
            self.find(pattern)
         
    def on_search(self):
        # open search (and replace) dialog
        self.search_dialog = QDialog(self)
        self.search_dialog.setWindowTitle(self.tr("Search"))

        vbox = QVBoxLayout()

        search_w = QWidget()
        searchbox = QHBoxLayout()
        self.searchedit = QLineEdit()
        searchbox.addWidget(self.searchedit)
        searchbut = QPushButton(self.tr("Search"))
        searchbut.clicked.connect(self.on_do_search)
        searchbox.addWidget(searchbut)
        searchbox.setContentsMargins(0,0,0,0)
        search_w.setLayout(searchbox)
        
        vbox.addWidget(search_w)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close,
                            Qt.Horizontal, self.search_dialog)
        button_box.clicked.connect(self.search_dialog.close)
        vbox.addWidget(button_box)
        
        self.search_dialog.setLayout(vbox)
        self.searchedit.setFocus()
        self.search_dialog.show()

    def on_save(self):
        # only really emit this signal if the save button is enabled
        if self.btn_save.isVisible():        
            self.save.emit(self.name, self.text())
        
    def on_run(self):
        if self.btn_run.isVisible():        
            if self.button_mode == True:
                self.run.emit(self.name, self.text())
            elif self.button_mode == False:
                self.stop.emit()

    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
   
    def keyPressEvent(self, event):
        # for python programs the tab is converted to four spaces
        if self.isPython() and event.key() == Qt.Key_Tab:
            self.textCursor().insertText(" " * (4 - self.textCursor().columnNumber() % 4))
            event.accept()
        elif self.isHtml() and event.key() == Qt.Key_Tab:
            self.textCursor().insertText(" " * (2 - self.textCursor().columnNumber() % 2))
            event.accept()
        else:
            QPlainTextEdit.keyPressEvent(self, event )

    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
            
        space = 3 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)


    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(),
                                       rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)


    def resizeEvent(self, event):
        super().resizeEvent(event)

        # relocate the run and save icons. Put the save icon on the right
        # for non-python files for which no run icon is being showed
        if self.isPython():
            self.btn_run.move(QPoint(self.width()-56, self.height()-56))
            self.btn_save.move(QPoint(self.width()-100, self.height()-56))
        else:
            self.btn_save.move(QPoint(self.width()-56, self.height()-56))
        
        cr = self.contentsRect();
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(),
                     self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(Qt.lightGray).lighter(120))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Just to make sure we use the right font
        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self.lineNumberArea.width()-2, height,
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def text(self):
        return self.toPlainText()

    def rename(self, new):
        self.name = new
        
    def saved(self, code):
        # the saved code may actually not be the one currently displayed
        # in the editor. This e.g. happens if a file is imported from the
        # PC which was already open in the editor
        if code != self.text():
            if hasattr(code, "encode"):
                self.setCode(code.encode("utf-8"))
            else:
                self.setCode(code)
        else:
            # the current code has been saved. So it becomes the
            # unmodified one
            self.code = self.text()
            
        self.updateModifyState(False)
    
    def highlight(self, line, msg = None):
        self.error = None
        
        if line is None:
            self.setExtraSelections([])
            return

        block = self.document().findBlockByLineNumber(line)
        blockPos = block.position()

        selection = QTextEdit.ExtraSelection()
        
        # highlight formatting
        selection.format = QTextCharFormat()
        selection.format.setBackground(QColor(Qt.red).lighter(180))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        if msg:
            # setToolTip does not work. So we store the error and handle it explicitely
            # selection.format.setToolTip(msg)
            self.error = { "line": line, "msg": msg.strip() }

        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        selection.cursor.setPosition(blockPos)
        selection.cursor.select(QTextCursor.LineUnderCursor);
        selection.cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)

        # and scroll to error position
        cursor = self.textCursor()
        cursor.setPosition(blockPos)
        self.setTextCursor(cursor)

        self.setExtraSelections([selection])
