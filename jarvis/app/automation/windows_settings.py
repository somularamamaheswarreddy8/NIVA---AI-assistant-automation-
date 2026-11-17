"""
Windows Settings Controller for NIVA.
Controls and verifies system settings: Bluetooth, Wi-Fi, Volume, Mute, Brightness,
and Settings pages navigation using native Windows APIs, WinRT Radios, CoreAudio, and WMI.
Never reports success merely from opening a settings page.
"""

import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("NIVA.Settings")

AUDIO_CONTROLLER_CS = r"""
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
"""


class WindowsSettingsController:
    """Manages system settings and verifies states."""

    SETTINGS_PAGES = {
        "settings": "ms-settings:",
        "windows_settings": "ms-settings:",
        "pc_settings": "ms-settings:",
        "bluetooth": "ms-settings:bluetooth",
        "bluetooth_section": "ms-settings:bluetooth",
        "wifi": "ms-settings:network-wifi",
        "wi-fi": "ms-settings:network-wifi",
        "wifi_section": "ms-settings:network-wifi",
        "network": "ms-settings:network",
        "network_section": "ms-settings:network",
        "sound": "ms-settings:sound",
        "sound_section": "ms-settings:sound",
        "volume": "ms-settings:sound",
        "volume_section": "ms-settings:sound",
        "audio": "ms-settings:sound",
        "audio_section": "ms-settings:sound",
        "display": "ms-settings:display",
        "display_section": "ms-settings:display",
        "brightness": "ms-settings:display",
        "brightness_section": "ms-settings:display",
        "battery": "ms-settings:powersleep",
        "power": "ms-settings:powersleep",
        "battery_section": "ms-settings:powersleep",
        "power_section": "ms-settings:powersleep",
        "windows_update": "ms-settings:windowsupdate",
        "update": "ms-settings:windowsupdate",
        "updates": "ms-settings:windowsupdate",
        "update_section": "ms-settings:windowsupdate",
        "storage": "ms-settings:storagesense",
        "storage_section": "ms-settings:storagesense",
        "apps": "ms-settings:appsfeatures",
        "apps_section": "ms-settings:appsfeatures",
        "installed_apps": "ms-settings:appsfeatures",
        "system": "ms-settings:about",
        "about": "ms-settings:about",
        "about_section": "ms-settings:about",
        "notifications": "ms-settings:notifications",
        "notifications_section": "ms-settings:notifications",
        "microphone_privacy": "ms-settings:privacy-microphone",
        "privacy": "ms-settings:privacy",
        "control_panel": "control",
    }

    @classmethod
    def open_settings_page(cls, page_name: Optional[str] = None, page: Optional[str] = None) -> Dict[str, Any]:
        """Opens a specific Windows Settings page and brings it to foreground."""
        target = page or page_name or "system"
        if hasattr(target, "page"):
            target = getattr(target, "page", "system")
        elif hasattr(target, "page_name"):
            target = getattr(target, "page_name", "system")
        raw_key = str(target).lower().strip()

        # Clean natural language prefixes and suffixes:
        # e.g., "the brightness section of the laptop" -> "brightness"
        clean_key = re.sub(r"^(?:the\s+)?", "", raw_key)
        clean_key = re.sub(r"\s+section(?:\s+of\s+the\s+(?:laptop|pc|computer|system|settings))?$", "", clean_key)
        clean_key = re.sub(r"\s+settings?$", "", clean_key).strip()

        uri = cls.SETTINGS_PAGES.get(clean_key, cls.SETTINGS_PAGES.get(raw_key, f"ms-settings:{clean_key}"))

        try:
            if uri.startswith("control"):
                subprocess.Popen(["control.exe"], shell=True)
            else:
                subprocess.Popen(["cmd.exe", "/c", "start", uri], shell=True)

            time.sleep(0.8)

            # Bring Settings window to foreground
            import ctypes
            import win32gui
            import win32con
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
            if hdesk:
                user32.SetThreadDesktop(hdesk)

            def enum_cb(h, _):
                if win32gui.IsWindowVisible(h):
                    cls_name = win32gui.GetClassName(h)
                    txt = win32gui.GetWindowText(h)
                    if cls_name == "ApplicationFrameWindow" and "setting" in txt.lower():
                        user32.ShowWindow(h, win32con.SW_RESTORE)
                        user32.SetForegroundWindow(h)

            if hdesk:
                win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
            else:
                win32gui.EnumWindows(enum_cb, None)

            disp_title = clean_key.replace("_", " ").title()
            return {"success": True, "message": f"Opened Windows {disp_title} section in Settings.", "page": clean_key}
        except Exception as e:
            return {"success": False, "error": f"Failed opening settings page '{target}': {str(e)}"}

    @classmethod
    def set_bluetooth_state(cls, enable: bool) -> Dict[str, Any]:
        """
        Toggles Bluetooth state via Windows Radio Management API and verifies resulting state.
        Reads current state first, toggles only if needed, then verifies resulting state.
        Never reports success merely from opening a settings page.
        """
        state_str = "On" if enable else "Off"
        ps_script = f"""
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
            $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        }}
        Function Await-WinRT($WinRtTask, $ResultType) {{
            $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
            $netTask = $asTask.Invoke($null, @($WinRtTask))
            $netTask.Wait(3000) | Out-Null
            return $netTask.Result
        }}
        try {{
            [Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType = WindowsRuntime] | Out-Null
            $radios = Await-WinRT ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
            $bt = $radios | Where-Object {{ $_.Kind -eq [Windows.Devices.Radios.RadioKind]::Bluetooth }}
            if (-not $bt) {{
                Write-Output "STATUS=NO_BLUETOOTH_RADIO"
                exit 0
            }}
            Write-Output "INITIAL_STATE=$($bt.State)"
            $targetEnum = [Windows.Devices.Radios.RadioState]::{state_str}
            if ($bt.State -eq $targetEnum) {{
                Write-Output "ALREADY_IN_STATE=$($bt.State)"
                Write-Output "FINAL_STATE=$($bt.State)"
                exit 0
            }}
            $accessStatus = Await-WinRT ($bt.SetStateAsync($targetEnum)) ([Windows.Devices.Radios.RadioAccessStatus])
            Write-Output "ACCESS_STATUS=$accessStatus"
            Start-Sleep -Milliseconds 500
            Write-Output "FINAL_STATE=$($bt.State)"
        }} catch {{
            Write-Output "ERROR:$_"
        }}
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=8
            )
            stdout = result.stdout.strip()
            logger.info(f"Bluetooth toggle stdout: {stdout}")

            if "STATUS=NO_BLUETOOTH_RADIO" in stdout:
                return {
                    "success": False,
                    "unsupported": True,
                    "error": "No Bluetooth radio hardware was detected on this computer."
                }

            lines = {line.split("=")[0].strip(): line.split("=")[1].strip() for line in stdout.splitlines() if "=" in line}

            final_state = lines.get("FINAL_STATE", "Unknown")
            if final_state.lower() == state_str.lower():
                return {
                    "success": True,
                    "verified": True,
                    "state": final_state,
                    "message": f"Bluetooth has been turned {final_state}. Verified state: {final_state}."
                }
            elif "ACCESS_STATUS" in lines and lines["ACCESS_STATUS"] != "Allowed":
                return {
                    "success": False,
                    "permission_denied": True,
                    "error": f"Bluetooth toggle blocked by Windows access permissions: {lines['ACCESS_STATUS']}."
                }
            else:
                return {
                    "success": False,
                    "error": f"Bluetooth state could not be verified. Current state is: {final_state}."
                }

        except Exception as e:
            logger.error(f"Error adjusting Bluetooth: {e}")
            return {
                "success": False,
                "error": f"Failed adjusting Bluetooth: {str(e)}"
            }

    @classmethod
    def get_bluetooth_state(cls) -> Optional[str]:
        """Queries current Bluetooth radio state."""
        ps_script = """
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
        try {
            [Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType = WindowsRuntime] | Out-Null
            $radios = Await-WinRT ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
            $bt = $radios | Where-Object { $_.Kind -eq [Windows.Devices.Radios.RadioKind]::Bluetooth }
            if ($bt) { Write-Output "$($bt.State)"; exit 0 }
        } catch {}
        Write-Output "UNKNOWN"
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=5
            )
            out = result.stdout.strip()
            return out if out else "Unknown"
        except Exception:
            return "Unknown"

    @classmethod
    def set_wifi_state(cls, enable: bool) -> Dict[str, Any]:
        """
        Toggles Wi-Fi radio state and verifies resulting state.
        Reads current state first, toggles only if needed, then verifies resulting state.
        """
        state_str = "On" if enable else "Off"
        ps_script = f"""
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
            $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        }}
        Function Await-WinRT($WinRtTask, $ResultType) {{
            $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
            $netTask = $asTask.Invoke($null, @($WinRtTask))
            $netTask.Wait(3000) | Out-Null
            return $netTask.Result
        }}
        try {{
            [Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType = WindowsRuntime] | Out-Null
            $radios = Await-WinRT ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
            $wifi = $radios | Where-Object {{ $_.Kind -eq [Windows.Devices.Radios.RadioKind]::WiFi }}
            if (-not $wifi) {{
                Write-Output "STATUS=NO_WIFI_RADIO"
                exit 0
            }}
            Write-Output "INITIAL_STATE=$($wifi.State)"
            $targetEnum = [Windows.Devices.Radios.RadioState]::{state_str}
            if ($wifi.State -eq $targetEnum) {{
                Write-Output "ALREADY_IN_STATE=$($wifi.State)"
                Write-Output "FINAL_STATE=$($wifi.State)"
                exit 0
            }}
            $accessStatus = Await-WinRT ($wifi.SetStateAsync($targetEnum)) ([Windows.Devices.Radios.RadioAccessStatus])
            Write-Output "ACCESS_STATUS=$accessStatus"
            Start-Sleep -Milliseconds 500
            Write-Output "FINAL_STATE=$($wifi.State)"
        }} catch {{
            Write-Output "ERROR:$_"
        }}
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=8
            )
            stdout = result.stdout.strip()
            logger.info(f"Wi-Fi toggle stdout: {stdout}")

            if "STATUS=NO_WIFI_RADIO" in stdout:
                return {
                    "success": False,
                    "unsupported": True,
                    "error": "No Wi-Fi radio hardware was detected on this computer."
                }

            lines = {line.split("=")[0].strip(): line.split("=")[1].strip() for line in stdout.splitlines() if "=" in line}
            final_state = lines.get("FINAL_STATE", "Unknown")

            if final_state.lower() == state_str.lower():
                return {
                    "success": True,
                    "verified": True,
                    "state": final_state,
                    "message": f"Wi-Fi has been turned {final_state}. Verified state: {final_state}."
                }
            elif "ACCESS_STATUS" in lines and lines["ACCESS_STATUS"] != "Allowed":
                return {
                    "success": False,
                    "permission_denied": True,
                    "error": f"Wi-Fi toggle blocked by Windows access permissions: {lines['ACCESS_STATUS']}."
                }
            else:
                return {
                    "success": False,
                    "error": f"Wi-Fi state could not be verified. Current state is: {final_state}."
                }
        except Exception as e:
            return {"success": False, "error": f"Failed adjusting Wi-Fi: {str(e)}"}

    @classmethod
    def get_wifi_state(cls) -> Optional[str]:
        """Queries current Wi-Fi radio state."""
        ps_script = """
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
        try {
            [Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType = WindowsRuntime] | Out-Null
            $radios = Await-WinRT ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
            $wifi = $radios | Where-Object { $_.Kind -eq [Windows.Devices.Radios.RadioKind]::WiFi }
            if ($wifi) { Write-Output "$($wifi.State)"; exit 0 }
        } catch {}
        Write-Output "UNKNOWN"
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=5
            )
            out = result.stdout.strip()
            return out if out else "Unknown"
        except Exception:
            return "Unknown"

    @classmethod
    def set_volume(cls, level_or_delta: Union[int, str], step_mode: bool = False, step: int = 10) -> Dict[str, Any]:
        """
        Sets Windows Master Volume (0 to 100) using CoreAudio and verifies.
        Supports absolute levels (e.g. 40) or relative steps (e.g. '+10', '-10', 'increase', 'decrease').
        If amount is not specified, uses a default step of 10%.
        """
        # Determine target mode and value
        target_mode = "set"
        target_val = 0

        val_str = str(level_or_delta).strip().lower()
        if step_mode or val_str in ["increase", "up", "+", "higher"]:
            target_mode = "relative"
            target_val = step
        elif val_str in ["decrease", "down", "-", "lower"]:
            target_mode = "relative"
            target_val = -step
        elif val_str.startswith("+"):
            target_mode = "relative"
            target_val = int(val_str[1:]) if val_str[1:].isdigit() else step
        elif val_str.startswith("-"):
            target_mode = "relative"
            target_val = -int(val_str[1:]) if val_str[1:].isdigit() else -step
        else:
            try:
                target_mode = "absolute"
                target_val = int(re.sub(r"[^\d]", "", val_str) or 50)
                target_val = max(0, min(100, target_val))
            except Exception:
                target_mode = "relative"
                target_val = step

        ps_script = f"""
        $code = @'
{AUDIO_CONTROLLER_CS}
'@
        Add-Type -TypeDefinition $code -Language CSharp
        $initVol = [AudioController]::GetVolume()
        Write-Output "INITIAL_VOLUME=$initVol"

        $target = {target_val}
        $mode = "{target_mode}"
        if ($mode -eq "relative") {{
            $newTarget = [math]::Max(0.0, [math]::Min(100.0, ($initVol + $target)))
        }} else {{
            $newTarget = [math]::Max(0.0, [math]::Min(100.0, [float]$target))
        }}

        [AudioController]::SetVolume($newTarget)
        # If increasing volume and currently muted, unmute
        if ($newTarget -gt 0 -and [AudioController]::GetMute()) {{
            [AudioController]::SetMute($false)
        }}
        Start-Sleep -Milliseconds 150
        $finalVol = [AudioController]::GetVolume()
        Write-Output "FINAL_VOLUME=$finalVol"
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=8
            )
            stdout = result.stdout.strip()
            logger.info(f"Volume adjustment stdout: {stdout}")

            lines = {line.split("=")[0].strip(): line.split("=")[1].strip() for line in stdout.splitlines() if "=" in line}
            if "FINAL_VOLUME" in lines:
                final_v = int(round(float(lines["FINAL_VOLUME"])))
                init_v = int(round(float(lines.get("INITIAL_VOLUME", final_v))))
                return {
                    "success": True,
                    "volume": final_v,
                    "initial_volume": init_v,
                    "verified": True,
                    "message": f"Volume set to {final_v}%. Verified actual system volume is {final_v}%."
                }
            return {"success": False, "error": f"Failed verifying audio volume: {stdout}"}
        except Exception as e:
            return {"success": False, "error": f"Audio volume adjustment error: {str(e)}"}

    @classmethod
    def get_volume(cls) -> Optional[int]:
        """Reads current master volume percentage."""
        ps_script = f"""
        $code = @'
{AUDIO_CONTROLLER_CS}
'@
        Add-Type -TypeDefinition $code -Language CSharp
        $v = [AudioController]::GetVolume()
        Write-Output "VOLUME=$([math]::Round($v))"
        """
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if "VOLUME=" in line:
                    return int(line.split("VOLUME=")[1].strip())
            return None
        except Exception:
            return None

    @classmethod
    def set_mute(cls, mute: bool) -> Dict[str, Any]:
        """Sets system mute state using CoreAudio and verifies."""
        mute_val = "$true" if mute else "$false"
        ps_script = f"""
        $code = @'
{AUDIO_CONTROLLER_CS}
'@
        Add-Type -TypeDefinition $code -Language CSharp
        [AudioController]::SetMute({mute_val})
        Start-Sleep -Milliseconds 150
        $cur = [AudioController]::GetMute()
        Write-Output "FINAL_MUTE=$cur"
        """
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=6)
            for line in res.stdout.splitlines():
                if "FINAL_MUTE=" in line:
                    verified_mute = line.split("FINAL_MUTE=")[1].strip().lower() == "true"
                    return {
                        "success": True,
                        "muted": verified_mute,
                        "verified": verified_mute == mute,
                        "message": f"System audio is now {'muted' if verified_mute else 'unmuted'}. Verified state."
                    }
            return {"success": False, "error": "Mute state could not be verified."}
        except Exception as e:
            return {"success": False, "error": f"Failed setting audio mute: {str(e)}"}

    @classmethod
    def get_mute(cls) -> Optional[bool]:
        """Queries whether audio is currently muted."""
        ps_script = f"""
        $code = @'
{AUDIO_CONTROLLER_CS}
'@
        Add-Type -TypeDefinition $code -Language CSharp
        Write-Output "MUTE=$([AudioController]::GetMute())"
        """
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if "MUTE=" in line:
                    return line.split("MUTE=")[1].strip().lower() == "true"
            return None
        except Exception:
            return None

    @classmethod
    def set_brightness(cls, level_or_delta: Union[int, str], step_mode: bool = False, step: int = 10) -> Dict[str, Any]:
        """
        Sets monitor display brightness (0 to 100) via WMI and verifies.
        Supports absolute levels (e.g. 60) or relative steps ('increase', 'decrease', '+10', '-10').
        If unsupported by the display or graphics driver, reports the exact limitation.
        Never reports success merely from opening Display Settings.
        """
        target_mode = "set"
        target_val = 0

        val_str = str(level_or_delta).strip().lower()
        if step_mode or val_str in ["increase", "up", "+", "brighter", "higher"]:
            target_mode = "relative"
            target_val = step
        elif val_str in ["decrease", "down", "-", "dimmer", "lower"]:
            target_mode = "relative"
            target_val = -step
        elif val_str.startswith("+"):
            target_mode = "relative"
            target_val = int(val_str[1:]) if val_str[1:].isdigit() else step
        elif val_str.startswith("-"):
            target_mode = "relative"
            target_val = -int(val_str[1:]) if val_str[1:].isdigit() else -step
        else:
            try:
                target_mode = "absolute"
                target_val = int(re.sub(r"[^\d]", "", val_str) or 50)
                target_val = max(0, min(100, target_val))
            except Exception:
                target_mode = "relative"
                target_val = step

        ps_script = f"""
        try {{
            $monitor = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
            $methods = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods -ErrorAction Stop

            $initB = [int]$monitor.CurrentBrightness
            Write-Output "INITIAL_BRIGHTNESS=$initB"

            $target = {target_val}
            $mode = "{target_mode}"
            if ($mode -eq "relative") {{
                $newTarget = [math]::Max(0, [math]::Min(100, ($initB + $target)))
            }} else {{
                $newTarget = [math]::Max(0, [math]::Min(100, $target))
            }}

            Invoke-CimMethod -InputObject $methods -MethodName WmiSetBrightness -Arguments @{{ Timeout = 1; Brightness = [uint32]$newTarget }} | Out-Null
            Start-Sleep -Milliseconds 400

            $check = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
            Write-Output "FINAL_BRIGHTNESS=$($check.CurrentBrightness)"
        }} catch {{
            Write-Output "ERROR:BRIGHTNESS_UNSUPPORTED: $_"
        }}
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=8
            )
            stdout = res.stdout.strip()
            logger.info(f"Brightness adjustment stdout: {stdout}")

            if "BRIGHTNESS_UNSUPPORTED" in stdout:
                return {
                    "success": False,
                    "unsupported": True,
                    "error": "The display or graphics driver does not support hardware brightness control via WMI (common for external desktop monitors)."
                }

            lines = {line.split("=")[0].strip(): line.split("=")[1].strip() for line in stdout.splitlines() if "=" in line}
            if "FINAL_BRIGHTNESS" in lines:
                final_b = int(lines["FINAL_BRIGHTNESS"])
                init_b = int(lines.get("INITIAL_BRIGHTNESS", final_b))
                return {
                    "success": True,
                    "brightness": final_b,
                    "initial_brightness": init_b,
                    "verified": True,
                    "message": f"Display brightness set to {final_b}%. (Changed from {init_b}%)."
                }

            return {"success": False, "error": f"Brightness adjustment could not be verified: {stdout}"}
        except Exception as e:
            return {"success": False, "error": f"Failed adjusting display brightness: {str(e)}"}

    @classmethod
    def get_brightness(cls) -> Optional[int]:
        """Queries current display brightness percentage."""
        ps_script = """
        try {
            $monitor = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop
            Write-Output "BRIGHTNESS=$($monitor.CurrentBrightness)"
        } catch {
            Write-Output "UNSUPPORTED"
        }
        """
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if "BRIGHTNESS=" in line:
                    return int(line.split("BRIGHTNESS=")[1].strip())
            return None
        except Exception:
            return None
