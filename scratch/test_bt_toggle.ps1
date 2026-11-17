param([string]$TargetState = "Off")

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
}

Function Await-WinRT($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(3000) | Out-Null
    return $netTask.Result
}

[Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType = WindowsRuntime] | Out-Null
$radios = Await-WinRT ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$bt = $radios | Where-Object { $_.Kind -eq [Windows.Devices.Radios.RadioKind]::Bluetooth }

if (-not $bt) {
    Write-Host "STATUS=NO_BLUETOOTH_RADIO"
    exit 1
}

Write-Host "INITIAL_STATE=$($bt.State)"

$targetEnum = if ($TargetState -match "on") { [Windows.Devices.Radios.RadioState]::On } else { [Windows.Devices.Radios.RadioState]::Off }

if ($bt.State -eq $targetEnum) {
    Write-Host "ALREADY_IN_STATE=$($bt.State)"
    Write-Host "FINAL_STATE=$($bt.State)"
    exit 0
}

$accessStatus = Await-WinRT ($bt.SetStateAsync($targetEnum)) ([Windows.Devices.Radios.RadioAccessStatus])
Write-Host "ACCESS_STATUS=$accessStatus"

Start-Sleep -Milliseconds 500
Write-Host "FINAL_STATE=$($bt.State)"
