try {
    $monitor = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
    $methods = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods -ErrorAction Stop
    
    $initB = $monitor.CurrentBrightness
    Write-Host "INITIAL_BRIGHTNESS=$initB"
    
    # Test setting to 60%
    Invoke-CimMethod -InputObject $methods -MethodName WmiSetBrightness -Arguments @{ Timeout = 1; Brightness = 60 } | Out-Null
    Start-Sleep -Milliseconds 500
    
    $check = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
    Write-Host "NEW_BRIGHTNESS=$($check.CurrentBrightness)"
    
    # Restore initial
    Invoke-CimMethod -InputObject $methods -MethodName WmiSetBrightness -Arguments @{ Timeout = 1; Brightness = [uint32]$initB } | Out-Null
    Start-Sleep -Milliseconds 500
    $restored = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
    Write-Host "RESTORED_BRIGHTNESS=$($restored.CurrentBrightness)"
} catch {
    Write-Host "BRIGHTNESS_UNSUPPORTED=$_"
}
