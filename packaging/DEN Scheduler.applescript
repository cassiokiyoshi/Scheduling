use scripting additions

on run
    set bundledAppScript to POSIX path of (path to resource "app.py" in directory "project")
    set bundledProjectFolder to do shell script ("/usr/bin/dirname " & quoted form of bundledAppScript)
    set userHome to system attribute "HOME"
    set supportFolder to userHome & "/Library/Application Support/DEN Scheduler"
    set projectFolder to supportFolder & "/project"
    set appScript to projectFolder & "/app.py"
    set requirementsFile to projectFolder & "/requirements.txt"
    set pythonPath to supportFolder & "/.venv/bin/python"
    set logDir to supportFolder & "/logs"
    set pidFile to supportFolder & "/server.pid"
    set quotedBundledProjectFolder to quoted form of bundledProjectFolder
    set quotedPythonPath to quoted form of pythonPath
    set quotedAppScript to quoted form of appScript
    set quotedRequirementsFile to quoted form of requirementsFile
    set quotedProjectFolder to quoted form of projectFolder
    set quotedLogDir to quoted form of logDir
    set quotedLogFile to quoted form of (logDir & "/streamlit.log")
    set quotedPidFile to quoted form of pidFile

    try
        do shell script "/usr/bin/curl -fsS --max-time 1 http://localhost:8501/_stcore/health >/dev/null"
        open location "http://localhost:8501"
        return
    end try

    try
        do shell script ("/bin/mkdir -p " & quoted form of supportFolder & " && /usr/bin/ditto " & quotedBundledProjectFolder & " " & quotedProjectFolder)
    on error errorMessage
        display dialog "DEN Scheduler could not prepare its local files.\n\n" & errorMessage buttons {"OK"} default button "OK" with icon caution
        return
    end try

    try
        do shell script ("/bin/test -f " & quotedAppScript & " && /bin/test -f " & quotedRequirementsFile)
    on error
        display dialog "DEN Scheduler's built-in files are missing. Please replace the app with a fresh copy." buttons {"OK"} default button "OK" with icon caution
        return
    end try

    set environmentReady to false
    try
        do shell script (quotedPythonPath & " -c " & quoted form of "import streamlit, pandas, openpyxl; raise SystemExit(0 if streamlit.__version__ == '1.50.0' else 1)")
        set environmentReady to true
    end try

    if environmentReady is false then
        set installChoice to display dialog "DEN Scheduler needs to install its local components on this Mac. This happens only once and requires an internet connection.\n\nPython 3.9 or newer must already be installed." buttons {"Cancel", "Install"} default button "Install" with icon note
        if button returned of installChoice is not "Install" then return

        try
            set pythonCommand to do shell script "/bin/zsh -lc 'command -v python3'"
            if pythonCommand is "" then error "Python 3 was not found."
            set quotedPythonCommand to quoted form of pythonCommand
            set installCommand to ("/bin/mkdir -p " & quotedLogDir & " && " & quotedPythonCommand & " -c " & quoted form of "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" & " && " & quotedPythonCommand & " -m venv --clear " & quoted form of (supportFolder & "/.venv") & " && " & quotedPythonPath & " -m pip install --upgrade pip && " & quotedPythonPath & " -m pip install -r " & quotedRequirementsFile)
            with timeout of 1200 seconds
                do shell script installCommand
            end timeout
        on error errorMessage
            if (length of errorMessage) > 1200 then set errorMessage to text 1 thru 1200 of errorMessage
            display dialog "Installation could not be completed.\n\nMake sure Python 3.9+ is installed and the Mac is connected to the internet.\n\nDetails:\n" & errorMessage buttons {"OK"} default button "OK" with icon caution
            return
        end try
    end if

    try
        do shell script "/usr/bin/curl -fsS --max-time 1 http://localhost:8501/_stcore/health >/dev/null"
    on error
        do shell script ("/bin/mkdir -p " & quotedLogDir & "; cd " & quotedProjectFolder & "; /usr/bin/nohup " & quotedPythonPath & " -m streamlit run app.py --server.headless true --server.port 8501 > " & quotedLogFile & " 2>&1 & /bin/echo $! > " & quotedPidFile)
        delay 2
    end try

    open location "http://localhost:8501"
end run

on idle
    return 30
end idle

on quit
    set userHome to system attribute "HOME"
    set pidFile to userHome & "/Library/Application Support/DEN Scheduler/server.pid"
    set quotedPidFile to quoted form of pidFile
    try
        do shell script ("if /bin/test -f " & quotedPidFile & "; then /bin/kill $(/bin/cat " & quotedPidFile & ") 2>/dev/null || true; /bin/rm -f " & quotedPidFile & "; fi")
    end try
    continue quit
end quit
