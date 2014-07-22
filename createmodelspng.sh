#!/bin/bash
# -*- coding: UTF8 -*-

./manage.py graph_models -a -g -X MigrationHistory,ContentType,Session,LogEntry,Group,Permission -o models.png
