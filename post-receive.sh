#!/bin/bash
# -*- coding: UTF8 -*-

# Launched by a git hook :
#  $ echo "#!/bin/sh\nsh /home/mystrade/public/post-receive.sh" > /home/mystrade/git/mystrade.git/hooks/post-receive
#  $ chmod +x /home/mystrade/git/mystrade.git/hooks/post-receive

# Remember that this script will be executed by the unix user who push to the
# git repository ; and the script will be executed in ~/public.
export GIT_WORK_TREE=/home/mystrade/public
export GIT_DIR=/home/mystrade/git/mystrade.git
git checkout -f
git reset --hard

# Update requirements
pip install -r requirements.txt

# Apply South migrations
./manage.py migrate

