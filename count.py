import os
import yaml
import numpy as np
import cv2
from datetime import datetime
import threading
import time
import queue
from ultralytics import YOLO  # Import thư viện YOLO

# Thay thế các số 0, 1, 2... bằng địa chỉ IP/Stream URL của 6 chiếc iPad
VIDEO_SOURCE = {
    0: "iPad Camera 1", # Ví dụ thay bằng: "http://192.168.1.101:8080/video"
    1: "iPad Camera 2",
    2: "iPad Camera 3",
    3: "iPad Camera 4",
    4: "iPad Camera 5",
    5: "iPad Camera 6",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
fn_yaml = os.path.join(BASE_DIR, "datasets", "area.yml")
# Đường dẫn tới model YOLO
MODEL_PATH = os.path.join(BASE_DIR, "models", "osechi_yolov8m.pt")

config = {'save_video': False,
          'text_overlay': True,
          'object_overlay': True,
          'object_id_overlay': False,
          'object_detection': True,
          'park_sec_to_wait': 0.1,
          'start_frame': 0,
          'confidence_threshold': 0.65} ###Chỉ nhận diện hộp khi độ tin cậy >= 65%

stop_event = threading.Event()
frame_queue = queue.Queue(maxsize=10)

def load_yaml_data(fn_yaml):
    """Loading data of file YAML."""
    try:
        with open(fn_yaml, 'r') as stream:
            object_area_data = yaml.safe_load(stream)
            if not object_area_data:
                print(f"Warning: File YAML '{fn_yaml}' Empty or not found data of counting area.")
                return [], []
    except Exception as e:
        print(f"Error reading file YAML: {e}")
        return [], []
        
    object_bounding_rects = []
    for park in object_area_data:
        points = np.array(park['points'], dtype=np.int32)
        rect = cv2.boundingRect(points)
        object_bounding_rects.append(rect)
            
    print(f"ROI area loaded: {len(object_area_data)}")
    return object_area_data, object_bounding_rects

object_area_data, object_bounding_rects = load_yaml_data(fn_yaml)

class CameraWorker(threading.Thread):
    def __init__(self, camera_id, camera_name, object_area_data, object_bounding_rects, stop_event, frame_queue):
        super().__init__()
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.object_area_data = object_area_data
        self.object_bounding_rects = object_bounding_rects
        self.stop_event = stop_event
        self.frame_queue = frame_queue
        
        # Khởi tạo model YOLO riêng cho từng luồng Camera
        try:
            self.model = YOLO(MODEL_PATH)
        except Exception as e:
            print(f"Lỗi không tải được model YOLO cho {self.camera_name}: {e}")
            self.model = None

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened() or self.model is None:
            print(f"Can't Open Camera {self.camera_id} ({self.camera_name}) or Model Missing. Pass.")
            return

        print(f"Opening {self.camera_name} (ID: {self.camera_id})")

        start_time_cam = datetime.now()
        last_time_cam = datetime.now()
        ct_cam = 0.0
        ppm_cam = 0.0
        total_output_cam = 0
        fastest_cam = 0.0
        ppm_average_cam = 0.0

        object_status = [False] * len(self.object_area_data)
        object_buffer = [None] * len(self.object_area_data)

        while cap.isOpened() and not self.stop_event.is_set():
            try:
                ret, frame = cap.read()

                if ret is False or frame is None:
                    time.sleep(0.1)
                    if cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0 and cap.get(cv2.CAP_PROP_POS_FRAMES) >= cap.get(cv2.CAP_PROP_FRAME_COUNT):
                        break
                    continue

                video_cur_pos = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                frame_out = frame.copy()

                if config['object_detection']:
                    # 1. AI DỰ ĐOÁN (Phát hiện hộp)
                    results = self.model.predict(source=frame, conf=config['confidence_threshold'], verbose=False)
                    detections = results[0].boxes.xyxy.cpu().numpy() # Lấy tọa độ [x1, y1, x2, y2]

                    # Vẽ Bounding Box của YOLO lên màn hình (Màu cam)
                    for box in detections:
                        x1, y1, x2, y2 = map(int, box)
                        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                        cv2.rectangle(frame_out, (x1, y1), (x2, y2), (0, 165, 255), 2)
                        cv2.circle(frame_out, (cx, cy), 5, (0, 0, 255), -1) # Chấm đỏ ở tâm hộp

                    # 2. XỬ LÝ LOGIC ROI & ĐẾM
                    for ind, park in enumerate(self.object_area_data):
                        pts = np.array(park['points'], dtype=np.int32)
                        status = False

                        # Kiểm tra xem có tâm hộp nào nằm trong vùng ROI đa giác không
                        for box in detections:
                            x1, y1, x2, y2 = map(int, box)
                            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                            
                            # Nếu tâm hộp (cx, cy) nằm trong polygon -> Kích hoạt trạng thái
                            if cv2.pointPolygonTest(pts, (cx, cy), False) >= 0:
                                status = True
                                break 

                        # Xử lý chống nhiễu (Debounce) và đếm
                        if status != object_status[ind]:
                            if object_buffer[ind] is None:
                                object_buffer[ind] = video_cur_pos
                            elif video_cur_pos - object_buffer[ind] > config['park_sec_to_wait']:
                                # Hộp vừa rời khỏi vùng ROI -> Đếm + 1
                                if object_status[ind] and status is False:
                                    total_output_cam += 1
                                    current_time = datetime.now()
                                    diff = current_time - last_time_cam
                                    ct_cam = diff.total_seconds()
                                    ppm_cam = round(60 / ct_cam, 2) if ct_cam > 0 else 0.0
                                    last_time_cam = current_time

                                    diff_total = current_time - start_time_cam
                                    minutes = diff_total.total_seconds() / 60
                                    ppm_average_cam = round(total_output_cam / minutes, 2) if minutes > 0 else 0.0

                                    if ppm_cam > fastest_cam:
                                        fastest_cam = ppm_cam

                                    print(f"[{self.camera_name}] Hộp Osechi đếm được: {total_output_cam}, PPM: {ppm_cam:.2f}")

                                object_status[ind] = status
                                object_buffer[ind] = None
                        elif status == object_status[ind] and object_buffer[ind] is not None:
                            object_buffer[ind] = None

                # 3. VẼ GIAO DIỆN ROI VÀ CHỮ
                if config['object_overlay']:
                    for ind, park in enumerate(self.object_area_data):
                        points = np.array(park['points'], dtype=np.int32)
                        # Đổi màu xanh lá nếu có hộp bên trong, màu đỏ nếu trống
                        color = (0, 255, 0) if object_status[ind] else (0, 0, 255)
                        cv2.drawContours(frame_out, [points], contourIdx=-1, color=color, thickness=2, lineType=cv2.LINE_8)

                if config['text_overlay']:
                    cv2.rectangle(frame_out, (1, 5), (350, 90), (0, 255, 0), 2)
                    cv2.putText(frame_out, f"{self.camera_name}", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2, cv2.LINE_AA)
                    cv2.putText(frame_out, f"Total Boxes = {total_output_cam}, Speed (PPM) = {ppm_cam:.2f}", (5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(frame_out, f"Fastest PPM: {fastest_cam:.2f}, Average: {ppm_average_cam:.2f}", (5, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
                    cv2.putText(frame_out, f"Last CT (s): {ct_cam:.2f}", (5, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)

                try:
                    self.frame_queue.put((self.camera_name, frame_out), timeout=0.01)
                except queue.Full:
                    pass

            except Exception as e:
                print(f"Camera Error {self.camera_name}: {e}")
                break

            time.sleep(0.001)

        cap.release()
        print(f"[{self.camera_name}] Stopped. Final Count: {total_output_cam}")

if __name__ == '__main__':
    if not object_area_data:
        print("Not found data of ROI, System can't be start. Log Out.")
        exit()

    threads = []
    for camera_id, camera_name in VIDEO_SOURCE.items():
        t = CameraWorker(camera_id, camera_name, object_area_data, object_bounding_rects, stop_event, frame_queue)
        threads.append(t)
        t.start()

    print("Camera systems start. Press 'q' or ESC to exit.")

    try:
        while not stop_event.is_set():
            try:
                camera_name, frame_out = frame_queue.get(timeout=0.001)
                imS = cv2.resize(frame_out, (480, 360))
                cv2.imshow(f'Output Counting - {camera_name}', imS)
            except queue.Empty:
                pass
            
            k = cv2.waitKey(1)
            if k == ord('q') or k == 27:
                stop_event.set()

    except KeyboardInterrupt:
        stop_event.set()
    except Exception as e:
        print(f"Main Loop Error: {e}")
        stop_event.set()

    print("Shutting Down Camera...")
    for t in threads:
        t.join(timeout=5)

    cv2.destroyAllWindows()
    print("Shutdown Systems.")