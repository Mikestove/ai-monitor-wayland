#!/usr/bin/env bash
export GDK_BACKEND=x11
exec python3 "$(dirname "$(realpath "$0")")/main.py" "$@"
