#!/usr/bin/env bash
set -euo pipefail

mkdir -p static/fonts
cp node_modules/font-awesome/fonts/* ./static/fonts
cp node_modules/font-awesome/css/font-awesome.min.css ./static/css

cp node_modules/flatpickr/dist/flatpickr.min.css ./static/css
