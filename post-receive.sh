#!/bin/bash
# -*- coding: UTF8 -*-

# Launched by a git hook :
#  $ echo "#!/bin/sh\nsh /home/mystrade/mystrade/post-receive.sh" > /home/mystrade/git/mystrade.git/hooks/post-receive
#  $ chmod +x /home/mystrade/git/mystrade.git/hooks/post-receive

# Remember that this script will be executed by the unix user who push to the
# git repository ; and the script will be executed in ~/public.
export GIT_WORK_TREE=/home/mystrade/mystrade
export GIT_DIR=/home/mystrade/git/mystrade.git
git checkout -f
git reset --hard

# Update requirements, installing the modules in alwaysdata specific directory
PYTHONPATH=~/python-modules ~/python-modules/pip install -t ~/python-modules -U -r requirements_production.txt
# note: the first time we needed PYTHONPATH=~/python-modules easy_install-2.6 --install-dir ~/python-modules markdown==2.3.1

# Apply South migrations
./manage.py migrate

