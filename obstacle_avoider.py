
import common as cm
import cv2
import numpy as np
from PIL import Image
import time
from threading import Thread
import util as ut

ut.init_gpio()
cap = cv2.VideoCapture(0)
threshold = 0.4  # Higher threshold to ignore distant objects
top_k = 5  # Top 5 detected objects
object_to_avoid = ['person', 'bottle', 'chair', 'cup', 'cell phone']  # Customize classes to avoid

# Model setup (same as human_follower.py)
model_dir = '/home/adarsh/projects/code_files/human_following/model'
model = 'mobilenet_ssd_v2_coco_quant_postprocess.tflite'
model_edgetpu = 'mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite'
lbl = 'coco_labels.txt'

# Avoidance parameters
tolerance = 0.2  # Central zone width (avoid if object is within this range)
min_y = 0.6  # Minimum Y-coordinate (closeness to the bottom of the frame)
arr_avoid_data = [0, 0, 0, 0, 0]  # [obj_x_center, obj_y_center, x_deviation, cmd, delay]

# Flask setup
from flask import Flask, Response, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/video_feed')
def video_feed():
    return Response(main(), mimetype='multipart/x-mixed-replace; boundary=frame')

def track_obstacles(objs, labels):
    global arr_avoid_data
    closest_obj = None
    max_y = 0  # Track closest object (highest Y-coordinate)

    for obj in objs:
        lbl = labels.get(obj.id, obj.id)
        if lbl in object_to_avoid:
            _, y_min, _, y_max = obj.bbox
            if y_max > max_y:
                max_y = y_max
                closest_obj = obj

    if not closest_obj:
        print("No obstacles detected")
        ut.forward()
        ut.forward_light("ON")
        ut.left_light("OFF")
        ut.right_light("OFF")
        arr_avoid_data = [0, 0, 0, "No obstacle", 0]
        return

    x_min, y_min, x_max, y_max = closest_obj.bbox
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    x_deviation = 0.5 - x_center

    arr_avoid_data = [x_center, y_center, x_deviation, "Detected", 0]

    # Trigger avoidance if object is close (Y-axis) and centered
    if y_max > min_y and abs(x_deviation) < tolerance:
        Thread(target=avoid_obstacle).start()

def avoid_obstacle():
    ut.red_light("ON")
    ut.forward_light("OFF")
    ut.back()  # Reverse briefly
    time.sleep(0.5)
    ut.stop()

    # Turn left or right based on object's X deviation
    if arr_avoid_data[2] > 0:
        ut.left_light("ON")
        ut.right_light("OFF")
        ut.left()
    else:
        ut.right_light("ON")
        ut.left_light("OFF")
        ut.right()
    
    time.sleep(0.8)
    ut.stop()
    ut.red_light("OFF")
    
    
def main():
    from util import edgetpu
    mdl = model_edgetpu if edgetpu else model
    interpreter, labels = cm.load_model(model_dir, mdl, lbl, edgetpu)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Preprocess frame
        cv2_im = cv2.flip(cv2.flip(frame, 0), -1)
        pil_im = Image.fromarray(cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB))

        # Inference
        cm.set_input(interpreter, pil_im)
        interpreter.invoke()
        objs = cm.get_output(interpreter, threshold, top_k)

        track_obstacles(objs, labels)

        # Overlay frame with data
        cv2_im = append_avoidance_data(cv2_im, objs, labels, arr_avoid_data)

        # Stream via Flask
        ret, jpeg = cv2.imencode('.jpg', cv2_im)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

def append_avoidance_data(cv2_im, objs, labels, arr_data):
    height, width, _ = cv2_im.shape
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Draw center crosshair and danger zone
    cv2.rectangle(cv2_im, (int(width/2 - tolerance*width), 0), 
                  (int(width/2 + tolerance*width), height), (0, 0, 255), 2)
    cv2.line(cv2_im, (int(width/2), 0), (int(width/2), height), (255, 0, 0), 1)

    # Display obstacle data
    cv2.putText(cv2_im, f"Status: {arr_data[3]}", (10, 20), font, 0.6, (0, 255, 0), 2)
    cv2.putText(cv2_im, f"X Deviation: {round(arr_data[2], 2)}", (10, 40), font, 0.6, (0, 255, 0), 2)

    # Draw bounding boxes for target objects
    for obj in objs:
        lbl = labels.get(obj.id, obj.id)
        if lbl in object_to_avoid:
            x0, y0, x1, y1 = map(int, [obj.bbox[0]*width, obj.bbox[1]*height, 
                                      obj.bbox[2]*width, obj.bbox[3]*height])
            cv2.rectangle(cv2_im, (x0, y0), (x1, y1), (0, 0, 255), 2)
            cv2.putText(cv2_im, f"{lbl} {int(obj.score*100)}%", 
                        (x0, y0-5), font, 0.5, (0, 255, 0), 1)

    return cv2_im

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2205, threaded=True)
