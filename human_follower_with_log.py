import common as cm
import cv2
import numpy as np
from PIL import Image
import time
from threading import Thread
from gpiozero import LED
import csv
import os
import psutil

# --- Performance Logging Setup ---
CSV_FILE_PATH = 'latency_log.csv'
CSV_HEADER = ['frame', 'capture_latency', 'preprocess_latency', 'inference_latency', 'logic_latency', 'total_latency', 'fps', 'memory_mb']

# Video path
video_path = '/home/adarsh/projects/code_files/test_folder/sample.mp4'
cap = cv2.VideoCapture(video_path)
threshold = 0.2
top_k = 5
edgetpu = 0

# Get video properties
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
# Define the codec and create VideoWriter object
output_video = "output_with_stats.mp4"
# Use a valid FPS value, e.g., 20, if cap.get(cv2.CAP_PROP_FPS) returns 0
fps_prop = cap.get(cv2.CAP_PROP_FPS)
if fps_prop == 0:
    fps_prop = 20.0
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, fps_prop, (frame_width, frame_height))


model_dir = '/home/adarsh/projects/code_files/human_following/model'
model_edgetpu = 'mobilenet_ssd_v2_coco_quant_postprocess.tflite'
lbl = 'coco_labels.txt'

tolerance = 0.1
x_deviation = 0
y_max = 0
arr_track_data=[0,0,0,0,0,0]

object_to_track = 'person'

# Initialize motor speed using gpiozero
speed_pin20 = LED(20)
speed_pin21 = LED(21)

val = 1
if val:
    speed_pin20.on()
    speed_pin21.on()
else:
    speed_pin20.off()
    speed_pin21.off()

print("Speed set to:", val)

# --- Process Info for Memory Logging ---
process = psutil.Process(os.getpid())
def log_memory_usage():
    # Return memory usage in MB
    return process.memory_info().rss / (1024 * 1024)

def track_object(objs, labels):
    """
    Track the specified object and calculate its deviation from the center.
    """
    global x_deviation, y_max, tolerance,arr_track_data

    if len(objs) == 0:
        #print("No objects to track")
        arr_track_data=[0,0,0,0,0,0]
        #stop_motors()
        return

    flag = False
    for obj in objs:
        lbl = labels.get(obj.id, obj.id)
        if lbl == object_to_track:
            x_min, y_min, x_max, y_max = list(obj.bbox)
            flag = True
            break

    if not flag:
        #print("Selected object not present")
        return

    x_diff = x_max - x_min
    y_diff = y_max - y_min

    obj_x_center = x_min + (x_diff / 2)
    obj_x_center = round(obj_x_center, 3)

    obj_y_center = y_min + (y_diff / 2)
    obj_y_center = round(obj_y_center, 3)

    x_deviation = round(0.5 - obj_x_center, 3)
    y_max = round(y_max, 3)

    #print("{", x_deviation, y_max, "}")

    thread = Thread(target=move_robot)
    thread.start()

    arr_track_data[0]=obj_x_center
    arr_track_data[1]=obj_y_center
    arr_track_data[2]=x_deviation
    arr_track_data[3]=y_max

def move_robot():
    """
    Move the robot based on the calculated deviation.
    """
    global x_deviation, y_max, tolerance,arr_track_data

    y = 1 - y_max

    if abs(x_deviation) < tolerance:
        delay=0
        if y < 0.1:
            cmd="Stop"
            #stop_motors()
        else:
            cmd="forward"
            #move_forward()
    else:
        if x_deviation >= tolerance:
            cmd="Move Left"
            delay = get_delay(x_deviation)
            #turn_left(delay)
        elif x_deviation <= -tolerance:
            cmd="Move Right"
            delay = get_delay(x_deviation)
            #turn_right(delay)

    arr_track_data[4]=cmd
    arr_track_data[5]=delay

def get_delay(deviation):
    """
    Calculate delay based on deviation to control turning duration.
    """
    deviation = abs(deviation)
    if deviation >= 0.4:
        return 0.080
    elif 0.35 <= deviation < 0.4:
        return 0.060
    elif 0.20 <= deviation < 0.35:
        return 0.050
    else:
        return 0.040

def move_forward():
    speed_pin20.on()
    speed_pin21.on()

def turn_left(delay):
    speed_pin20.off()
    speed_pin21.on()
    time.sleep(delay)
    stop_motors()

def turn_right(delay):
    speed_pin20.on()
    speed_pin21.off()
    time.sleep(delay)
    stop_motors()

def stop_motors():
    speed_pin20.off()
    speed_pin21.off()


