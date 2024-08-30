#!/bin/bash
npm install --legacy-peer-deps
npm run ${1:-build}
