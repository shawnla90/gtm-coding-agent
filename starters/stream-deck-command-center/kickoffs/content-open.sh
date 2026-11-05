#!/bin/bash
# KICKOFF 4 (silent): reveal the current pack folder in Finder. This is the human gate:
# you read the drafts and renders here and decide what ships. Nothing in this kit posts.
source "$(dirname "$0")/_lib.sh"
slug="$(current_slug)"
/usr/bin/open "$DRAFTS_DIR/${slug:-}"
