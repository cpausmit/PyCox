## PyCox

PyCox is an interface that implements the common shell commands to interact with dropbox storage space. PyCox is written in python and is based on the pycurl library which relies on the curl transfer tools. This explains the package name Py(thon)C(url)(Dropb)ox.

## Installation

  clone https://github.com/cpausmit/PyCox
  cd PyCox
  ./install.sh

This will generate the ./setup.sh command. It will make sure that the commands can run picking up the default configuation. To make sure you can access the data in your dropbox place you need to define all relevant parameters, see the pycox.cfg file.

If you want to use pycox please setup using source ./setup.sh.

## Available Commands

The core functions can be run using the pycox.py script. It has python style command line arguments and can feel a little clunky, nevertheless for clarity it was written that way. For ease of use a number of short bash function are defined which will make the tool feel more like shell command.

* pcLs <dropbox-path>
* pcDu1 <dropbox-path>
* pcMkdir <dropbox-path>
* pcRm <dropbox-file>
* pcRmDir <dropbox-dir>
* pcUp <local-file> <dropbox-file>
* pcDown <dropbox-file> <local-file>


## Status

The core functions I need for now are implemented, but there are a number of more functions we will add with time. In principle recursive actions as well as wildcards should be possible.