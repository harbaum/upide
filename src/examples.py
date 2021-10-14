#
# examples.py - read examples from local file system or from github
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

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
import xml.etree.ElementTree as et
import os, sys

URL="https://raw.githubusercontent.com"
PATH="/harbaum/upide/master/examples/"
INDEX="index.xml"

class Examples(QObject):
    loaded = pyqtSignal(dict)
    imported = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()        
        self.local_index = { }

    def scan(self):
        # if local and network contain the same examples, then
        # network will take precedence as it's loaded later and
        # overwrites previous entries
        self.scanLocal()     # scan for local examples
        self.scanNetwork()   # scan for external examples
        
    def handleSection(self, e, path, isLocal):
        index = { }
        
        for child in e:
            if path != "":
                fullname = path + "/" + child.attrib["name"]
            else:
                fullname = child.attrib["name"]
                
            if child.tag == "section":
                index[fullname] = {
                    "description":  child.attrib["description"],
                    "children": self.handleSection(child, fullname, isLocal)
                }
            elif child.tag == "example":
                index[fullname] = {
                    "description": child.attrib["description"],
                    "local": isLocal
                }
        return index

    def dumpIndex(self, index):
        for i in index:
            print("{}: {}".format(i, index[i]["description"]))
            if "children" in index[i]:
                self.dumpIndex(index[i]["children"])
    
    def handleIndex(self, root, isLocal):
        if root.tag != "examples":
            raise ValueError("Index missing examples element")

        self.local_index.update(self.handleSection(root, "", isLocal))
        # self.dumpIndex(self.local_index)

        self.loaded.emit(self.local_index)
            
    # Translate asset paths to useable format for PyInstaller
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, "examples", relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", relative_path)

    def scanLocal(self):
        try:
            self.handleIndex(et.parse(self.resource_path(INDEX)).getroot(), True)
        except Exception as e:
            print("Examples local exception:", str(e))
        
    def handleNetworkResponse(self, reply):
        # check what this request was for
        name = reply.property("name")
        if not name:
            print("unexpected reply:", reply.request().url().path())
            return
        
        err = reply.error()        
        if err == QNetworkReply.NoError:
            try:
                data = str(reply.readAll(), 'utf-8')                
                if name == INDEX:
                    self.handleIndex(et.fromstring(data), False)
                else:
                    self.imported.emit(name, data)

            except Exception as e:
                print("Examples network exception:", str(e))
        else:
            print("Examples network error: ", err)
            print(reply.errorString())
        
    def scanNetwork(self):
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.handleNetworkResponse)
        reply = self.manager.get(QNetworkRequest(QUrl(URL + PATH + INDEX)))
        reply.setProperty("name", INDEX)

    def requestImport(self, name, src, local):
        if local:        
            try:
                with open(self.resource_path(src)) as f:
                    self.imported.emit(name, f.read())
            except:                
                pass
        else:
            reply = self.manager.get(QNetworkRequest(QUrl(URL + PATH + src)))
            reply.setProperty("name", name)            

