# shellcheck shell=bash
# ANSI color constants for the panther-ivy-plugin statusline.
# Sourced by main.sh and segment helpers.
#
# Honors CLAUDE_STATUSLINE_COLORS (matches the user's global statusline) and
# the standard NO_COLOR env var. When colors are disabled every constant is
# the empty string so callers can interpolate unconditionally.

if [ -n "${NO_COLOR:-}" ] || [ "${CLAUDE_STATUSLINE_COLORS:-true}" = "false" ]; then
    C_RESET=""
    C_BOLD=""
    C_DIM=""
    C_RED=""
    C_GREEN=""
    C_YELLOW=""
    C_CYAN=""
    C_WHITE=""
else
    C_RESET=$'\033[0m'
    C_BOLD=$'\033[1m'
    C_DIM=$'\033[2m'
    C_RED=$'\033[31m'
    C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'
    C_CYAN=$'\033[36m'
    C_WHITE=$'\033[37m'
fi

export C_RESET C_BOLD C_DIM C_RED C_GREEN C_YELLOW C_CYAN C_WHITE

# When emojis are disabled (matching the global statusline's env var), emit
# textual markers instead.
if [ "${CLAUDE_STATUSLINE_EMOJIS:-true}" = "false" ]; then
    EMO_PROTOCOL=""
    EMO_WARN=""
else
    EMO_PROTOCOL="🐍 "
    EMO_WARN="⚠ "
fi

export EMO_PROTOCOL EMO_WARN
