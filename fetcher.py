from dataclasses import dataclass, field
import requests
import time
from typing import Optional

@dataclass
class DriverState:
    driver_number: int
    name: str
    team: str
    team_color: str
    position: int = 99
    gap_to_leader: float = 999.0
    tyre_compound: str = "UNKNOWN"
    tyre_age: int = 0
    pit_count: int = 0
    stint_number: int = 1

    last_lap_time: Optional[float] = None
    avg_lap_time: Optional[float] = None
    lap_delta: float = 0.0

@dataclass
class RaceState:
    session_key: int
    total_laps: int
    current_lap: int = 0
    laps_remaining: int = 0
    safety_car_active: bool = False
    virtual_safety_car_active: bool = False
    red_flag: bool = False
    drivers: dict[int, DriverState] = field(default_factory=dict)

tyre_life = {
    "SOFT": 25,
    "MEDIUM": 38,
    "HARD": 55,
    "INTERMEDIATE": 30,
    "WET": 40
}
tyre_pace = {
    "SOFT": 0.8,
    "MEDIUM": 0.4,
    "HARD": 0.0,
    "INTERMEDIATE": 0.0,    
    "WET": 0.0
}       

Base_URL = "https://api.openf1.org/v1"

class OpenF1Fetcher:
    def __init__(self, session_key: int, total_laps: int):
        self.session_key = session_key
        self.total_laps = total_laps
        self._state = None
        self._lap_history = {}
    
    def _get(self, endpoint: str, params: dict) -> list:
        params["session_key"] = self.session_key
        try:
            r = requests.get(f"{Base_URL}/{endpoint}", params=params, timeout=5)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return []

    def fetch(self) -> RaceState:
        if self._state is None:
            self._state = self._init_state()
        self._update_positions()
        self._update_stints()
        self._update_laps()
        self._update_pits()
        self._update_race_control()
        return self._state
    
    def _init_state(self) -> RaceState:
        state = RaceState(
            session_key=self.session_key,
            total_laps=self.total_laps,
        )
        driver_data = self._get("drivers", {})
        for d in driver_data:
            num = d.get("driver_number")
            if num:
                state.drivers[num] = DriverState(
                    driver_number=num,
                    name=d.get("full_name", f"Driver {num}"),
                    team=d.get("team_name", "Unknown"),
                    team_color=d.get("team_colour", "FFFFFF"),
                )
        print(f"Loaded {len(state.drivers)} drivers")
        return state
    
    def _update_positions(self):
        position_data = self._get("position", {})
        latest = {}
        for p in position_data:
            driver_num = p.get("driver_number")
            if driver_num:
                latest[driver_num] = p          

        for num, p in latest.items():
            if num in self._state.drivers:
                self._state.drivers[num].position = p.get("position", 99)

    def _update_stints(self):
        stint_data = self._get("stints", {})
        latest = {}
        for row in stint_data:
            num = row.get("driver_number")
            if num:
                current = latest.get(num)
                if current is None or row.get("stint_number") > current.get("stint_number", 0):
                    latest[num] = row

        for num, row in latest.items():
            if num in self._state.drivers:
                driver = self._state.drivers[num]
                driver.tyre_compound = row.get("compound", "UNKNOWN").upper()
                driver.stint_number = row.get("stint_number", 1)
                lap_start = row.get("lap_start", 0) or 0
                age_at_start = row.get("tyre_age_at_start", 0) or 0
                driver.tyre_age = self._state.current_lap - lap_start + age_at_start
        ''' 

        Note the `or 0` after `.get()` — the API sometimes returns `None` for these fields and `None - 20` would crash. `None or 0` gives you `0` safely.

        '''

    def _update_laps(self):
        data = self._get("laps", {})
        by_driver = {}
        max_race_lap = 0
        for row in data:
            num = row.get("driver_number")
            if num:
                by_driver.setdefault(num, []).append(row)
            lap_num = row.get("lap_number", 0)
            if lap_num > max_race_lap:
                max_race_lap = lap_num
                
        if max_race_lap > self._state.current_lap:
            self._state.current_lap = max_race_lap
            self._state.laps_remaining = max(0, self.total_laps - max_race_lap)

        for num, laps in by_driver.items():
            if num not in self._state.drivers:
                continue
            driver = self._state.drivers[num]
            laps.sort(key=lambda x: x.get("lap_number", 0))

            valid = [
                l["lap_duration"] for l in laps 
                if l.get("lap_duration") and not l.get("is_pit_out_lap")  
            ]
            if valid:
                driver.last_lap_time = valid[-1]
                driver.avg_lap_time = sum(valid) / len(valid)
                if len(valid) > 2:
                    driver.lap_delta = valid[-2] - valid[-1]

    def _update_pits(self):
        pit_data = self._get("pit", {})
        pit_count = {}
        for row in pit_data:
            num = row.get("driver_number")
            if num:
                pit_count[num] = pit_count.get(num, 0) + 1

        for num, count in pit_count.items():
            if num in self._state.drivers:
                self._state.drivers[num].pit_count = count

    def _update_race_control(self):
        control_data = self._get("race_control", {"category": "SafetyCar"})
        if not control_data:
            return
        control_data.sort(key=lambda x: x.get("date", 0))
        latest = control_data[-1]
        msg = latest.get("message", "").upper()
        self._state.safety_car_active = "SAFETY CAR" in msg and "DEPLOYED" in msg
        self._state.virtual_safety_car_active = "VIRTUAL" in msg and "DEPLOYED" in msg
        self._state.red_flag = latest.get("flag", "").upper() == "RED"

    def _update_gaps(self):
        """
        OpenF1 doesn't have a direct gap endpoint, so we approximate:
        gap = (position - 1) * estimated seconds per position.
        In a real integration you'd use timing data to get exact gaps.
        """
        for num, driver in self._state.drivers.items():
            if driver.position == 1:
                driver.gap_to_leader = 0.0
            else:
                # Rough approximation: each position ~ 2s gap
                # Replace this with real interval data when available
                driver.gap_to_leader = (driver.position - 1) * 2.0       
