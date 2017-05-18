#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

redis-cli --scan --pattern 'cache:*' | xargs redis-cli del
