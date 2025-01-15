from zpui_lib.helpers import ProHelper, setup_logger
from time import sleep

logger = setup_logger(__name__, "debug")

def passwd(username, password):
    # return a list of two values: 1 - True/False (success/likely failure)
    # 2 - list of all unexpected output
    ph = None
    status = ["unknown"] # hack, explained below
    def process_output(output):
        logger.debug("debug: calling process_output with {}".format(repr(output)))
        if output.strip().startswith("Enter new UNIX password:"):
            status[0] = "enter"
        elif output.strip().startswith("Retype new UNIX password:"):
            status[0] = "repeat"
        elif output.strip().startswith("passwd: password updated successfully"):
            status[0] = "success"
        else:
            # Unexpected output, let's append it to status and stop the process
            status.append(output)
            ph.kill_process()
        logger.debug("current status: {}".format(status[0]))
    ph = ProHelper(["passwd", username], output_callback=process_output)
    ph.run()
    while ph.is_ongoing():
        ph.poll() # go through output and call process_output on it
        if status[0] in ["enter", "repeat"]:
            ph.write(password+'\n')
            status[0] = "waiting" # so that we don't send the password more than necessary
        elif status[0] == "success":
            pass # By this time, we've probably finished, next cycle of "while" will not happen
        sleep(0.1)
    ph.poll() # Process leftover output so that we can check for success/failure
    # return a list of two values: 1 - True/False (success/likely failure)
    # 2 - list of all unexpected output
    return [True if status[0] == "success" else False, status[1:]]
