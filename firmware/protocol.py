"""Line protocol matching doc/api.md, plus RECOVER for hard safety unlock."""

import config


def _ok():
    return "OK"


def _err(code):
    return "ERROR " + code


def _value(v):
    if isinstance(v, float):
        return "VALUE %.1f" % v
    return "VALUE " + str(v)


class Protocol:
    def __init__(self, controller):
        self.ctl = controller

    def handle(self, line):
        line = (line or "").strip()
        if not line:
            return None
        cmd, _, param = line.partition(" ")
        cmd = cmd.upper().strip()
        param = param.strip()
        try:
            return self._dispatch(cmd, param)
        except Exception:
            return _err("INVALID_VALUE")

    def _dispatch(self, cmd, param):
        c = self.ctl

        if cmd == "PING":
            return _ok()

        if cmd == "GET_SYSTEM_INFO":
            state = "LOCKED" if c.safety.state != "OK" else ("BUSY" if c.busy else "READY")
            return "INFO FW=%s STATE=%s" % (config.FW_VERSION, state)

        if cmd == "GET_STATUS":
            fields = c.status_fields()
            body = " ".join("%s=%s" % (k, fields[k]) for k in fields)
            return "STATUS " + body

        if cmd == "GET_FAULT":
            return _value(c.safety.fault)

        if cmd == "GET_TARGET_TEMP":
            return _value(c.store.target_c)

        if cmd == "GET_TUB_TEMP":
            return _value(c.sensors.tub_c)

        if cmd == "GET_INLET_TEMP":
            return _value(c.sensors.inlet_c)

        if cmd == "SET_TARGET_TEMP":
            return _ok() if c.set_target(float(param)) else _err("INVALID_VALUE")

        if cmd == "SET_INLET_OFFSET":
            return _ok() if c.set_inlet_offset(float(param)) else _err("INVALID_VALUE")

        if cmd == "SET_REHEAT_HYST":
            return _ok() if c.set_reheat_hyst(float(param)) else _err("INVALID_VALUE")

        if cmd == "SET_TUB_CAL":
            return _ok() if c.set_tub_cal(float(param)) else _err("INVALID_VALUE")

        if cmd == "SET_MODE":
            return _ok() if c.set_mode(param) else _err("INVALID_VALUE")

        if cmd == "START_FLOW":
            result = c.start_flow()
            return _ok() if result == "OK" else _err(result)

        if cmd == "STOP_FLOW":
            return _ok() if c.stop_flow() == "OK" else _err("BUSY")

        if cmd == "SET_DRAIN":
            result = c.set_drain(param)
            return _ok() if result == "OK" else _err(result)

        if cmd == "SET_FROST_DELAY":
            return _ok() if c.set_frost_delay(float(param)) else _err("INVALID_VALUE")

        if cmd == "SET_FROST_ACTIVE":
            return _ok() if c.set_frost_active(param) else _err("INVALID_VALUE")

        if cmd == "SET_HEAT_CABLE":
            return _ok() if c.set_heat_cable(param) else _err("INVALID_VALUE")

        if cmd == "SET_AUX":
            on = param.upper() in ("ON", "1", "TRUE")
            off = param.upper() in ("OFF", "0", "FALSE")
            if not (on or off):
                return _err("INVALID_VALUE")
            c.set_aux(on)
            return _ok()

        if cmd == "CLEAR_FAULT":
            result = c.clear_fault()
            return _ok() if result == "OK" else _err(result)

        if cmd == "RECOVER":
            # Hard unlock path: cool mixer, then clear SAFETY LOCKED.
            return _ok() if c.recover() == "OK" else _err("BUSY")

        return _err("INVALID_CMD")
