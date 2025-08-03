import time
import util as ut
from gpiozero import PWMOutputDevice
import curses # Import the curses library

# --- Configuration ---
# GPIO pins for L298N Speed Control (Enable Pins)
SPEED_PIN_A = 20  # ENA - Controls speed for motor 2
SPEED_PIN_B = 21  # ENB - Controls speed for motor 1

# --- Global Variables ---
speed_pin_a = None
speed_pin_b = None

# --- Main Functions ---

def set_speed(speed_value, stdscr):
    """
    Sets the motor speed and displays it on the screen.
    """
    if not (0.0 <= speed_value <= 1.0):
        stdscr.addstr(5, 0, "Speed value must be between 0.0 and 1.0")
        return

    if speed_pin_a and speed_pin_b:
        speed_pin_a.value = speed_value
        speed_pin_b.value = speed_value
        stdscr.addstr(5, 0, f"Speed set to {int(speed_value * 100)}%      ") # Add padding to clear old text
    else:
        stdscr.addstr(5, 0, f"Simulating speed set to {int(speed_value * 100)}%")
    stdscr.refresh()


def main(stdscr):
    """Main function to be run by curses."""
    global speed_pin_a, speed_pin_b

    # --- Curses Setup ---
    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(True) # Make getch() non-blocking
    stdscr.timeout(100)  # Set a timeout for getch() in milliseconds

    # --- GPIO Initialization ---
    try:
        speed_pin_a = PWMOutputDevice(SPEED_PIN_A, frequency=100)
        speed_pin_b = PWMOutputDevice(SPEED_PIN_B, frequency=100)
        ut.init_gpio()
    except Exception as e:
        stdscr.addstr(10, 0, f"GPIO Warning: {e}")
        stdscr.refresh()
        time.sleep(3)


    # --- Print Instructions ---
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Robot Control (curses) ---")
    stdscr.addstr(1, 0, "W: Forward | S: Backward | A: Left | D: Right")
    stdscr.addstr(2, 0, "1-4: Set speed (25%, 50%, 75%, 100%)")
    stdscr.addstr(3, 0, "Q: Quit")
    stdscr.addstr(4, 0, "--------------------------------")
    stdscr.refresh()

    # Set a default starting speed
    current_speed = 0.5
    set_speed(current_speed, stdscr)

    # --- Main Loop ---
    while True:
        # Get user input, returns -1 if no key is pressed within the timeout
        key = stdscr.getch()

        action_taken = False
        if key == ord('w'):
            stdscr.addstr(6, 0, "Status: Moving Forward ")
            ut.forward()
            action_taken = True
        elif key == ord('s'):
            stdscr.addstr(6, 0, "Status: Moving Backward")
            ut.back()
            action_taken = True
        elif key == ord('a'):
            stdscr.addstr(6, 0, "Status: Turning Left   ")
            ut.left()
            action_taken = True
        elif key == ord('d'):
            stdscr.addstr(6, 0, "Status: Turning Right  ")
            ut.right()
            action_taken = True
        elif key in [ord('1'), ord('2'), ord('3'), ord('4')]:
            current_speed = int(chr(key)) * 0.25
            set_speed(current_speed, stdscr)
        elif key == ord('q'):
            stdscr.addstr(6, 0, "Status: Quitting...    ")
            stdscr.refresh()
            break # Exit the loop

        # If no key was pressed in this cycle, stop the motors
        if key == -1:
            stdscr.addstr(6, 0, "Status: Stopped        ")
            ut.stop()

        stdscr.refresh()

def cleanup():
    """Cleans up GPIO resources properly."""
    print("\nCleaning up GPIO resources...")
    ut.stop()
    if speed_pin_a:
        speed_pin_a.close()
    if speed_pin_b:
        speed_pin_b.close()
    if hasattr(ut, 'cleanup_gpio'):
        ut.cleanup_gpio()
    print("Cleanup complete.")

if __name__ == "__main__":
    try:
        # curses.wrapper handles all the setup and teardown of the screen
        curses.wrapper(main)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # This will run after the program exits to ensure motors are off
        cleanup()
