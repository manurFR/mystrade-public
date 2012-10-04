#!/bin/bash
# -*- coding: UTF8 -*-

APPS=`python -c "from mystrade.settings import MYSTRADE_APPS; print ' '.join(MYSTRADE_APPS)"`

./manage.py test ${APPS}
