#! /bin/bash
#
#    Copyright (c) 2025 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#

./devtools/test.sh

while inotifywait -e modify devtools/watchtests.sh devtools/test.sh bin/user/pushover.py bin/user/tests
do
    ./devtools/test.sh $WEEWX $PY_VERSION
done