#
# buffered_serial.py
#
# buffers incoming serial data to speed up pyboard.py
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
# Street, Fifth Floor, Boston, MA 02110-1301 USA.from PyQt5.QtCore import *
#

import serial

__version__ = serial.__version__

class Serial(serial.Serial):
    def __init__(self, device, **kwargs):
      super().__init__(device, **kwargs)
      self._buffer = b""
      
    def inWaiting(self):
        # return anything in buffer, avoid calling super().inWaiting()
        # as it is the culprit for the slow performance
        if len(self._buffer):
            return len(self._buffer)
        
        return super().inWaiting()
      
    def read(self, num=None):
        # check if buffer can already satisfy request
        if len(self._buffer) >= num:
            retval = self._buffer[:num]
            self._buffer = self._buffer[num:]
            return retval
        
        # otherwise buffer everything available
        available = super().inWaiting()
        if available:
            self._buffer += super().read(available)

        # check if buffer is now sufficient
        if len(self._buffer) >= num:
            retval = self._buffer[:num]
            self._buffer = self._buffer[num:]
            return retval

        # nah, still not enough data, append more even if
        # that might block ...
        data = self._buffer
        if num is None:
            data += super().read()
        else:            
            data += super().read(num - len(self._buffer))

        # we'll return all data read, so buffer is now empty
        self._buffer = b""     
        return data
