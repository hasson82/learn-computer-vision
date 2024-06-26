import cv2
import numpy as np
import matplotlib.pyplot as plt
import glob
import queue
import threading

confidence_threshold = 0.5
with open("..\\..\\models\\coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

path_prefix = "..\\..\\models"
model_cfg = f"{path_prefix}\\yolov3-608.cfg"
model_weights = f"{path_prefix}\\yolov3-608.weights"
net = cv2.dnn.readNetFromDarknet(model_cfg, model_weights)

# Define the writer thread function
def write_frames(video_writer, id):
    i = 0
    while True:
        i += 1
        frame = frames[id].get()
        if frame is None:  # None is used as a signal to stop the thread
            print("Got none")
            break
        print(f"frame {i}")
        video_writer.write(frame)
    video_writer.release()

frames = []
frame_queue = queue.Queue(maxsize=100)
frames.append(frame_queue)

def get_output_layers(net):
    layer_names = net.getLayerNames()
    # print(layer_names)
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
    # print(output_layers)

    return output_layers

def rotate_image(image):
    return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

def object_detection(image):
    blob = cv2.dnn.blobFromImage(image, scalefactor=0.00392, size=(608, 608), mean=(0, 0, 0), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(get_output_layers(net))
    hT, wT, sT = image.shape
    
    detections = []
    blank_image = np.zeros_like(image)
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > confidence_threshold:
                detections.append({"class_id": classes[class_id], "confidence": confidence})
                # Calculate bounding box coordinates
                # Draw bounding box
                if (classes[class_id] == "person"):
                    w, h = int(detection[2] * wT), int(detection[3] * hT)
                    x, y = int((detection[0] * wT) - w / 2), int((detection[1] * hT) - h / 2)
                    cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    cv2.rectangle(blank_image, (x, y), (x+w, y+h), (0, 0, 0), -1)
    return image
    
    # rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    # rotated_blank_image = cv2.rotate(blank_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    # plt.imshow(rotated_image)
    # plt.show()

def image_analysis():
    print("Image Analysis - NFL Defenses")
    nfl_pictures = glob.glob("nfl_coaches_film/*.png")
    
    for picture in nfl_pictures:
        print(picture)
        image = cv2.imread(picture)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        object_detection(rgb_image)

def video_analysis():
    print("Video Analysis - NFL Defenses")
    video = cv2.VideoCapture("nfl_coaches_film/browns_49ers_offense_1_drive.webm")
    fps = video.get(cv2.CAP_PROP_FPS)/2
    frame_width = int(video.get(3))
    frame_height = int(video.get(4))
    print(fps)
    delay = int(1000/fps)
    last_frame_hist = None
    i = 0
    out = cv2.VideoWriter(f'output_video{i}.webm', cv2.VideoWriter_fourcc(*'VP90'), fps, (frame_width, frame_height))
    threads = []
    writer_thread = threading.Thread(target=write_frames, args=(out,i,))
    threads.append(writer_thread)
    writer_thread.start()
    send_frame = True
    frame_number = 0
    while True:
        ret, frame = video.read()
        # If an image frame has been grabbed, display it
        if ret:
            frame_resized = cv2.resize(frame, (frame.shape[1] // 2, frame.shape[0] // 2))
            image_with_detections = frame_resized
            cv2.imshow('Displaying image frames from video file', image_with_detections)
            gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
            cur_frame_hist = cv2.calcHist([gray], [0], None, [256], [0, 256])  
            if last_frame_hist is not None:    
                cmp = cv2.compareHist(last_frame_hist, cur_frame_hist, cv2.HISTCMP_CORREL)  
                if cmp > 0.9:
                    # if frame_number % 10 == 0:
                    frames[i].put(frame, block=True)
                else:
                    print("Reached new play")
                    print(f"Put None in queue {i}")
                    frames[i].put(None)
                    i += 1
                    if i >= 15:
                        print(f"created {i} threads")
                        break
                    out = cv2.VideoWriter(f'output_video{i}.webm', cv2.VideoWriter_fourcc(*'VP90'), fps, (frame_width, frame_height))
                    frame_queue = queue.Queue(maxsize=100)
                    frames.append(frame_queue)
                    writer_thread = threading.Thread(target=write_frames, args=(out,i,))
                    threads.append(writer_thread)
                    writer_thread.start()
                    frames[i].put(frame, block=True)

            last_frame_hist = cur_frame_hist
            frame_number += 1
            # print(f"last frame hist: {last_frame_hist}")
            # print(f"cur frame hist: {cur_frame_hist}")
            cv2.waitKey(delay)
        
        if not ret:
            break
        # rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # object_detection(rgb_frame)
        if cv2.waitKey(delay) & 0xFF == ord("q"):
            break
        # if cv2.waitKey(delay) & 0xFF == ord("d"):
        #     delay = delay*2
        #     print("d")
        # if cv2.waitKey(delay) & 0xFF == ord("a"):
        #     delay = delay/2
        #     print("a")
        # if cv2.waitKey(delay) & 0xFF == ord("s"):
        #     print("stopped video")
        #     cv2.waitKey()
    
    # Signal the writer thread to finish and wait for it
    frames[-1].put(None)
    print("Put None in queue")
    for thread in threads:
        thread.join()
    print("All threads have completed")

    video.release()
    out.release()
    cv2.destroyAllWindows()

def main():
    video_analysis()

if __name__ == "__main__":
    main() 