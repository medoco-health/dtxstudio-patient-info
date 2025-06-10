@echo off
rem This is the PMS OPP Web API batch file that will merge two patients together
rem It uses the PMSID of each patient to perform the merge.
@echo *******************************************************
@echo *****Welcome to the DTX Patient Merge Application!*****
@echo *******************************************************
@echo.
pause
cls
rem The input file name that is being requested should be placed into the same
rem folder with this batch file.  Failure to put these two files together
rem will result in the user having to input the full pathname plus the file name.
rem The input file contains the src pms_id next to the targed pms_id, seperated with 
rem a comma, and must be created beforehand.
rem If the window closes before starting the script then the path or the file name
rem was invalid and unable to be parsed correctly.
@echo *********************************************************
@echo *****      You will now be asked two questions:     *****
@echo *****                                               *****
@echo *****The file name that contains the old and new IDs*****
@echo *****         and the PMS Bearer Token.             *****
@echo *****       Both are REQUIRED to proceed.           *****
@echo *********************************************************
@echo.
@echo.
pause
cls
setlocal enabledelayedexpansion
 
set /p inputFile="Enter the input file name: "
 
set /p BearerToken="Enter the PMS Bearer Token: "
 
for /f "tokens=1,2 delims=," %%a in (%inputFile%) do (
    set "src=%%a"
    set "trg=%%b"
    curl -s -S -i --insecure -X PUT "https://localhost:44389/api/message" -H "Content-Type: application/json" -H "Authorization: Bearer !BearerToken!" -d "{\"header\":{\"version\":\"1.0\"},\"message\":{\"contract\":\"patient\",\"operation\":\"merge.request\",\"context\":{},\"sourcePatientId\":\"!src!\",\"targetPatientId\":\"!trg!\"}}" >> merge_log.txt 2>> merge_error_log.txt
)
 
endlocal