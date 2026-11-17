$code = @'
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out uint pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, ref Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, ref Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, ref Guid pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, ref Guid pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, ref Guid pguidEventContext);
    int GetMute([MarshalAs(UnmanagedType.Bool)] out bool pbMute);
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
    private static IAudioEndpointVolume GetEndpoint() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var guid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume ep = null;
        dev.Activate(ref guid, 23, 0, out ep);
        return ep;
    }

    public static float GetVolume() {
        var ep = GetEndpoint();
        float vol = 0;
        ep.GetMasterVolumeLevelScalar(out vol);
        return vol * 100f;
    }

    public static void SetVolume(float level) {
        var ep = GetEndpoint();
        var emptyGuid = System.Guid.Empty;
        ep.SetMasterVolumeLevelScalar(level / 100f, ref emptyGuid);
    }

    public static bool GetMute() {
        var ep = GetEndpoint();
        bool mute = false;
        ep.GetMute(out mute);
        return mute;
    }

    public static void SetMute(bool mute) {
        var ep = GetEndpoint();
        var emptyGuid = System.Guid.Empty;
        ep.SetMute(mute, ref emptyGuid);
    }
}
'@

Add-Type -TypeDefinition $code -Language CSharp

$initVol = [AudioController]::GetVolume()
$initMute = [AudioController]::GetMute()
Write-Host "INITIAL_VOLUME=$([math]::Round($initVol))"
Write-Host "INITIAL_MUTE=$initMute"

# Test setting volume to 40%
[AudioController]::SetVolume(40.0)
$newVol = [AudioController]::GetVolume()
Write-Host "NEW_VOLUME=$([math]::Round($newVol))"

# Test muting
[AudioController]::SetMute($true)
Write-Host "MUTED=$([AudioController]::GetMute())"

# Test unmuting
[AudioController]::SetMute($false)
Write-Host "UNMUTED=$([AudioController]::GetMute())"

# Restore initial volume
[AudioController]::SetVolume($initVol)
Write-Host "RESTORED_VOLUME=$([math]::Round([AudioController]::GetVolume()))"
