#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"
export PYTHONPATH="`pwd`:`pwd`/examples:`pwd`/examples/generic"
TOP=$(readlink -f $(pwd)/..)

#
# Load the configuration
#
. conf.sh

# Prepare test environment
#
# * make dist
# * install packaged files into /tests
# * copy examples into /tests
# * run pep8 checks against /tests -- to cover test code also
# * run nosetests
#
# It is important to test not in-place, but after `make dist`,
# since in that case only those files will be tested, that are
# included in the package.
#
# Tox installs the package into each environment, so we can safely skip
# extraction of the packaged files
if [ -z "$WITHINTOX" ]; then
    # detect, if we run from git
    cd $TOP
    [ -d ".git" ] && {
        # ok, make tarball
        make dist
        mkdir "$TOP/tests/bin/"
        cp -a "$TOP/examples" "$TOP/tests/"
        cp -a "$TOP/cli/ipdb" "$TOP/tests/bin/"
        cp -a "$TOP/cli/ss2" "$TOP/tests/bin/"
        cd "$TOP/dist"
        tar xf *
        mv pyroute2*/pyroute2 "$TOP/tests/"
    } ||:
    # or just give up and try to run as is
fi
cd "$TOP/tests/"

#
# Install test requirements, if not installed.
#
function install_test_reqs() {
    which pip >/dev/null 2>&1 && pip install -q -r requirements.txt
}

if [ -z "$VIRTUAL_ENV" ]; then
    install_test_reqs
else
    # Install requirements only into manually-made virtualenvs.
    if [ -f "$VIRTUAL_ENV/bin/activate" ]; then
        source "$VIRTUAL_ENV/bin/activate"
        install_test_reqs
    fi
    echo "Running in VirtualEnv"
fi

#
# Setup kernel parameters
#
[ "`id | sed 's/uid=[0-9]\+(\([A-Za-z]\+\)).*/\1/'`" = "root" ] && {
    echo "Running as root"
    ulimit -n 2048
    modprobe dummy 2>/dev/null ||:
    modprobe bonding 2>/dev/null ||:
    modprobe 8021q 2>/dev/null ||:
    modprobe mpls_router 2>/dev/null ||:
    modprobe mpls_iptunnel 2>/dev/null ||:
    sysctl net.mpls.platform_labels=2048 2>/dev/null ||:
}


#
# Adjust paths
#
if which pyenv 2>&1 >/dev/null; then
    PYTHON_PATH=$(pyenv which $PYTHON)
    FLAKE8_PATH=$(pyenv which $FLAKE8)
    NOSE_PATH=$(pyenv which $NOSE)
else
    PYTHON_PATH=$(which $PYTHON)
    FLAKE8_PATH=$(which $FLAKE8)
    NOSE_PATH=$(which $NOSE)
fi

echo "8<------------------------------------------------"
echo "kernel: `uname -r`"
echo "python: $PYTHON_PATH [`$PYTHON_PATH --version 2>&1`]"
echo "flake8: $FLAKE8_PATH [`$FLAKE8_PATH --version 2>&1`]"
echo "nose: $NOSE_PATH [`$NOSE_PATH --version 2>&1`]"
echo "8<------------------------------------------------"

#
# Check PEP8
#
$FLAKE8_PATH . && echo "flake8 ... ok" || exit 254

#
# Run tests
#
function get_module() {
    module=$1
    pattern=$2
    prefix="`echo $pattern | sed 's/:.*//'`"
    pattern="`echo $pattern | sed 's/[^:]\+://'`"
    [ "$prefix" = "$module" ] || exit 1
    echo $pattern
}

errors=0
for i in `seq $LOOP`; do
    tstamp=`date +%s`
    echo "iteration $i of $LOOP [timestamp: $tstamp] [errors: $errors]"
    for module in $MODULES; do
        [ -z "$MODULE" ] || {
            SUBMODULE="`get_module $module $MODULE`"
            RETVAL=$?
            [ $RETVAL -eq 0 ] || continue

        }
        $PYTHON $WLEVEL "$NOSE_PATH" -P -v $PDB \
            --with-coverage \
            --with-xunit \
            --cover-package=pyroute2 \
            $SKIP_TESTS \
            $COVERAGE $module/$SUBMODULE
        errors=$(($errors + $?))
        mv nosetests.xml xunit-$module.xml
    done
done
exit $errors
