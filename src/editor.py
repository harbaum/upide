#
# editor.py
# 
# Copyright (C) 2021-2022 Till Harbaum <till@harbaum.org>
#  GIF encoder taken from https://github.com/qalle2/pygif
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

import sys, os, math, struct
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
            'and', 'as', 'assert', 'async', 'await', 'break', 'class',
            'continue', 'def', 'del', 'elif', 'else', 'except',
            'exec', 'finally', 'for', 'from', 'global', 'if',
            'import', 'in', 'is', 'lambda', 'not', 'or', 'pass',
            'print', 'raise', 'return', 'try', 'while', 'yield',
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
    saveBytes = pyqtSignal(str, bytes)
    stop = pyqtSignal()
    searchRequested = pyqtSignal()
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

    def on_search(self):
        # user wants to search, so focus search box
        self.searchRequested.emit()
        
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
        
    def on_modified(self):
        # the on_modified can be triggered externally if
        # unsaved editor contents have been reloaded after a
        # crash or the like. In this case we set "code" to
        # an empty string representing the fact that we don't
        # have an unmodfied state to compare to
        self.code = ""
        self.updateModifyState(True)
        
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
            # convert to text if necessary
            if hasattr(code, "decode"):
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

    def getData(self):
        return self.text()
        
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
                painter.drawText(0, int(top), self.lineNumberArea.width()-2, height,
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def text(self):
        return self.toPlainText()

    def rename(self, new):
        self.name = new
        
    def saved(self, code, user_triggered):
        # A user triggered save is done from within an editor and we don't
        # force an update of the editor contents as the user may still be
        # modifiying it.
        if not user_triggered:        
            # the saved code may actually not be the one currently displayed
            # in the editor. This e.g. happens if a file is imported from the
            # PC which was already open in the editor
            if code != self.text():
                if hasattr(code, "encode"):
                    self.setCode(code.encode("utf-8"))
                else:
                    self.setCode(code)

        # the current code has been saved. So it becomes the
        # unmodified one
        self.code = code

        self.updateModifyState(self.checkModified())
    
    def highlight(self, line, scroll_to = True, msg = None):
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
        if scroll_to:
            cursor = self.textCursor()
            cursor.setPosition(blockPos)
            self.setTextCursor(cursor)

        self.setExtraSelections([selection])

    def search(self, pattern=None):
        # unless the search pattern is the same, go back one word
        if hasattr(self, "last_pattern") and pattern != self.last_pattern:
            textCursor = self.textCursor()
            textCursor.movePosition(QTextCursor.WordLeft)
            self.setTextCursor(textCursor)
            
        if pattern and not self.find(pattern):
            # nothing found, set cursor to begin of document and try again
            textCursor = self.textCursor()
            textCursor.movePosition(QTextCursor.Start)
            self.setTextCursor(textCursor)
            self.find(pattern)        

        self.last_pattern = pattern
            
class ImageItem(QGraphicsPixmapItem):
    # modified = pyqtSignal()
        
    def __init__(self):
        super().__init__()
        self.color = None
        self.pix = None          # no image yet
        self.drawing = False
        self.cb = None
        self.button_mode = None
        
    def setModificationCb(self, cb):
        self.cb = cb
        
    def setColor(self, color):
        self.color = color
            
    def setImage(self, data):
        self.pix = QPixmap()        
        self.pix.loadFromData(data)
        self.setPixmap(self.pix)
        self.painter = QPainter()

    def setPixel(self, pos):
        self.painter.begin(self.pix)
        self.painter.setPen(self.color)            
        self.painter.drawPoint(int(pos.x()), int(pos.y()))
        self.painter.end()
        self.setPixmap(self.pix)
        if self.cb: self.cb()
      
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setPixel(event.pos())
            self.drawing = True
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            
    def mouseMoveEvent(self, event):
        if self.drawing:
            self.setPixel(event.pos())
                
class ImageEditor(QGraphicsView):
    run = pyqtSignal(str, str)   # never emitted
    save = pyqtSignal(str, str)
    saveBytes = pyqtSignal(str, bytes)
    stop = pyqtSignal()          # never emitted
    modified = pyqtSignal(str, bool)
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.item = ImageItem()
        self.scene.addItem(self.item)

        self.viewport().installEventFilter(self)
        self.setMouseTracking(True)

        # pen (color picker) button
        self.btn_pen = QPushButton(QIcon(self.resource_path("assets/editor_pen.svg")), "", self)
        self.btn_pen.setIconSize(QSize(32,32));
        self.btn_pen.setFlat(True)
        self.btn_pen.resize(32, 32)
        self.btn_pen.setStyleSheet("background-color: rgba(255, 255, 255, 0);");
        self.btn_pen.pressed.connect(self.on_pen)

        # overlay save button
        self.btn_save = QPushButton(QIcon(self.resource_path("assets/editor_save.svg")), "", self)
        self.btn_save.setIconSize(QSize(32,32));
        self.btn_save.setFlat(True)
        self.btn_save.resize(32, 32)
        self.btn_save.setStyleSheet("background-color: rgba(255, 255, 255, 0);");
        self.btn_save.pressed.connect(self.on_save)
        self.btn_save.setToolTip(self.tr("Save this code") + " (CTRL-S)");
        self.btn_save.setHidden(True)
        
        self.setColor(QColor(Qt.black))

    def getData(self):
        ext = self.name.split(".")[-1]
        if ext.lower() == "gif":
            gifenc = GifEncoder()
            data = gifenc.encode(self.item.pixmap().toImage())
        else:        
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            self.item.pixmap().save(buffer, ext)
            data = bytes(buffer.data())

        return data
            
    def on_save(self):
        data = self.getData()
        
        # only really emit this signal if the save button is enabled
        if self.btn_save.isVisible():        
            self.saveBytes.emit(self.name, data)

    def isModified(self):
        return self.is_modified
        
    def on_modified(self):
        if not self.is_modified:
            self.btn_save.setHidden(False)
            self.modified.emit(self.name, True)
            self.is_modified = True
        
    def setColor(self, color):
        if color.isValid():
            self.color = color
            self.item.setColor(color)
        
    def on_pen(self):
        self.setColor(QColorDialog.getColor(self.color))
            
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    
    def setImage(self, data):
        self.is_modified = False
        self.item.setImage(data)
        self.item.setModificationCb(self.on_modified)

    def gentle_zoom(self, factor):
        self.scale(factor, factor);

    def wheelEvent(self, event):
        self.gentle_zoom(1.001 ** event.angleDelta().y())
        
    def saved(self, data, user_triggered):
        # if this was not user triggered it was a new image and the
        # current image should be replaced
        self.item.setImage(data)
        
        self.modified.emit(self.name, False)
        self.btn_save.setHidden(True)
        self.is_modified = False
    
    def resizeEvent(self, event):
        super().resizeEvent(event)

        # relocate the paint and save icons. Put the save icon on the right
        # for non-python files for which no run icon is being showed
        self.btn_pen.move(QPoint(self.width()-56, self.height()-56))
        self.btn_save.move(QPoint(self.width()-100, self.height()-56))

class GifEncoder:
    class Image(QImage):
        def __init__(self, image):
            super().__init__(image)
            self.offset = 0

        def get_pixel(self, image, offset = None):
            if offset == None: offset = self.offset        
            pix = QColor(image.pixel(offset % image.width(), offset // image.width) & 0xffffff)
            self.offset = offset + 1
            return bytes(  )

        def seek(self, offset, whence=0):
            if whence == 2:
                self.offset = 3 * self.width() * self.height() - offset
            elif whence == 1:
                self.offset += offset
            else:
                self.offset = offset

            return self.offset

        def read(self, num):
            # always assume we are reading full pixels
            c = QColor(self.pixel((self.offset//3) % self.width(),
                                  (self.offset//3) // self.width()) & 0xffffff)

            self.offset += 3
            return bytes( [ c.red(), c.green(), c.blue() ] )
        
    # GIF encoder taken from https://github.com/qalle2/pygif
    def __init__(self):
        pass

    def encode(self, qimage):
        image = GifEncoder.Image(qimage)
        
        palette = self.get_palette(image)
        if not palette: return

        imageData = self.raw_image_to_indexed(image, palette)

        data = b''
        for chunk in self.generate_gif(palette, imageData, image):
            data += chunk

        return data
            
    def get_palette(self, handle):
        # get palette from raw RGB image, return bytes (RGBRGB...)
        
        pixelCount = handle.seek(0, 2) // 3
        handle.seek(0)
        palette = {handle.read(3) for i in range(pixelCount)}
        if len(palette) > 256:
            print("Too many unique colors in input file.")
            return None
            
        return b"".join(sorted(palette))
        
    def raw_image_to_indexed(self, handle, palette):
        # convert RGB image into indexed (1 byte/pixel) using palette (RGBRGB...)

        pixelCount = handle.seek(0, 2) // 3
        handle.seek(0)
        rgbToIndex = dict(
            (palette[i*3:(i+1)*3], i) for i in range(len(palette) // 3)
        )
        return bytes(rgbToIndex[handle.read(3)] for i in range(pixelCount))
    
    def generate_lzw_codes(self, palBits, imageData):
        # encode image data using LZW (Lempel-Ziv-Welch)
        # palBits:   palette bit depth in encoding (2-8)
        # imageData: indexed image data (1 byte/pixel)
        # generate:  (code, code_length_in_bits)

        # TODO: find out why this function encodes wolf3.gif and wolf4.gif
        # different from GIMP.

        # LZW dictionary (key = LZW entry, value = LZW code)
        # note: doesn't contain clear and end codes, so actual length is len() + 2
        # note: uses a lot of memory but looking up an entry is fast
        lzwDict = dict((bytes((i,)), i) for i in range(2 ** palBits))

        pos     = 0            # position in input data
        codeLen = palBits + 1  # length of LZW codes (3-12)
        entry   = bytearray()  # dictionary entry

        yield (2 ** palBits, codeLen)  # clear code

        while pos < len(imageData):
            # find longest entry that's a prefix of remaining input data, and
            # corresponding code; TODO: [pos:pos+1] instead of [pos:] breaks some
            # decoders, investigate further
            entry.clear()
            for byte in imageData[pos:]:
                entry.append(byte)
                try:
                    code = lzwDict[bytes(entry)]
                except KeyError:
                    entry = entry[:-1]
                    break

            yield (code, codeLen)  # code for entry

            # advance in input data; if there's data left, update dictionary
            pos += len(entry)
            if pos < len(imageData):
                if len(lzwDict) < 2 ** 12 - 2:
                    # dictionary not full; add entry (current entry plus next
                    # pixel); increase code length if necessary
                    entry.append(imageData[pos])
                    lzwDict[bytes(entry)] = len(lzwDict) + 2
                    if len(lzwDict) > 2 ** codeLen - 2:
                        codeLen += 1
                # elif not args.no_dict_reset:
                else:
                    # dict. full; output clear code; reset code length & dict.
                    yield (2 ** palBits, codeLen)
                    codeLen = palBits + 1
                    lzwDict = dict((bytes((i,)), i) for i in range(2 ** palBits))

        yield (2 ** palBits + 1, codeLen)  # end code

    def generate_lzw_bytes(self, paletteBits, imageData):
        # get LZW codes, generate LZW data bytes

        data    = 0  # LZW codes to convert into bytes (max. 7 + 12 = 19 bits)
        dataLen = 0  # data length in bits

        codeCount    = 0  # codes written
        totalCodeLen = 0  # bits written

        for (code, codeLen) in self.generate_lzw_codes(paletteBits, imageData):
            # prepend code to data
            data |= code << dataLen
            dataLen += codeLen
            # chop off full bytes from end of data
            while dataLen >= 8:
                yield data & 0xff
                data >>= 8
                dataLen -= 8
            # update stats
            codeCount += 1
            totalCodeLen += codeLen

        if dataLen:
            yield data  # the last byte

    def generate_gif(self, palette, imageData, image):
        # generate a GIF file (version 87a, one image) as bytestrings
        # palette: 3 bytes/color, imageData: 1 byte/pixel

        # palette size in bits in Global Color Table (1-8) / in LZW encoding (2-8)
        palBitsGct = max(math.ceil(math.log2(len(palette) // 3)), 1)
        palBitsLzw = max(palBitsGct, 2)

        yield b"GIF87a"  # Header (signature, version)

        # Logical Screen Descriptor
        yield struct.pack(
            "<2H3B",
            image.width(), image.height(),  # logical screen width/height
            0b10000000 | palBitsGct - 1,    # packed fields (GCT present)
            0, 0                            # background color index, aspect ratio
        )

        # todo: fix palette writing
        yield palette + (2 ** palBitsGct * 3 - len(palette)) * b"\x00"  # pad GCT

        # Image Descriptor
        yield struct.pack(
            "<s4HB",
            b",", 0, 0,                     # image separator, image left/top position
            image.width(), image.height(),  # image width/height
            0b00000000                      # packed fields
        )

        yield bytes((palBitsLzw,))

        # LZW data in subblocks (length byte + 255 LZW bytes or less)
        subblock = bytearray()
        for lzwByte in self.generate_lzw_bytes(palBitsLzw, imageData):
            subblock.append(lzwByte)
            if len(subblock) == 0xff:
                # flush subblock
                yield bytes((len(subblock),)) + subblock
                subblock.clear()
        if subblock:
            yield bytes((len(subblock),)) + subblock  # the last subblock

        yield b"\x00;"  # empty subblock, trailer
