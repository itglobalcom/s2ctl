# use this to run `powershell -noexit "&" ".\bundle\build_win.ps1"`
Write-Output ">>> PREPARE PYTHON VIRTUAL ENVIRONMENT"
#poetry install -n --no-ansi
Set-Location .\bundle

Write-Output ">>> BUNDLING STARTED"
pyinstaller -y --clean --onefile -n s2ctl bundle.py
Write-Output ">>> BUNDLE CREATED"

Remove-Item -Force -Recurse build
Remove-Item -Force -Recurse s2ctl.spec
Set-Location ..
Write-Output "get your exe in .\bundle\dist"
