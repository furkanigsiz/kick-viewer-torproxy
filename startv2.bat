@echo off
echo [*] Cleaning data folders...
for %%i in (1 2 3 4 5 6 7 8 9 10 11 12) do (
    if %%i==1 (
        rmdir /s /q "tor-expert-bundle-windows-x86_64-15.0.3\data" 2>nul
        mkdir "tor-expert-bundle-windows-x86_64-15.0.3\data"
    ) else (
        rmdir /s /q "tor-expert-bundle-windows-x86_64-15.0.3\data%%i" 2>nul
        mkdir "tor-expert-bundle-windows-x86_64-15.0.3\data%%i"
    )
)

echo [*] Starting 12 Tor instances in background...
cd tor-expert-bundle-windows-x86_64-15.0.3\tor
start /b tor.exe -f torrc 2>nul
start /b tor.exe -f ..\tor2\torrc 2>nul
start /b tor.exe -f ..\tor3\torrc 2>nul
start /b tor.exe -f ..\tor4\torrc 2>nul
start /b tor.exe -f ..\tor5\torrc 2>nul
start /b tor.exe -f ..\tor6\torrc 2>nul
start /b tor.exe -f ..\tor7\torrc 2>nul
start /b tor.exe -f ..\tor8\torrc 2>nul
start /b tor.exe -f ..\tor9\torrc 2>nul
start /b tor.exe -f ..\tor10\torrc 2>nul
start /b tor.exe -f ..\tor11\torrc 2>nul
start /b tor.exe -f ..\tor12\torrc 2>nul
cd ..\..

echo [*] Waiting for Tor instances to bootstrap...
echo.
python tor_bootstrap_check.py

echo.
echo [*] Starting viewer bot v2...
python kickv2.py
pause
