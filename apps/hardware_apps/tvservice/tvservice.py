import json
from subprocess import check_output, CalledProcessError
from time import sleep
from helpers import setup_logger
logger = setup_logger(__name__, "info")
"""
#Not yet implemented:
  -t, --ntsc                        Use NTSC frequency for HDMI mode (e.g. 59.94Hz rather than 60Hz)
  -c, --sdtvon="MODE ASPECT"        Power on SDTV with MODE (PAL or NTSC) and ASPECT (4:3 14:9 or 16:9)
  -M, --monitor                     Monitor HDMI events
  -a, --audio                       Get supported audio information
  -d, --dumpedid <filename>         Dump EDID information to file
"""

def tvservice_command(*command):
    try:
        output = check_output(['tvservice'] + list(command))
    except CalledProcessError as e:
        raise
    else:
        if isinstance(output, bytes): output = output.decode("ascii")
        return output

def get_modes(group):
    """-m, --modes=GROUP                 Get supported modes for GROUP (CEA, DMT)"""
    output = tvservice_command("-j", "-m", group)
    modes = json.loads(output)
    return modes

def get_name():
    """-n, --name                        Print the device ID from EDID"""
    output = tvservice_command("-n")
    name = output.strip('\n').split('=', 1)[1].strip(' ')
    return name

def set_mode(group, mode, drive):
    """-e, --explicit="GROUP MODE DRIVE" Power on HDMI with explicit GROUP (CEA, DMT, CEA_3D_SBS, CEA_3D_TB, CEA_3D_FP, CEA_3D_FS), MODE (see --modes) and DRIVE (HDMI, DVI)"""
    if type(mode) == int: mode = str(mode)
    output = tvservice_command("-e", "{} {} {}".format(group, mode, drive))

def status():
    """-s, --status                      Get HDMI status"""
    output = tvservice_command("-s") #See example outputs at the bottom
    output = output.strip('\n').strip(' ')
    #First, we get the state flags and then parse everything according to which flags are set (since tvservice -s output is a little flag-specific)
    state = output.split('[')[0]
    state_value_str = state.split(' ')[1].strip(' ')
    flags = get_state_flags(state_value_str)
    hdmi_port_active = "VC_HDMI_DVI" in flags or "VC_HDMI_HDMI" in flags
    tv_out_active = "VC_SDTV_NTSC" in flags or "VC_SDTV_PAL" in flags
    if not hdmi_port_active and not tv_out_active: #Neither HDMI nor TV-out active
        result = {"state":state_value_str, "flags":flags, "mode":"NONE"}
        return result
    #Now parsing things common to both HDMI and TV modes
    state_str, resolution, scan_type = [part.strip(' ') for part in output.split(',')]
    state_params = state_str.split('[')[1].strip(']')
    resolution, refresh_rate = [part.strip(' ') for part in resolution.split('@')]
    x, y = resolution.split('x')
    result = {"state":state_value_str, "flags":flags, "resolution":(x, y), "scan_type":scan_type, "refresh_rate": refresh_rate}
    #Now going through mode-specific parameters
    if hdmi_port_active:
       result["mode"] = "HDMI"
       drive, group, mode_str, color_scheme, something, ratio = state_params.split(" ", 5)
       result["ratio"] = ratio
       mode = mode_str.strip("()")
       result["gmd"] = (group, mode, drive)
    elif tv_out_active:
       result["mode"] = "TV"
       mode, ratio = state_params.split(" ", 2)
       result["tv_mode"] = mode
       result["ratio"] = ratio
    else:
       logger.warning("Unexpected tvservice -s output: {}".format(output))
       result["mode"] = "UNKNOWN"
    return result

def display_off():
    """-o, --off                         Power off the display"""
    tvservice_command("-o")
    
def display_on():
    """-p, --preferred                   Power on HDMI with preferred settings"""
    tvservice_command("-p")
    
