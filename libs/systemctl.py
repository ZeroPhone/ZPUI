from zpui_lib.helpers import setup_logger
from pydbus import SystemBus

from operator import itemgetter

logger = setup_logger(__name__, "warning")

# See D-Bus documentation here:
#     https://www.freedesktop.org/wiki/Software/systemd/dbus/

bus = SystemBus()
systemd = bus.get(".systemd1")

def list_units(unit_filter_field = None, unit_filter_values = []):
    """
    This function lists units, optionally filtering them by a certain parameter.
    It returns a list of dictionaries, with following fields:

    * ``"name"``: Full unit name, in the "name.type" format - i.e. "zpui.service"
    * ``"basename"``: Unit name without unit type - i.e. "zpui"
    * ``"unit_type"``: Unit type - i.e. "service", "socket" or "target"
    * ``"description"``: Unit's human-readable description
    * ``"active"``: Whether the unit is now active - i.e. "active", "failed", "inactive"
    * ``"load"``: Whether the unit is now loaded - i.e. "loaded", "masked", "not found"
    * ``"sub"``: Type-specific unit state - i.e.  "running", "listening", "mounted"
    * ``"follower"``: A unit that is being followed in its state by this unit, if there is any, otherwise an empty string.
    * ``"unit_object_path"``: The unit object path
    * ``"job_queued"``: If there is a job queued for the job unit - the numeric job id, 0 otherwise
    * ``"job_object_path"``: The job object path
    * ``"job_type"``: The job type as string

    Arguments:

      * ``unit_filter_field``: a field which to filter the units by.
      * ``unit_filter_values``: a list of values for the given field that are acceptable
    """

    units = []

    unit_params = ["name", "description", "load", "active", "sub", "follower", "unit_object_path", "job_queued", "job_type", "job_object_path"]
    additional_params = ["basename", "unit_type"]

    if unit_filter_field and unit_filter_field not in unit_params+additional_params:
        logger.error("Set unit_filter_field '{}' not one of '{}'".format(unit_filter_field, available_unit_filter_fields))
        return False

    for unit in systemd.ListUnits():
        unit_dict = {}
        assert (len(unit) == len(unit_params)), "Can't unpack the unit list - wrong number of arguments!"
        for i, param in enumerate(unit_params):
            unit_dict[param] = unit[i]

        unit_dict["basename"], unit_dict["unit_type"] = unit_dict["name"].rsplit('.', 1)

        if unit_filter_field is None or unit_dict[unit_filter_field] in unit_filter_values:
            units.append(unit_dict)

    units = sorted(units, key=itemgetter('name'))

    return units


def action_unit(action, unit, mode="fail", en_dis_runtime=False, en_force=False):
    # See D-Bus documentation (linked above) for argument explanation
    job = False

    try:
        if action == "start":
            job = systemd.StartUnit(unit, mode)
        elif action == "stop":
            job = systemd.StopUnit(unit, mode)
        elif action == "restart":
            job = systemd.RestartUnit(unit, mode)
        elif action == "reload":
            job = systemd.ReloadUnit(unit, mode)
        elif action == "enable":
            job = systemd.EnableUnitFiles([unit], en_dis_runtime, en_force)
        elif action == "disable":
            job = systemd.DisableUnitFiles([unit], en_dis_runtime)
        elif action == "reload-or-restart":
            job = systemd.ReloadOrRestartUnit(unit, mode)
        else:
            raise ValueError("Unknown action '{}' attempted on unit '{}'".format(action, unit))
    except Exception as e:
        logger.exception("Exception while trying to run '{}' on unit '{}'".format(action, unit))
        raise

    return job

if __name__ == "__main__":
    units_loaded = list_units('load', ['loaded'])
    units_active = list_units('active', ['active'])
    units_sub    = list_units('sub', ['sub'])

    for unit in units_loaded:
        print(unit["name"])

    for unit in units_active:
        print(unit["name"])

    for unit in units_sub:
        print(unit["name"])
