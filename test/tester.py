from utils.to_xml.shows_to_xml import calculate_start_time, calculate_step_timing

# Test parameters
signature = "4/4"
start_bpm = 100
end_bpm = 190
num_bars = 16
speed = "1"
transition = "gradual"

# Test calculate_start_time
previous_time = 0
total_duration = calculate_start_time(previous_time, signature, end_bpm, num_bars, transition, start_bpm) - previous_time

# Test calculate_step_timing
step_timings, total_steps = calculate_step_timing(signature, start_bpm, end_bpm, num_bars, speed, transition)
sequence_duration = sum(step_timings)

print(f"Start time calculation: {total_duration}ms")
print(f"Step timing sum: {sequence_duration}ms")