def main():
    """
    Main function to load model, process video, track object, and log performance.
    """
    interpreter, labels = cm.load_model(model_dir, model_edgetpu, lbl, edgetpu)
    
    frame_count = 0
    
    # Open CSV file and write header
    with open(CSV_FILE_PATH, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(CSV_HEADER)

        print(f"Starting performance logging to {CSV_FILE_PATH}...")
        print("Running in headless mode. Press Ctrl+C to stop.")
        
        try:
            while True:
                start_total_time = time.time()
                frame_count += 1
                
                # 1. Frame Capture Latency
                start_capture = time.time()
                ret, frame = cap.read()
                if not ret:
                    break
                capture_latency = time.time() - start_capture
    
                # 2. Preprocessing Latency
                start_preprocess = time.time()
                cv2_im = cv2.flip(frame, -1)
                cv2_im_rgb = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
                pil_im = Image.fromarray(cv2_im_rgb)
                preprocess_latency = time.time() - start_preprocess
    
                # 3. Inference Latency
                start_inference = time.time()
                cm.set_input(interpreter, pil_im)
                interpreter.invoke()
                objs = cm.get_output(interpreter, score_threshold=threshold, top_k=top_k)
                inference_latency = time.time() - start_inference
    
                # 4. Tracking Logic Latency
                start_logic = time.time()
                track_object(objs, labels)
                logic_latency = time.time() - start_logic
                
                # --- Performance Calculation ---
                total_latency = time.time() - start_total_time
                fps = 1.0 / total_latency if total_latency > 0 else 0
                current_memory_mb = log_memory_usage()
    
                # --- Logging to CSV ---
                log_data = [
                    frame_count,
                    f"{capture_latency:.4f}",
                    f"{preprocess_latency:.4f}",
                    f"{inference_latency:.4f}",
                    f"{logic_latency:.4f}",
                    f"{total_latency:.4f}",
                    f"{fps:.2f}",
                    f"{current_memory_mb:.2f}"
                ]
                writer.writerow(log_data)
                
                # --- Video Write (still saves the video with overlays) ---
                perf_data = {
                    'capture': capture_latency * 1000,
                    'inference': inference_latency * 1000,
                    'logic': logic_latency * 1000,
                    'fps': fps
                }
                
                cv2_im = append_text_img1(cv2_im, objs, labels, perf_data, arr_track_data)
                out.write(cv2_im)
                
                # --- GUI Display (DISABLED FOR HEADLESS OPERATION) ---
                # The following lines are commented out to prevent the display error.
                # cv2.imshow('Human Follower - Press Q to Quit', cv2_im)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     print("Stopping...")
                #     break
        except KeyboardInterrupt:
            print("\nStopping script with Ctrl+C.")

    print(f"Logging complete. Data saved to {CSV_FILE_PATH}.")
    cap.release()
    out.release()
    # cv2.destroyAllWindows() # Also comment out this line

def append_text_img1(cv2_im, objs, labels, perf_data, arr_track_data):
    height, width, channels = cv2_im.shape
    font=cv2.FONT_HERSHEY_SIMPLEX
    
    global tolerance
    
    cv2.rectangle(cv2_im, (0,0), (width, 24), (0,0,0), -1)
   
    cam=round(perf_data['capture'], 0)
    inference=round(perf_data['inference'], 0)
    other=round(perf_data['logic'], 0)
    text_dur = f"Cam: {cam}ms | Inf: {inference}ms | Logic: {other}ms"
    cv2.putText(cv2_im, text_dur, (10, 16),font, 0.4, (255, 255, 255), 1)
    
    fps=round(perf_data['fps'],1)
    text1 = f'FPS: {fps}'
    cv2.putText(cv2_im, text1, (width - 100, 18),font, 0.6, (150, 150, 255), 2)
   
    # ... (rest of your drawing code remains the same)
    #draw black rectangle at bottom
    cv2_im = cv2.rectangle(cv2_im, (0,height-24), (width, height), (0,0,0), -1)
    
    #write deviations and tolerance
    str_tol='Tol : {}'.format(tolerance)
    cv2_im = cv2.putText(cv2_im, str_tol, (10, height-8),font, 0.55, (150, 150, 255), 2)
  
    x_dev=arr_track_data[2]
    str_x='X: {}'.format(x_dev)
    if(abs(x_dev)<tolerance):
        color_x=(0,255,0)
    else:
        color_x=(0,0,255)
    cv2_im = cv2.putText(cv2_im, str_x, (110, height-8),font, 0.55, color_x, 2)
    
    y_dev=arr_track_data[3]
    str_y='Y: {}'.format(y_dev)
    if(abs(y_dev)>0.9):
        color_y=(0,255,0)
    else:
        color_y=(0,0,255)
    cv2_im = cv2.putText(cv2_im, str_y, (220, height-8),font, 0.55, color_y, 2)
   
    #write command, tracking status and speed
    cmd=arr_track_data[4]
    cv2_im = cv2.putText(cv2_im, str(cmd), (int(width/2) + 10, height-8),font, 0.68, (0, 255, 255), 2)
    
    delay1=arr_track_data[5]
    str_sp='Speed: {}%'.format(round(delay1/(0.1)*100,1))
    cv2_im = cv2.putText(cv2_im, str_sp, (int(width/2) + 185, height-8),font, 0.55, (150, 150, 255), 2)
    
    # ... rest of the function ...

    for obj in objs:
        x0, y0, x1, y1 = list(obj.bbox)
        x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
        percent = int(100 * obj.score)
        
        box_color, text_color, thickness=(0,150,255), (0,255,0),1
        
        text3 = '{}% {}'.format(percent, labels.get(obj.id, obj.id))
        
        if(labels.get(obj.id, obj.id)=="person"):
            cv2_im = cv2.rectangle(cv2_im, (x0, y0), (x1, y1), box_color, thickness)
            cv2_im = cv2.putText(cv2_im, text3, (x0, y1-5),font, 0.5, text_color, thickness)

    return cv2_im          
 
if __name__ == '__main__':
    main()
