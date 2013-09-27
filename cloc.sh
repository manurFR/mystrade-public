#!/bin/bash
# -*- coding: UTF8 -*-
FILE=cloc.log

date >> $FILE
cloc . --exclude-dir=migrations,jquery,.idea,.git | tee -a $FILE
echo >> $FILE
