#===========================================================================
# Copyright (c) 2012, the evlio developers
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the PyFACT developers nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE PYFACT DEVELOPERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#===========================================================================
# Imports

import re
import logging
import os.path

#===========================================================================
# Regular expressions

# Extract key, value, and comment from FITS template file line
_FITS_TEMPLATE_LINE_RE = re.compile(r'(?:^        (?P<is_comment>.+))?\s*(?P<key>[-_A-Za-z0-9\\#]+)?(?:(?:\s*=\s*|\s*)(?P<value>[^ \t\r\n\f/]+))?(?:\s*/(?P<comment>.*))?')
_IS_TABLE_KW_RE = re.compile(r'(?P<table_kw>TTYPE|TFORM|TUNIT|TNULL|TSCAL|TZERO|TDISP|TBCOL|TDIM)(?P<auto_index>\#)?')
_EXTRA_PROPERTIES_RE = re.compile(r'(?P<std>.+)?\{(?P<extra>(?:\w+=\w+,?\s*)+)\}')
_ENTRY_VALUE_TYPE = re.compile(r'(?P<int>^[0-9]+$)?(?P<float>^[-+]?(?:[0-9]+\.[0-9]*)|(?:[0-9]*\.[0-9]+)|(?:[0-9]+\.?[0-9]*[eE][+-]?[0-9]+)|(?:[0-9]*\.?[0-9]+[eE][+-]?[0-9]+))?')

#===========================================================================
# Constants

_MAX_FILE_RECURSION_DEPTH = 5

#===========================================================================
# Functions & classes

#---------------------------------------------------------------------------
class FITSHeaderEntry(object) :

    """Data class of a FITS file header entry."""

    def __init__(self, key=None, value=None, comment=None,
                 parse_value=False, parse_extra_properties=False) :
        self.key = key
        if parse_value :
            self.value = self._parse_value(value)
        else :
            self.value = value
        self._parse_extra_properties = parse_extra_properties
        if comment and parse_extra_properties :
            self._do_parse_extra_properties(comment)
        else :
            self.comment = comment

    def _parse_value(self, value) :
        if type(value) is not str :
            return value
        m = _ENTRY_VALUE_TYPE.match(value)
        if m and m.group('int') :
            return int(value)
        elif m and m.group('float') :
            return float(value)
        else :
            return value

    def _do_parse_extra_properties(self, comment) :
        """
        Parse object extra properties from comment.

        Add additional properties to the object extracted from the comment.
        Property format is '{key1=value1,key2=value2, ...}'. All values are
        stored as strings.
        """
        self._orig_comment = comment
        m = _EXTRA_PROPERTIES_RE.match(comment)
        if m :
            if m.group('extra') :
                for s in m.group('extra').split(',') :
                    prop, val = s.strip().split('=')
                    setattr(self, prop, val)
            self.comment = m.group('std').strip()
        else :
            self.comment = comment
            

#---------------------------------------------------------------------------
class FITSHeader(list) :

    """Data class of a FITS file header."""

#---------------------------------------------------------------------------
class FITSExtension(object) :

    """Data class of a FITS file extension."""

    def __init__(self, type_=None, name=None, bitpix=None, naxis=None, header=None, data=None) :
        self.type_ = type_
        self.name = name
        self.bitpix = bitpix
        self.naxis = naxis
        self.header = header
        self.data = data

    def init_from_header(self, header=None) :
        if header :
            self.header = header
        if not self.header :
            logging.error('Could not intialize FITSExtension from header (header=None)')
            return
        # Reset properties
        self.type_, self.name, self.bitpix, self.naxis, self.data = None, None, None, None, None
        prop_map = {'EXTENSION': 'type_', 'XTENSION': 'type_', 'EXTNAME': 'name', 'BITPIX': 'bitpix',
                    'NAXIS': 'naxis'}
        # Read properties from header
        for fh in header :
            for key, prop in prop_map.items() :
                if fh.key == key :
                    setattr(self, prop, fh.value)
                    break

#---------------------------------------------------------------------------
class FITSFileTemplate(object) :
    """
    Class representing a FITS file template (fitsio).

    Notes
    -----
    http://heasarc.gsfc.nasa.gov/docs/software/fitsio/c/c_user/node105.html
    """
    def __init__(self, filename, parse_extra_properties=False) :
        self.filename_dir, self.filename_base = os.path.split(filename)
        self.extensions = None
        self._auto_index = 0
        self._auto_index_key = None
        self._parse_extra_properties = parse_extra_properties
        self._file_recursion_depth = 0
        self._parse_file(filename)
        [ext.init_from_header(ext.header) for ext in self.extensions]

    def _parse_file(self, filename) :
        """Parses a FITS file template."""
        # Check recursion depth
        self._file_recursion_depth += 1
        if self._file_recursion_depth > _MAX_FILE_RECURSION_DEPTH :
            logging.error('Maximum file recursion depth is reached ({0})'.format(_MAX_FILE_RECURSION_DEPTH))
            return
        f = open(filename)
        for l in f :
            self._parse_line(l)
        self._file_recursion_depth -= 1

    def _parse_line(self, l) :
        """Parses a FITS file template line."""
        m = _FITS_TEMPLATE_LINE_RE.match(l)
        if m :
            key = m.group('key')
            if m.group('is_comment') :
                # Empty key with comment, tbi
                pass
            elif key and len(key) > 0 and key[0] is not '#' :
                value = m.group('value')
                if key.find(r'\include') is not -1 and value != None :
                    # Smart path handling
                    if os.path.split(value)[0] == '' :
                        value = self.filename_dir + '/' + os.path.split(value)[1]
                    # Include file
                    self._parse_file(value)
                elif key.find(r'\group') is not -1 :
                    # We enter a new group
                    logging.warning('Grouping is not yet implemented')
                    pass
                elif key.find(r'\end') is not -1 :
                    # We leave a group
                    logging.warning('Grouping is not yet implemented')
                    pass
                else :
                    # Convert key to upper case
                    key = key.upper()
                    # Create primary HDU
                    if self.extensions == None :
                        self.extensions = [FITSExtension(type_='PRIMARY', name='PRIMARY', bitpix=16,
                                                         naxis=0, header=FITSHeader())]
                    # Verify key length
                    if len(key) > 8 :
                        logging.warning('Key too long (more then 8 characters): {0}'.format(key))
                    if key == 'XTENSION' :
                        # Add new extension
                        self.extensions.append(FITSExtension(type_='value', header=FITSHeader()))
                        # Reset auto indexing on start of a new extension
                        self._auto_index = 0
                        self._auto_index_key = None
                    # Are we dealing with table keywords
                    is_table_kw = _IS_TABLE_KW_RE.match(key)
                    if is_table_kw and is_table_kw.group('auto_index') :
                        # Apply auto index
                        if self._auto_index_key == None :
                            self._auto_index_key = is_table_kw.group('table_kw')
                        if is_table_kw.group('table_kw') == self._auto_index_key :
                            self._auto_index += 1
                        key = key.replace('#', str(self._auto_index))
                    # Add data to extension header
                    self.extensions[-1].header.append(
                        FITSHeaderEntry(key=key, value=value,
                                        comment = m.group('comment'),
                                        parse_value=True,
                                        parse_extra_properties=self._parse_extra_properties)
                        )
                    logging.debug('{0:>8} = {1:<20} / {2}'.format(key, m.group('value'), m.group('comment')))

#===========================================================================
#===========================================================================