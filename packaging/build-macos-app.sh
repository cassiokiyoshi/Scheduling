#!/bin/zsh

set -eu

PROJECT_DIR="${0:A:h:h}"
APP_PATH="$PROJECT_DIR/DEN Scheduler.app"
ICON_SOURCE="$PROJECT_DIR/assets/den-scheduler-icon.png"
ICONSET_DIR="$PROJECT_DIR/packaging/DEN.iconset"

/usr/bin/osacompile -l AppleScript -o "$APP_PATH" "$PROJECT_DIR/packaging/DEN Scheduler.applescript"
if ! /usr/libexec/PlistBuddy -c "Set :OSAAppletStayOpen true" "$APP_PATH/Contents/Info.plist" 2>/dev/null; then
  /usr/libexec/PlistBuddy -c "Add :OSAAppletStayOpen bool true" "$APP_PATH/Contents/Info.plist"
fi

/bin/mkdir -p "$ICONSET_DIR"
for size in 16 32 128 256 512; do
  /usr/bin/sips -z "$size" "$size" "$ICON_SOURCE" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
  double_size=$((size * 2))
  /usr/bin/sips -z "$double_size" "$double_size" "$ICON_SOURCE" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
done
/usr/bin/iconutil -c icns "$ICONSET_DIR" -o "$APP_PATH/Contents/Resources/applet.icns"

# Bundle the scheduler itself so the .app can be moved anywhere and does not
# depend on sibling files in a particular folder layout.
PROJECT_RESOURCES="$APP_PATH/Contents/Resources/project"
/bin/mkdir -p "$PROJECT_RESOURCES/assets" "$PROJECT_RESOURCES/.streamlit"
/bin/cp "$PROJECT_DIR/app.py" "$PROJECT_DIR/scheduler.py" "$PROJECT_DIR/importer.py" "$PROJECT_DIR/excel_export.py" "$PROJECT_DIR/csv_export.py" "$PROJECT_DIR/requirements.txt" "$PROJECT_RESOURCES/"
/bin/cp "$PROJECT_DIR/2026 DEN shift - 26.09.csv" "$PROJECT_RESOURCES/"
/bin/cp "$PROJECT_DIR/DEN shift availability.csv" "$PROJECT_RESOURCES/"
/bin/cp "$PROJECT_DIR/assets/den-scheduler-icon.webp" "$PROJECT_DIR/assets/den-scheduler-icon.png" "$PROJECT_RESOURCES/assets/"
/bin/cp "$PROJECT_DIR/.streamlit/config.toml" "$PROJECT_RESOURCES/.streamlit/config.toml"
/usr/bin/touch "$APP_PATH"

# Re-sign after replacing the compiled app's icon. Changing any bundled
# resource invalidates osacompile's original signature and macOS may then
# report the copied application as "damaged".
/usr/bin/codesign --force --deep --sign - "$APP_PATH"

echo "Created: $APP_PATH"
