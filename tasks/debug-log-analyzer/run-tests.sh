#!/bin/bash
set -e
cd /tests
if [ -f setup-pytest.sh ]; then bash setup-pytest.sh; fi
bash run-pytest.sh
