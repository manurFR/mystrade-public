#!/bin/bash
# -*- coding: UTF8 -*-

# Called by the post-receive git hook, as user mystrade and with a clean environment (no variables).

# Let's update the "working tree", ie the deployed production files
export GIT_WORK_TREE=$HOME/mystrade
export GIT_DIR=$HOME/git/mystrade.git
git checkout -f
git reset --hard

# The rest of the deploy process is done in another file, which has just been updated. This way, any
#  modification to the process can be applied directly in the push that brought it, not the next one.
$HOME/mystrade/production/post-deploy.sh
