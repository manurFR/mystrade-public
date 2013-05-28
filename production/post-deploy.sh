#!/bin/bash
# -*- coding: UTF8 -*-

# Called by deploy.sh, as user mystrade and with a clean environment (no variables).
PROD_DIR=$HOME/mystrade/production
DEPLOY_OK=0

# Update .bash_profile
cp -f $PROD_DIR/.bash_profile $HOME
if (( ! $? )); then
    DEPLOY_OK=1
    echo "** WARNING ** [cp -f $PROD_DIR/.bash_profile $HOME] failed";
fi

# Source .bash_profile (to get PYTHONPATH, DJANGO_SETTINGS_MODULE, etc. which make manage.py work)
source $HOME/.bash_profile

# Update requirements, installing the modules in personal modules directory (python-modules) per alwaysdata policy
# note: the first time we needed PYTHONPATH=$HOME/python-modules easy_install-2.6 --install-dir $HOME/python-modules markdown==2.3.1
$HOME/python-modules/pip install -t $HOME/python-modules -U -r $PROD_DIR/requirements_production.txt
if (( ! $? )); then
    DEPLOY_OK=1
    echo "** WARNING ** [$HOME/python-modules/pip install -t $HOME/python-modules -U -r $PROD_DIR/requirements_production.txt] failed";
fi

# Copy settings_production.py to its rightful place
cp -f $PROD_DIR/settings_production.py $HOME/mystrade/mystrade/
if (( ! $? )); then
    DEPLOY_OK=1
    echo "** WARNING ** [cp -f $PROD_DIR/settings_production.py $HOME/mystrade/mystrade/] failed";
fi

# Apply South migrations
$HOME/mystrade/manage.py migrate
if (( ! $? )); then
    DEPLOY_OK=1
    echo "** WARNING ** [$HOME/mystrade/manage.py migrate] failed";
fi

# Collect staticfiles
$HOME/mystrade/manage.py collectstatic --noinput
if (( ! $? )); then
    DEPLOY_OK=1
    echo "** WARNING ** [$HOME/mystrade/manage.py collectstatic --noinput] failed";
fi

if (( $DEPLOY_OK )); then
    echo "The deployment has been correctly performed. Now you should manually restart the FastCGI process through alwaysdata's web console.";
else
    echo "** Some problems were encountered during the deployment. Please fix the server before restarting the FastCGI process.";
fi

exit $DEPLOY_OK
