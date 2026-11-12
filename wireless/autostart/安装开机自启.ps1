# 安装 MYBIT PC Agent 开机自启
# 用法：右键 -> 使用 PowerShell 运行

$ErrorActionPreference = "Stop"

# 自动定位：脚本所在目录的上一级就是项目根
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent (Split-Path -Parent $scriptDir)
Write-Host "项目目录: $projectDir" -ForegroundColor Gray
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$lnkPath = "$startup\MYBIT PC Agent.lnk"

Write-Host "=== 安装 MYBIT PC Agent 开机自启 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 检查文件
$bat = Join-Path $projectDir "start_agent.bat"
if (-not (Test-Path $bat)) {
    Write-Host "错误：找不到 $bat" -ForegroundColor Red
    Write-Host "请先确认项目目录路径正确" -ForegroundColor Yellow
    pause
    exit 1
}

# 2. 检查 python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "错误：找不到 python，请先安装并加入 PATH" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "python: $($py.Source)" -ForegroundColor Green

# 3. 创建快捷方式
Remove-Item $lnkPath -Force -ErrorAction SilentlyContinue
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = "C:\Windows\System32\cmd.exe"
$lnk.Arguments = "/c `"$bat`""
$lnk.WorkingDirectory = $projectDir
$lnk.WindowStyle = 7
$lnk.Description = "MYBIT PC Agent"
$lnk.Save()

Write-Host "快捷方式已创建：" -ForegroundColor Green
Write-Host "  $lnkPath"

# 4. 立即启动
Write-Host ""
Write-Host "正在启动..." -ForegroundColor Cyan
Start-Process -FilePath $lnkPath
Start-Sleep -Seconds 8

# 5. 验证
$ps = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -match 'pc_agent' }
if ($ps) {
    Write-Host ""
    Write-Host "✓ 启动成功，PID: $($ps.ProcessId)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ 启动失败，请查看 pc_agent.log" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 完成 ===" -ForegroundColor Cyan
Write-Host "以后开机自动运行，不用手动管"
Write-Host "要停止：任务管理器里结束 python.exe，或删掉启动文件夹里的快捷方式"
Write-Host ""
pause