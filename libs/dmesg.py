import subprocess


def get_dmesg(bin_path='dmesg'):
    commandline = [bin_path]
    try:
        output = subprocess.check_output(commandline, stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError:
        print("Dmesg command error!")
        return []
    except OSError:
        print("Dmesg command not found?")
        return []
    else:
        if isinstance(output, bytes): output = output.decode("ascii")
        return parse_dmesg_output(output)

def parse_dmesg_output(output):
    result = []
    current_message = None
    lines = filter(None, output.split("\n"))
    for line in lines:
        if line.startswith("["):
            if current_message:
                #flush the current message
                result.append(current_message)
            #create dict
            current_message = {"message":None, "rel_timestamp_str":None}
            #first line with the timestamp
            ts, msg_start = line.split("]", 1)
            current_message["rel_timestamp_str"] = ts.strip('[').strip(" ")
            current_message["message"] = msg_start.strip()
        else:
            #multi-line message continues
            if line.strip():
                current_message["message"] += '\n{}'.format(line)
    if current_message:
        #flush the last message
        result.append(current_message)
    return result

def dmesg_output_was_truncated(msgs):
    """
        Checks if the dmesg output has been truncated from startup,
        returns ``True`` if so - ``False`` otherwise. For now, checks
        if there are any messages with "[    0.000000" timestamp string
        that start with "Booting Linux".
    """
    zero_ts_messages = [msg for msg in msgs if msg["rel_timestamp_str"] == "0.000000"]
    if not zero_ts_messages:
        return True
    return not any([msg["message"].startswith("Booting Linux") for msg in zero_ts_messages])



if __name__ == "__main__":
    print(get_dmesg()[:10])
    print(dmesg_output_was_truncated(get_dmesg()))
