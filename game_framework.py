"""Minimal mode switching + fixed references; structurally close to course examples."""
from time import perf_counter
from pico2d import open_canvas, close_canvas, delay

running = False
current_mode = None
frame_time = 1.0 / 60.0


def change_mode(next_mode):
    global current_mode
    if current_mode:
        current_mode.finish()
    current_mode = next_mode
    current_mode.init()


def quit_game():
    global running
    running = False


def run(start_mode):
    global running, current_mode, frame_time
    open_canvas(960, 640)
    running = True
    change_mode(start_mode)
    last_time = perf_counter()
    try:
        while running:
            now = perf_counter()
            frame_time = min(0.05, max(0.001, now - last_time))
            last_time = now
            current_mode.handle_events()
            if not running:
                break
            current_mode.update()
            current_mode.draw()
            # Reasonable CPU use; actual delta remains time-based.
            delay(0.01)
    finally:
        if current_mode:
            current_mode.finish()
        close_canvas()
