#!/bin/bash
cd /app/project
git checkout develop
git checkout -b release/v2.3.1
git push origin release/v2.3.1
