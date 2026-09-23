"""Frozen entry point: run the bundled scheduler without an installed Python."""
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

sys.path.insert(0, str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))))

# These imports also tell PyInstaller which application dependencies to bundle.
import pandas
import openpyxl
from PIL import Image
import scheduler
import importer
import excel_export
from streamlit.web import bootstrap


def main():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    os.chdir(root)
    sys.path.insert(0, str(root))
    if '--self-test' in sys.argv:
        from datetime import date
        from io import BytesIO
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(root / 'app.py')).run()
        assert not app.exception, app.exception
        with (root / 'assets/den-reference.xlsx').open('rb') as reference:
            output = excel_export.reference_schedule_workbook(reference, [], date(2026, 10, 1), ['Alex'])
        sheet = openpyxl.load_workbook(BytesIO(output)).active
        assert sheet['L8'].value == 'ZAC'
        assert sheet['K28'].data_type == 'f'
        print('Standalone startup and Excel export passed.', flush=True)
        return
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'

    def open_when_ready():
        for _ in range(120):
            try:
                with urllib.request.urlopen(url + '/_stcore/health', timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        return
            except OSError:
                pass
            time.sleep(0.5)

    threading.Thread(target=open_when_ready, daemon=True).start()
    options = {
        'server.address': '127.0.0.1', 'server.port': port,
        'server.headless': True, 'server.fileWatcherType': 'none',
        'browser.gatherUsageStats': False,
        'global.developmentMode': False, 'server.enableCORS': True,
    }
    bootstrap.load_config_options(options)
    bootstrap.run(str(root / 'app.py'), False, [], options)


if __name__ == '__main__':
    main()
