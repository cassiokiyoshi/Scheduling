use scripting additions
property serverPID : ""

on run
    if serverPID is not "" then return
    set serverExecutable to POSIX path of (path to resource "den-scheduler")
    set logFolder to (POSIX path of (path to library folder from user domain)) & "Logs/DEN Scheduler"
    do shell script "/bin/mkdir -p " & quoted form of logFolder
    set serverPID to do shell script ("/usr/bin/nohup " & quoted form of serverExecutable & " > " & quoted form of (logFolder & "/standalone.log") & " 2>&1 & echo $!")
end run

on idle
    if serverPID is not "" then
        try
            do shell script "/bin/kill -0 " & serverPID
        on error
            set serverPID to ""
            display dialog "DEN Scheduler stopped. See Library/Logs/DEN Scheduler/standalone.log for details." buttons {"OK"} default button "OK"
            quit
        end try
    end if
    return 5
end idle

on quit
    if serverPID is not "" then
        try
            do shell script "/bin/kill -TERM " & serverPID
        end try
        set serverPID to ""
    end if
    continue quit
end quit
