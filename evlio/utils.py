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
import glob

import evlio

#===========================================================================
# Regular expressions

#===========================================================================
# Constants

#===========================================================================
# Functions & classes

#---------------------------------------------------------------------------
def get_tpls_as_dict(path=evlio.BASE_PATH + '/templates') :
    """
    Reads the content of the templates/ directory in a dictionary.

    Parameters
    ----------
    path : str
        Base path to start parsing from.

    Returns
    -------
    tpls : dict
        Dictionary structure mapping the available tpls and versions.
    """
    tpls = {}
    for d1 in glob.iglob(path + '/*') :
        if os.path.isdir(d1) :
            vers = {}
            tpls[d1.split('/')[-1]] = vers
            for d2 in glob.iglob(d1 + '/*') :
                if os.path.isdir(d2) :
                    vers[d2.split('/')[-1]] = [os.path.basename(s) for s in glob.glob(d2 + '/*')]
    return tpls

#===========================================================================
#===========================================================================