def get_state_flags(state_str):
    state_flags = {
    "VC_HDMI_UNPLUGGED"          : 0,  #HDMI cable is detached
    "VC_HDMI_ATTACHED"           : 1,  #HDMI cable is attached but not powered on
    "VC_HDMI_DVI"                : 2,  #HDMI is on but in DVI mode (no audio)
    "VC_HDMI_HDMI"               : 3,  #HDMI is on and HDMI mode is active
    "VC_HDMI_HDCP_UNAUTH"        : 4,  #HDCP authentication is broken (e.g. Ri mismatched) or not active
    "VC_HDMI_HDCP_AUTH"          : 5,  #HDCP is active
    "VC_HDMI_HDCP_KEY_DOWNLOAD"  : 6,  #HDCP key download successful/fail
    "VC_HDMI_HDCP_SRM_DOWNLOAD"  : 7,  #HDCP revocation list download successful/fail
    "VC_HDMI_CHANGING_MODE"      : 8,  #HDMI is starting to change mode, clock has not yet been set
    "VC_SDTV_UNPLUGGED"          : 16, #SDTV cable unplugged, subject to platform support
    "VC_SDTV_ATTACHED"           : 17, #SDTV cable is plugged in
    "VC_SDTV_NTSC"               : 18, #SDTV is in NTSC mode
    "VC_SDTV_PAL"                : 19, #SDTV is in PAL mode
    "VC_SDTV_CP_INACTIVE"        : 20, #Copy protection disabled
    "VC_SDTV_CP_ACTIVE"          : 21  #Copy protection enabled
    }
    state_value = int(state_str, 0)
    flags_set = []
    for flag_name in state_flags:
        if state_value & 1 << state_flags[flag_name]:
            flags_set.append(flag_name)
    return flags_set


if __name__ == "__main__":
    print(get_modes("DMT"))
    print(status())
    print(get_name())
    #display_off()
    #sleep(5)
    #display_on()


"""

#Tvservice status strings & flags:

state 0x120006 [DVI DMT (35) RGB full 5:4], 1280x1024 @ 60.00Hz, progressive
['VC_HDMI_ATTACHED', 'VC_SDTV_ATTACHED', 'VC_HDMI_DVI', 'VC_SDTV_CP_INACTIVE']

state 0x120006 [DVI DMT (35) RGB full 5:4], 1280x1024 @ 60.00Hz, progressive
['VC_HDMI_ATTACHED', 'VC_SDTV_ATTACHED', 'VC_HDMI_DVI', 'VC_SDTV_CP_INACTIVE']

state 0x120002 [TV is off]
['VC_HDMI_ATTACHED', 'VC_SDTV_ATTACHED', 'VC_SDTV_CP_INACTIVE']

state 0x40001 [NTSC 4:3], 720x480 @ 60.00Hz, interlaced
['VC_SDTV_NTSC', 'VC_HDMI_UNPLUGGED']

state 0x40002 [NTSC 4:3], 720x480 @ 60.00Hz, interlaced
['VC_HDMI_ATTACHED', 'VC_SDTV_NTSC']

state 0x120006 [DVI DMT (35) RGB full 5:4], 1280x1024 @ 60.00Hz, progressive
['VC_HDMI_ATTACHED', 'VC_SDTV_ATTACHED', 'VC_HDMI_DVI', 'VC_SDTV_CP_INACTIVE']

state 0x120006 [DVI DMT (35) RGB full 5:4], 1280x1024 @ 60.00Hz, progressive
['VC_HDMI_ATTACHED', 'VC_SDTV_ATTACHED', 'VC_HDMI_DVI', 'VC_SDTV_CP_INACTIVE']

state 0x120005 [DVI DMT (35) RGB full 5:4], 1280x1024 @ 60.00Hz, progressive
['VC_SDTV_ATTACHED', 'VC_HDMI_DVI', 'VC_HDMI_UNPLUGGED', 'VC_SDTV_CP_INACTIVE']


"""
