from fetcher import RaceState, DriverState, tyre_life, tyre_pace 

WEIGHTS = {
    "position": 0.35,   
    "gap": 0.25,
    "tyre_pace": 0.10,
    "tyre_life": 0.15,
    "pit_strategy": 0.08,
    "lap_delta": 0.07,
}

SC_COMPRESSION_FACTOR = 0.4

def compute_probabilities(state: RaceState) -> dict[int, float]:

    drivers = [d for d in state.drivers.values() if d.position < 90] 
    if not drivers:
        return {}

    raw_scores: dict[int, float] = {}
    for driver in drivers:
        raw_scores[driver.driver_number] = _score_driver(driver, state)

    if state.safety_car_active or state.virtual_safety_car_active:
        raw_scores = _apply_safety_car(raw_scores, state)
        
    total = sum(raw_scores.values())
    if total == 0:
        equal = 100/len(drivers)
        return {d.driver_number: equal for d in drivers}
    
    return {
        num: round((score / total) * 100, 1)
        for num, score in raw_scores.items()
    }

#-----------scoring Function ----------------
def _score_driver(driver: DriverState, state: RaceState) -> float:
    num_drivers = len([d for d in state.drivers.values() if d.position < 90])
    laps_done = state.current_lap
    total_laps = state.total_laps
    race_progress = laps_done / total_laps if total_laps > 0 else 0.5

    scores = {
        "position":  _position_score(driver.position, num_drivers),
        "gap":       _gap_score(driver.gap_to_leader),
        "tyre_pace": _tyre_pace_score(driver.tyre_compound),
        "tyre_life": _tyre_life_score(driver.tyre_age, driver.tyre_compound),
        "pit_strategy": _pit_strategy_score(driver, state),
        "lap_delta": _lap_delta_score(driver.lap_delta),
    }
    
    weights = WEIGHTS.copy()
    if race_progress > 0.75:
        weights["position"] = min(0.50, weights["position"] + 0.08)
        weights["gap"] = min(0.35, weights["gap"] + 0.06)
        weights["pit_strategy"] = max(0.02, weights["pit_strategy"] - 0.04)
        weights["tyre_pace"] = max(0.04, weights["tyre_pace"] - 0.05)
        weights["tyre_life"] = max(0.05, weights["tyre_life"] - 0.05)
        
    total_weight = sum(weights.values())
    final_score = sum(scores[k] * weights[k] for k in scores) / total_weight
    return max(final_score, 0.001)

def _position_score(position: int, num_drivers: int) -> float:
    if num_drivers <= 1:
        return 1.0
    normalised = 1 - ((position - 1) / (num_drivers - 1))
    return normalised ** 1.5

def _gap_score(gap_seconds: float) -> float:
    import math 
    return math.exp(-gap_seconds / 15.0)

def _tyre_pace_score(compound: str) -> float:
    pace = tyre_pace.get(compound.upper(), 0.0)
    max_pace = max(tyre_pace.values())
    if max_pace == 0:
        return 0.5
    return 0.5 + (pace / max_pace) * 0.5

def _tyre_life_score(age: int, compound: str) -> float:
    max_age = tyre_life.get(compound.upper(), 35)
    if max_age == 0:
        return 0.5
    
    remaining_fraction = 1 - (age / max_age)
    if remaining_fraction <= 0:
        return 0.05
    elif remaining_fraction <= 0.2:
        return remaining_fraction * 0.5
    else:
        return remaining_fraction

def _pit_strategy_score(driver: DriverState, state: RaceState) -> float:
    
    race_progress = state.current_lap / state.total_laps if state.total_laps > 0 else 0.5
    max_age = tyre_life.get(driver.tyre_compound, 35)
    tyre_fraction = 1 - (driver.tyre_age / max_age if max_age > 0 else 0.5)

    if driver.pit_count >= 1:
        return 0.6

    if tyre_fraction < 0.15:
        return 0.1
    
    if race_progress > 0.6 and driver.tyre_compound in ("MEDIUM", "HARD"):
        return 0.75
    
    return 0.5

def _lap_delta_score(delta: float) -> float:

    clamed = max(-1.5, min(1.5, delta))
    return (clamed + 1.5) / 3.0

def _apply_safety_car(scores: dict[int, float], state: RaceState) -> dict[int, float]:

    adjusted = {}
    drivers = {d.driver_number: d for d in state.drivers.values()}   
   
    for num, score in scores.items():
        driver = drivers.get(num)
        if driver is None:
            adjusted[num] = score
            continue
    
        num_drivers = len(scores)
        relative_position = (driver.position - 1) / max(num_drivers - 1, 1)
        sc_boost = relative_position * SC_COMPRESSION_FACTOR
     
        # Blend: compress towards equal probability under SC
        equal_share = 1.0 / num_drivers
        adjusted[num] = score * (1 - SC_COMPRESSION_FACTOR) + (equal_share + sc_boost * score) * SC_COMPRESSION_FACTOR
 
    return adjusted

def explain_driver(driver: DriverState, state: RaceState) -> dict:
    num_drivers = len([d for d in state.drivers.values() if d.position < 90])
    return {
        "position_score": round(_position_score(driver.position, num_drivers), 3),
        "gap_score": round(_gap_score(driver.gap_to_leader), 3),
        "tyre_pace_score": round(_tyre_pace_score(driver.tyre_compound), 3),
        "tyre_life_score": round(_tyre_life_score(driver.tyre_age, driver.tyre_compound), 3),
        "pit_strategy_score": round(_pit_strategy_score(driver, state), 3),
        "lap_delta_score": round(_lap_delta_score(driver.lap_delta), 3),
    }
