#!/bin/zsh
set -eu
PROJECT_DIR="${0:A:h:h}"
cd "$PROJECT_DIR"
export PYINSTALLER_CONFIG_DIR="$PROJECT_DIR/build/pyinstaller-cache"
"$PROJECT_DIR/.venv/bin/python" -m PyInstaller --noconfirm --onefile \
  --name den-scheduler --paths "$PROJECT_DIR" \
  --collect-all streamlit --copy-metadata streamlit \
  --collect-all altair --collect-all pydeck \
  --add-data "$PROJECT_DIR/app.py:." --add-data "$PROJECT_DIR/assets:assets" \
  --add-data "$PROJECT_DIR/DEN shift availability.csv:." \
  --add-data "$PROJECT_DIR/.streamlit:.streamlit" \
  --specpath build --workpath build/pyinstaller --distpath build/bin \
  packaging/standalone.py
APP_PATH="$PROJECT_DIR/dist/DEN Scheduler.app"
mkdir -p "$PROJECT_DIR/dist"
/usr/bin/osacompile -l AppleScript -o "$APP_PATH" "$PROJECT_DIR/packaging/DEN Scheduler.applescript"
/usr/libexec/PlistBuddy -c "Set :OSAAppletStayOpen true" "$APP_PATH/Contents/Info.plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :OSAAppletStayOpen bool true" "$APP_PATH/Contents/Info.plist"
/bin/cp "$PROJECT_DIR/build/bin/den-scheduler" "$APP_PATH/Contents/Resources/den-scheduler"
"$PROJECT_DIR/.venv/bin/python" -c 'from PIL import Image; Image.open("assets/den-scheduler-icon.png").save("dist/DEN Scheduler.app/Contents/Resources/applet.icns")'
/usr/bin/codesign --force --deep --sign - "$APP_PATH"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$PROJECT_DIR/dist/DEN Scheduler.zip"
echo "Created: $APP_PATH"
