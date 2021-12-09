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
    imported = pyqtSignal(str, str, dict)
    file_imported = pyqtSignal(str, bytes, dict)
    
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
                if "files" in child.attrib:
                    for f in child.attrib["files"].split(";"):
                        if len(f.split("=")) > 1:
                            dst = f.split("=",1)[0]
                            src = f.split("=",1)[1]
                            if path != "": src = path + "/" + src
                
                            if not "files" in index[fullname]:
                                index[fullname]["files"] = { }

                            index[fullname]["files"][src] = dst                            

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
                ctx = reply.property("context")
                data = reply.readAll()
                
                if name == INDEX:
                    print("INDEX", str(data, 'utf-8'))
                    self.handleIndex(et.fromstring(str(data, 'utf-8')), False)
                elif name.lower().endswith(".py"):
                    self.imported.emit(name, str(data, 'utf-8'), ctx)
                else:
                    self.additional_file_loaded(ctx["dst"], data, ctx)

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

    def additional_file_loaded(self, name, data, ctx):
        print("Additional example file loaded", name, ctx, len(data))

        # data of extra file has successfully been imported and
        # should now be written to the device
        # data may be a string if a python file was loaded, bytes otherwise
        if isinstance(data, str): data = data.encode("utf-8")
        self.file_imported.emit(name, data, ctx)
        
    def import_additional_files(self, ctx):
        # The examples python file has been imported and saved on the
        # target. Now check if the example requires additional files
        # like e.g. sound files for audio examples
        
        # no further files to import?
        if not "files" in ctx or not ctx["files"]:
            print("example import complete")
            return

        # pull next file to be imported
        src, dst = ctx["files"].popitem()
        
        if ctx["local"]:        
            try:
                # addtional files are loaded as binary unless
                # they are python files
                with open(self.resource_path(src),
                          "r" if src.lower().endswith(".py") else "rb") as f:
                    self.additional_file_loaded(dst, f.read(), ctx)
            except Exception as e:
                print("Exception when loading extra file:", str(e))
        else:
            reply = self.manager.get(QNetworkRequest(QUrl(URL + PATH + src)))
            # unlike "name" in requestImport the dst is a full path as the
            # file may be stored in a special location on flash
            reply.setProperty("name", dst)
            reply.setProperty("context", ctx)            
        
    def requestImport(self, name, ctx):
        if ctx["local"]:        
            try:
                with open(self.resource_path(ctx["filename"])) as f:
                    self.imported.emit(name, f.read(), ctx)
            except Exception as e:
                print("Example import exception:", str(e))
        else:
            reply = self.manager.get(QNetworkRequest(QUrl(URL + PATH + ctx["filename"])))
            reply.setProperty("name", name)            
            reply.setProperty("context", ctx)            
