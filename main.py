import time
from fetcher import OpenF1Fetcher
from model import compute_probabilities

SESSION_KEY = 1234
TOTAL_LAPS = 57

fetcher = OpenF1Fetcher(SESSION_KEY, TOTAL_LAPS)

def print_standing(state, probs):
    print("\n" + "="*50)
    print(f"LAP {state.current_lap}/{state.total_laps}")
    if state.safety_car_active:
        print("*** SAFETY CAR ***")
    print(f"{'PROB':<5} | {'DRIVER':<25} | {'POS':<8} | {'PACE':<6} | {'WIN%'}")
    print("-" * 50)

    drivers = [d for d in state.drivers.values() if d.position < 90]
    drivers.sort(key=lambda d: probs.get(d.driver_number, 0), reverse=True)
    
    for d in drivers:
        prob = probs.get(d.driver_number, 0)
        print(f"p{d.position:<4} {d.name:<25} {d.tyre_compound:<8} {d.tyre_age:<6}, {prob:.1f}%")
        
def main():
    session_key_input = input("Enter session key (try 9158 for Bahrain 2023): ")
    session_key = int(session_key_input) if session_key_input else 9158
    total_laps_input = input("Enter total laps (57 for Bahrain): ")
    total_laps = int(total_laps_input) if total_laps_input else 57
    
    local_fetcher = OpenF1Fetcher(session_key=session_key, total_laps=total_laps)
    print("starting ... press ctrl-c to quit")
    try:
        while True:
            state = local_fetcher.fetch()
            probs = compute_probabilities(state)
            print_standing(state, probs)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()