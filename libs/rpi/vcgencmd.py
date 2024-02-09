import subprocess


"""
This module parses vcgencmd command output, as well as detects unprogrammed otp.
"""

def command(*args, **kwargs):
    bin_path = kwargs.get("bin_path", 'vcgencmd')
    commandline = [bin_path]
    commandline += args
    try:
        output = subprocess.check_output(commandline, stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError:
        print("vcgencmd command error!")
        return None
    except OSError:
        print("vcgencmd command not found?")
        return None
    else:
        if isinstance(output, bytes): output = output.decode("ascii")
        return output

def otp_dump(bin_path = None):
    kwargs = {}
    if bin_path: kwargs["bin_path"] = bin_path
    output = command("otp_dump", **kwargs)
    result = {}
    if output:
        lines = filter(None, output.split("\n"))
        for line in lines:
            if line.count(":") == 1:
                addr, value = line.split(":")
                if addr.isdigit() and value.isdigit():
                    result[int(addr)] = int(value, 16)
        return result
    else:
        raise ValueError("vcgencmd command problem")

def otp_problem_detected(otp_dict):
    return otp_dict[30] == 0

if __name__ == "__main__":
    print(otp_dump())
    print(otp_problem_detected(otp_dump()))
