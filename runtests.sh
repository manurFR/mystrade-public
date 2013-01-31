#!/bin/bash
# -*- coding: UTF8 -*-

APPS=`python -c "from mystrade.settings import MYSTRADE_APPS; print ' '.join(MYSTRADE_APPS)"`

for app in ${APPS}; do
	echo "**** Tests for app:           ${app}"
	./manage.py test ${app}
  if [[ $? != 0 ]]; then
    echo "TESTS FAILURE !"
    exit 1
  fi
  echo "/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\"
done

echo
echo "=================="
echo "  All tests OK    "
echo "=================="

exit 0
