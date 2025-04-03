@echo off
:loop
C:/Users/medev/anaconda3/python.exe c:/Users/medev/CSProjects/cmvpe/create_dataset.py
echo Script crashed. Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop