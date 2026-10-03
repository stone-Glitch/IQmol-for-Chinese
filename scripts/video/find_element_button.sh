#!/bin/bash
# Sweep the toolbar to locate the elementSelectButton ("C") that opens the
# Periodic Table popup. Detects success by the popup's X window title
# ("Periodic Table" / "元素周期表"). No image reading required.
set -u
export DISPLAY=:99

MAIN_WID=4194314
Y=76            # toolbar vertical center (window at 1,22, content begins ~22)
DISM_X=400      # safe menu-bar point to dismiss any popup
DISM_Y=30

popup_open() {
  # returns 0 if a Periodic Table popup window exists
  DISPLAY=:99 xdotool search --name 'Periodic Table' 2>/dev/null | grep -q .
}

dismiss() {
  DISPLAY=:99 xdotool mousemove "$DISM_X" "$DISM_Y"
  DISPLAY=:99 xdotool click 1
  sleep 0.25
}

FOUND=""
for x in $(seq 235 5 330); do
  # ensure clean state
  dismiss
  sleep 0.15
  # click candidate
  DISPLAY=:99 xdotool mousemove "$x" "$Y"
  DISPLAY=:99 xdotool click 1
  sleep 0.45
  if popup_open; then
    FOUND="$x"
    echo "FOUND elementSelectButton at x=$x (y=$Y)"
    break
  fi
done

if [ -z "$FOUND" ]; then
  echo "NOT FOUND in range; popup last state:"
  DISPLAY=:99 xdotool search --name 'Table' 2>/dev/null
  exit 1
fi

# Report popup window geometry for framing
POP_WID=$(DISPLAY=:99 xdotool search --name 'Periodic Table' 2>/dev/null | head -1)
echo "Popup WID=$POP_WID"
DISPLAY=:99 xdotool getwindowgeometry "$POP_WID" 2>/dev/null
echo "ELEMENT_BUTTON_X=$FOUND"
