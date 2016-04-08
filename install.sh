#!/bin/bash
#---------------------------------------------------------------------------------------------------
# Install the pycox interface.
#---------------------------------------------------------------------------------------------------

# generate the setup file
rm -f setup.sh
touch setup.sh

# first the base directory and the path
echo "# CAREFUL THIS FILE IS GENERATED AT INSTALL" >> setup.sh
echo "export PYCOX_BASE="`pwd`                     >> setup.sh
echo "export PATH=\"\${PATH}:\${PYCOX_BASE}\""     >> setup.sh
echo ""                                            >> setup.sh

# need to setup the funtions and load them
echo 'function pcLs()    { pycox.py --action ls    --source "$1"; }'               >> setup.sh
echo 'function pcDu1()   { pycox.py --action du1   --source "$1"; }'               >> setup.sh
echo 'function pcDu2()   { pycox.py --action du2   --source "$1"; }'               >> setup.sh
echo 'function pcRm()    { pycox.py --action rm    --source "$1"; }'               >> setup.sh
echo 'function pcRmdir() { pycox.py --action rmdir --source "$1"; }'               >> setup.sh
echo 'function pcMkdir() { pycox.py --action mkdir --source "$1"; }'               >> setup.sh
echo 'function pcUp()    { pycox.py --action up    --source "$1" --target "$2"; }' >> setup.sh
echo 'function pcDown()  { pycox.py --action down  --source "$1" --target "$2"; }' >> setup.sh
echo 'function pcMv()    { pycox.py --action mv    --source "$1" --target "$2"; }' >> setup.sh
echo 'function pcCp()    { pycox.py --action cp    --source "$1" --target "$2"; }' >> setup.sh

exit 0
