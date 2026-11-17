import subprocess
import json

def run_ps(script: str):
    res = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script], capture_output=True, text=True, timeout=10)
    return res.stdout.strip(), res.stderr.strip()

print("=== 1. TESTING BLUETOOTH ===")
bt_script = """
try {
    [Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType = WindowsRuntime] | Out-Null
    $radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
    $asTask = [WindowsRuntimeSystemExtensions]::AsTask($radios)
    if ($asTask.Wait(3000)) {
        foreach ($r in $asTask.Result) {
            Write-Host "Radio: $($r.Name) | Kind: $($r.Kind) | State: $($r.State)"
        }
    } else {
        Write-Host "Radio async task timed out."
    }
} catch {
    Write-Host "Bluetooth error: $_"
}
"""
out, err = run_ps(bt_script)
print("OUT:", out)
print("ERR:", err)

print("\n=== 2. TESTING VOLUME & AUDIO ===")
vol_script = """
$code = @'
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {
    int f(); int g(); int h(); int j();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int k();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
public class MMDeviceEnumeratorComObject { }

public class AudioController {
    public static float GetVolume() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var guid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume ep = null;
        dev.Activate(ref guid, 23, 0, out ep);
        float vol = 0;
        ep.GetMasterVolumeLevelScalar(out vol);
        return vol * 100f;
    }
    public static void SetVolume(float level) {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var guid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume ep = null;
        dev.Activate(ref guid, 23, 0, out ep);
        ep.SetMasterVolumeLevelScalar(level / 100f, System.Guid.Empty);
    }
    public static bool GetMute() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var guid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume ep = null;
        dev.Activate(ref guid, 23, 0, out ep);
        bool mute = false;
        ep.GetMute(out mute);
        return mute;
    }
    public static void SetMute(bool mute) {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var guid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume ep = null;
        dev.Activate(ref guid, 23, 0, out ep);
        ep.SetMute(mute, System.Guid.Empty);
    }
}
'@
Add-Type -TypeDefinition $code -Language CSharp
$v = [AudioController]::GetVolume()
$m = [AudioController]::GetMute()
Write-Host "Current Volume: $([math]::Round($v))%"
Write-Host "Mute: $m"
"""
out, err = run_ps(vol_script)
print("OUT:", out)
print("ERR:", err)

print("\n=== 3. TESTING BRIGHTNESS ===")
br_script = """
try {
    $b = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
    Write-Host "Current Brightness: $($b.CurrentBrightness)%"
} catch {
    Write-Host "WMI Brightness check failed: $_"
}
"""
out, err = run_ps(br_script)
print("OUT:", out)
print("ERR:", err)
