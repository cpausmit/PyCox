#!/bin/bash
#---------------------------------------------------------------------------------------------------
# Install the pycox interface.
#---------------------------------------------------------------------------------------------------

# generate the setup file
rm -f setup.sh
touch setup.sh

# first the base directory and the path
echo "# CAREFUL THIS FILE IS GENERATED AT INSTALL"          >> setup.sh
echo "export PYCOX_BASE=`pwd`"                              >> setup.sh
echo "export PATH=\"\${PATH}:\${PYCOX_BASE}\""              >> setup.sh
echo ""                                                     >> setup.sh
echo "export MY_PYTHON=\`which python26\`"                  >> setup.sh
echo "[ -z \"\$MY_PYTHON\" ] && MY_PYTHON=\`which python\`" >> setup.sh
echo ""                                                     >> setup.sh




# need to setup the funtions and load them
echo 'function pcLs()    { $MY_PYTHON $PYCOX_BASE/pycox.py --action ls    --source "$1"; }'               >> setup.sh
echo 'function pcDu()    { $MY_PYTHON $PYCOX_BASE/pycox.py --action du    --source "$1"; }'               >> setup.sh
echo 'function pcDu1()   { $MY_PYTHON $PYCOX_BASE/pycox.py --action du1   --source "$1"; }'               >> setup.sh
echo 'function pcDu2()   { $MY_PYTHON $PYCOX_BASE/pycox.py --action du2   --source "$1"; }'               >> setup.sh
echo 'function pcRm()    { $MY_PYTHON $PYCOX_BASE/pycox.py --action rm    --source "$1"; }'               >> setup.sh
echo 'function pcRmdir() { $MY_PYTHON $PYCOX_BASE/pycox.py --action rmdir --source "$1"; }'               >> setup.sh
echo 'function pcMkdir() { $MY_PYTHON $PYCOX_BASE/pycox.py --action mkdir --source "$1"; }'               >> setup.sh
echo 'function pcUp()    { $MY_PYTHON $PYCOX_BASE/pycox.py --action up    --source "$1" --target "$2"; }' >> setup.sh
echo 'function pcDown()  { $MY_PYTHON $PYCOX_BASE/pycox.py --action down  --source "$1" --target "$2"; }' >> setup.sh
echo 'function pcMv()    { $MY_PYTHON $PYCOX_BASE/pycox.py --action mv    --source "$1" --target "$2"; }' >> setup.sh
echo 'function pcCp()    { $MY_PYTHON $PYCOX_BASE/pycox.py --action cp    --source "$1" --target "$2"; }' >> setup.sh

exit 0
