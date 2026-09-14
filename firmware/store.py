"""Persistent settings and learned fill statistics."""

import json

import config


class Store:
    def __init__(self, path=None):
        self.path = path or config.STORE_PATH
        self.target_c = config.DEFAULT_TARGET_C
        self.inlet_offset_c = config.DEFAULT_INLET_OFFSET_C
        self.reheat_hyst_c = config.DEFAULT_REHEAT_HYST_C
        self.tub_cal_c = config.DEFAULT_TUB_CAL_C
        self.frost_delay_s = config.DEFAULT_FROST_DELAY_S
        self.frost_active = 0
        self.heat_cable = "AUTO"
        self.aux_duration_s = config.AUX_DURATION_DEFAULT_S
        self.mode = "AUTO"
        self.fill_times = []  # recent fill durations (seconds)
        self.learned_drop_c = config.DEFAULT_INLET_OFFSET_C
        self.load()

    def load(self):
        try:
            with open(self.path, "r") as fh:
                data = json.load(fh)
        except Exception:
            return
        self.target_c = float(data.get("target_c", self.target_c))
        self.inlet_offset_c = float(data.get("inlet_offset_c", self.inlet_offset_c))
        self.reheat_hyst_c = float(data.get("reheat_hyst_c", self.reheat_hyst_c))
        self.tub_cal_c = float(data.get("tub_cal_c", self.tub_cal_c))
        self.frost_delay_s = float(data.get("frost_delay_s", self.frost_delay_s))
        self.frost_active = int(data.get("frost_active", self.frost_active))
        self.heat_cable = str(data.get("heat_cable", self.heat_cable))
        self.aux_duration_s = float(data.get("aux_duration_s", self.aux_duration_s))
        self.mode = str(data.get("mode", self.mode))
        fills = data.get("fills_times") or data.get("fills_s") or data.get("fill_s") or []
        self.fill_times = [float(x) for x in fills][-config.FILL_HISTORY :]
        self.learned_drop_c = float(data.get("learned_drop_c", self.learned_drop_c))

    def save(self):
        data = {
            "target_c": self.target_c,
            "inlet_offset_c": self.inlet_offset_c,
            "reheat_hyst_c": self.reheat_hyst_c,
            "tub_cal_c": self.tub_cal_c,
            "frost_delay_s": self.frost_delay_s,
            "frost_active": self.frost_active,
            "heat_cable": self.heat_cable,
            "aux_duration_s": self.aux_duration_s,
            "mode": self.mode,
            "fills_times": self.fill_times[-config.FILL_HISTORY :],
            "learned_drop_c": self.learned_drop_c,
        }
        try:
            with open(self.path, "w") as fh:
                json.dump(data, fh)
        except Exception:
            pass

    def record_fill(self, duration_s, inlet_c, tub_c):
        if duration_s <= 0:
            return
        self.fill_times.append(float(duration_s))
        self.fill_times = self.fill_times[-config.FILL_HISTORY :]
        drop = max(0.0, float(inlet_c) - float(tub_c))
        self.learned_drop_c = (self.learned_drop_c * 0.7) + (drop * 0.3)
        self.save()

    def avg_fill_s(self):
        if not self.fill_times:
            return float(config.FILL_ETA_DEFAULT_S)
        return sum(self.fill_times) / len(self.fill_times)

    def effective_inlet_setpoint(self):
        offset = max(self.inlet_offset_c, min(5.0, self.learned_drop_c))
        return self.target_c + offset
