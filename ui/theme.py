"""
ui/theme.py
-----------
Approved application-wide color palette.

Warm natural system harmonising with the bamboo / ivory background.
All values are hex strings usable directly as Flet color arguments.

Usage:
    from ui.theme import _C_ACCENT, _C_BORDER, ...

Do not import individual Flet Colors.* defaults for these roles;
use these constants instead so the palette stays centrally managed.
"""

# ---------------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------------
_C_BG_APP   = "#F5F2EC"  # overall app background (warm ivory)
_C_BG_MAIN  = "#FAFAF7"  # main working surface
_C_BG_PANEL = "#F0EDE6"  # subtle surface — form / secondary panels
_C_BG_WARN  = "#FDF3E3"  # warning banner background

# ---------------------------------------------------------------------------
# Borders / dividers
# ---------------------------------------------------------------------------
_C_BORDER = "#D8D3C8"  # input borders, dividers, card outlines

# ---------------------------------------------------------------------------
# Accent family — sage green
# ---------------------------------------------------------------------------
_C_ACCENT          = "#5C7A63"  # primary action
_C_ACCENT_ACTIVE   = "#3E5A45"  # hover / pressed state
_C_ACCENT_SECONDARY = "#7A8C7E"  # secondary accent / in-progress indicator

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
_C_TEXT_PRIMARY   = "#2A2A25"  # main body text
_C_TEXT_SECONDARY = "#5A5850"  # section labels, secondary labels
_C_TEXT_HELPER    = "#8A877E"  # hints, helper text, passive labels

# ---------------------------------------------------------------------------
# Semantic status colors
# ---------------------------------------------------------------------------
_C_OK          = "#4A7260"  # success / positive status
_C_WARN        = "#8A5A1A"  # caution / destructive (restrained amber)
_C_ERR         = "#8A3030"  # error (dark warm red)
_C_DISABLED    = "#B8B5AE"  # disabled / inactive controls
_C_IN_PROGRESS = "#7A8C7E"  # neutral indicator for running operations
