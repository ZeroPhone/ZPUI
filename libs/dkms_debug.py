import subprocess
import platform

def dkms_driver_is_installed(name, dkms_info=None):
    """ Parses output of "dkms status" to understand whether a driver is installed """
    uname = platform.uname()[2]
    dkms_info = dkms_info if dkms_info else get_dkms_status_info()
    for driver_info in dkms_info:
        if driver_info["name"] == name:
            if driver_info["uname"] == uname:
                if driver_info["status"] == "installed":
                    return True
    return False

def get_dkms_status_info():
    """
    Returns a list of dictionaries, each dict representing a DKMS driver info entry.

    Dict keys:

      * ``status``: "installed" or some other string

    Returns an empty list if "dkms status" command fails.
    """
    try:
        output = subprocess.check_output(["dkms", "status"])
    except subprocess.CalledProcessError:
        return []
    answer = []
    if isinstance(output, bytes): output = output.decode("ascii")
    lines = output.split('\n')
    lines = filter(None, lines)
    for line in lines:
        if ':' in line: #simple sanity check
            info, status = line.rsplit(':', 1)
            status = status.strip(' ')
            name, version, uname, arch = [el.strip(' ') for el in info.split(',')]
            answer.append({"status":status, "name":name, "version":version,
                           "uname":uname, "arch":arch })
    return answer

if __name__ == "__main__":
    info = get_dkms_status_info()
    print(info)
    print(dkms_driver_is_installed("esp8089", dkms_info=info))
