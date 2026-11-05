#!/bin/bash
# One key, several apps. Swap in whatever you keep open while you build.
source "$(dirname "$0")/_common.sh"
open_app_or_url "ChatGPT" "https://chatgpt.com/"
open_app_or_url "Claude" "https://claude.ai/"
open_app "Terminal"
open_url "https://github.com/pulls"
