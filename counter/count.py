import os
import yaml
import numpy as np
import cv2
from datetime import datetime
import threading
import time
import queue
import mysql.connector

BACKEND_URL = 'https://127.0.0.1:3000/auto_count'

MYSQL_CONFIG = {
    'host': '34.97.183.142',
    'port': 3306,
    'user': 'FruxAdmin',
    'password': 'Fruxadmin#2025',
    'database': 'FRUX',
}

VIDEO_SOURCES = {
    1: "Camera A (ID 1)",
    2: "Camera B (ID 2)",
    3: "Camera C (ID 3)",
    4: "Camera D (ID 4)",
    5: "Camera E (ID 5)",
    6: "Camera F (ID 6)",
}

CAMERA_TABLE_MAP = {
    "Camera A (ID 1)": "Aライン生産データ",
    "Camera B (ID 2)": "Bライン生産データ",
    "Camera C (ID 3)": "Cライン生産データ",
    "Camera D (ID 4)": "Dライン生産データ",
    "Camera E (ID 5)": "Eライン生産データ",
    "Camera F (ID 6)": "Fライン生産データ",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
fn_yaml = os.path.join(BASE_DIR, "data.yaml")

config = {'save_video': False,
          'text_overlay': True,
          'object_overlay': True,
          'object_id_overlay': False,
          'object_detection': True,
          'min_area_motion_contour': 200,
          'min_area_ratio': 0.02,
          'park_sec_to_wait': 0.25,
          'min_gap_between_counts': 0.6,
          'bg_diff_thresh': 25,
          'bg_update_alpha': 0.02,
          'start_frame': 0}

stop_event = threading.Event()

frame_queue = queue.Queue(maxsize=40) 
DISPLAY_WINDOW_SIZE = (480,360)

def log_count_to_mysql(camera_name, total_count, ppm, timestamp, is_check_only=False):
    """
    Save total_count in 自動数 and returns the active task_id and is_paused status.
    A task is paused if 中断時刻 IS NOT NULL and 再開時刻 IS NULL.
    is_check_only=True: Only check task_id and is_paused, not update 自動数.
    Returns: (task_id, is_paused) or (None, False)
    """
    table_name = CAMERA_TABLE_MAP.get(camera_name)
    
    if not table_name:
        print(f"[MySQL Log] ERROR: Camera name '{camera_name}' not found in CAMERA_TABLE_MAP.")
        return None, False

    conn = cursor = None
    task_id = None
    is_paused = False 
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG) 
        cursor = conn.cursor()

        cursor.execute(f"""
                       SELECT 商品コード, 中断時刻, 再開時刻
                       FROM {table_name}
                       WHERE 開始時刻 IS NOT NULL AND 終了時刻 IS NULL
                       ORDER BY 商品コード DESC
                       LIMIT 1
                       """)
        row = cursor.fetchone()
        
        if not row:
            return None, False 
        
        task_id = row[0]
        interruption_time = row[1] 
        resume_time = row[2]       

        if interruption_time is not None and resume_time is None:
             is_paused = True

        if not is_check_only and not is_paused: 
            cursor.execute(f"""
                           UPDATE {table_name}
                           SET 自動数 = %s WHERE 商品コード = %s
                           """, (total_count, task_id))
            conn.commit()
            
            if cursor.rowcount == 0:
                 print(f"[MySQL Log] WARNING: No rows updated in {table_name}. Task ID not found.")
        
        return task_id, is_paused 

    except mysql.connector.Error as err:
        print(f"[MySQL Error] Failed to process data in {table_name}: {err}")
        return None, False
    except Exception as e:
        print(f"[General Error] Log function error: {e}")
        return None, False
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn and conn.is_connected():
            conn.close()

def load_yaml_data(fn_yaml):
    """Loading data of file YAML."""
    try:
        with open(fn_yaml, 'r') as stream:
            object_area_data = yaml.safe_load(stream)
            if not object_area_data:
                print(f"Warning: File YAML '{fn_yaml}' Empty or Not found data of countting area.")
                return [], []
    except FileNotFoundError:
        print(f"Error: Not Found file YAML: {fn_yaml}")
        return [], [], 
    except Exception as e:
        print(f"Error reading YAML file: {e}")
        return [], []
        
    object_bounding_rects = []
    
    for park in object_area_data:
        points = np.array(park['points'], dtype=np.int32)
        rect = cv2.boundingRect(points)
        object_bounding_rects.append(rect)
            
    print(f"ROI area: {len(object_area_data)}")
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

        self.total_output_cam = 0
        self.current_task_id = None
        self.is_paused = False 
        self.last_check_time = time.time() 
        self.check_interval = 2.0

        self.start_time_cam = datetime.now()
        self.last_time_cam = datetime.now()
        self.ct_cam = 0.0
        self.ppm_cam = 0.0
        self.fastest_cam = 0.0
        self.ppm_average_cam = 0.0

        self.bg_rois = [None] * len(self.object_area_data)
        self.last_count_time = [None] * len(self.object_area_data)
        self.reset_detection = True

    def reset_counter(self):
        """Reset total count when object start or finish."""
        if self.total_output_cam > 0:
            print(f"[{self.camera_name}] 🔄 Task {self.current_task_id} ended. Resetting counter from {self.total_output_cam}.")
        
        self.total_output_cam = 0
        self.current_task_id = None
        self.is_paused = False 

        self.start_time_cam = datetime.now()
        self.last_time_cam = datetime.now()
        self.ct_cam = 0.0
        self.ppm_cam = 0.0
        self.fastest_cam = 0.0
        self.ppm_average_cam = 0.0

        self.last_count_time = [None] * len(self.object_area_data)
        self.reset_detection = True

    def check_task_status(self):
        """check object active or not."""

        active_task_id, is_paused_db = log_count_to_mysql(self.camera_name, 0, 0, datetime.now(), is_check_only=True)

        if self.current_task_id is not None and active_task_id == self.current_task_id and self.is_paused != is_paused_db:
             if is_paused_db:
                 print(f"[{self.camera_name}] ⏸️ Task {active_task_id} is PAUSED (中断).")
             else:
                 print(f"[{self.camera_name}] ▶️ Task {active_task_id} is RESUMED (再開).")
             self.is_paused = is_paused_db

        elif self.current_task_id is None and active_task_id is not None:
            print(f"[{self.camera_name}] 🟢 New task found: {active_task_id}")
            self.reset_counter()
            self.current_task_id = active_task_id
            self.is_paused = is_paused_db 
            
        elif self.current_task_id is not None and active_task_id is None:
            print(f"[{self.camera_name}] 🛑 Current task {self.current_task_id} finished on iPad. Resetting.")
            self.reset_counter()
            
        elif self.current_task_id is not None and active_task_id is not None and self.current_task_id != active_task_id:
            print(f"[{self.camera_name}] ➡️ Task switch: {self.current_task_id} -> {active_task_id}. Resetting.")
            self.reset_counter()
            self.current_task_id = active_task_id
            self.is_paused = is_paused_db 

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            print(f"Can't Open Camera {self.camera_id} ({self.camera_name}). Passed this thread.")
            return

        print(f"Camera Opening {self.camera_name} (ID: {self.camera_id})")

        self.reset_counter()
        self.check_task_status()

        n_rois = len(self.object_area_data)
        object_status = [False] * n_rois
        object_buffer = [None] * n_rois
        last_count_time = [None] * n_rois

        prev_task_id = self.current_task_id

        kernel = np.ones((3, 3), np.uint8)
        bgs = cv2.createBackgroundSubtractorMOG2(
            history=int(config.get("bg_history", 500)),
            varThreshold=float(config.get("bg_var_threshold", 32)),
            detectShadows=bool(config.get("bg_detect_shadows", False)),
        )

        while cap.isOpened() and not self.stop_event.is_set():
            try:
                current_time_sec = time.time()
                if current_time_sec - self.last_check_time > self.check_interval:
                    self.check_task_status()
                    self.last_check_time = current_time_sec

                    if self.current_task_id != prev_task_id:
                        object_status = [False] * n_rois
                        object_buffer = [None] * n_rois
                        last_count_time = [None] * n_rois
                        prev_task_id = self.current_task_id

                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                video_cur_pos = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                frame_out = frame.copy()

                frame_h, frame_w = frame.shape[:2]
                frame_blur = cv2.GaussianBlur(frame, (5, 5), 0)

                lr_wait = float(config.get("bg_learning_rate_wait", 0.01))
                lr_active = float(config.get("bg_learning_rate_active", 0.002))
                lr = lr_active if (self.current_task_id is not None and not self.is_paused) else lr_wait

                fg = bgs.apply(frame_blur, learningRate=lr)
                _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)
                fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
                fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)

                if bool(config.get("object_detection", True)):
                    min_area_abs = int(config.get("min_area_motion_contour", 200))
                    min_area_ratio = float(config.get("min_area_ratio", 0.02))
                    park_wait = float(config.get("park_sec_to_wait", 0.25))
                    min_gap = float(config.get("min_gap_between_counts", 0.6))

                    for ind in range(n_rois):
                        x, y, w, h = self.object_bounding_rects[ind]
                        x1 = 0 if x < 0 else x
                        y1 = 0 if y < 0 else y
                        x2 = frame_w if (x + w) > frame_w else (x + w)
                        y2 = frame_h if (y + h) > frame_h else (y + h)

                        if x2 <= x1 or y2 <= y1:
                            status = object_status[ind]
                        else:
                            roi_fg = fg[y1:y2, x1:x2]
                            if roi_fg.size <= 0:
                                status = object_status[ind]
                            else:
                                area = cv2.countNonZero(roi_fg)
                                roi_area = int((x2 - x1) * (y2 - y1))
                                min_area = min_area_abs
                                ratio_area = int(min_area_ratio * roi_area)
                                if ratio_area > min_area:
                                    min_area = ratio_area
                                status = area >= min_area

                        if status != object_status[ind]:
                            if object_buffer[ind] is None:
                                object_buffer[ind] = video_cur_pos
                            elif (video_cur_pos - object_buffer[ind]) > park_wait:
                                leaving = (object_status[ind] is True) and (status is False)

                                if leaving and (self.current_task_id is not None) and (not self.is_paused):
                                    can_count = True
                                    lt = last_count_time[ind]
                                    if lt is not None and (video_cur_pos - lt) < min_gap:
                                        can_count = False

                                    if can_count:
                                        self.total_output_cam += 1
                                        last_count_time[ind] = video_cur_pos

                                        current_time = datetime.now()
                                        diff = current_time - self.last_time_cam
                                        self.ct_cam = diff.total_seconds()
                                        self.ppm_cam = round(60 / self.ct_cam, 2) if self.ct_cam > 0 else 0.0
                                        self.last_time_cam = current_time

                                        diff_total = current_time - self.start_time_cam
                                        minutes = diff_total.total_seconds() / 60
                                        self.ppm_average_cam = round(self.total_output_cam / minutes, 2) if minutes > 0 else 0.0

                                        if self.ppm_cam > self.fastest_cam:
                                            self.fastest_cam = self.ppm_cam

                                        print(
                                            f"[{self.camera_name}] Count* {self.total_output_cam}, "
                                            f"PPM: {self.ppm_cam:.2f}, Avg PPM: {self.ppm_average_cam:.2f}"
                                        )

                                        self.current_task_id, self.is_paused = log_count_to_mysql(
                                            self.camera_name, self.total_output_cam, self.ppm_cam, current_time, is_check_only=False
                                        )

                                        if self.current_task_id != prev_task_id:
                                            object_status = [False] * n_rois
                                            object_buffer = [None] * n_rois
                                            last_count_time = [None] * n_rois
                                            prev_task_id = self.current_task_id

                                object_status[ind] = status
                                object_buffer[ind] = None
                        elif object_buffer[ind] is not None:
                            object_buffer[ind] = None

                if bool(config.get("object_overlay", True)):
                    for ind, park in enumerate(self.object_area_data):
                        points = np.array(park["points"], dtype=np.int32)
                        color = (0, 255, 0) if object_status[ind] else (0, 0, 255)
                        if self.is_paused:
                            color = (150, 150, 150)
                        cv2.drawContours(frame_out, [points], contourIdx=-1, color=color, thickness=2, lineType=cv2.LINE_8)

                        if bool(config.get("object_id_overlay", False)):
                            moments = cv2.moments(points)
                            if moments["m00"] != 0:
                                centroid = (int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"]))
                                cv2.putText(frame_out, str(park.get("id", ind)), centroid, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA,)

                if bool(config.get("text_overlay", True)):
                    cv2.rectangle(frame_out, (1, 5), (410, 105), (0, 255, 0), 2)
                    cv2.putText(frame_out, f"CAMERA: {self.camera_name}", (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2, cv2.LINE_AA,)

                    if self.current_task_id is not None:
                        status_text = "STATUS: PAUSED (中断中)" if self.is_paused else "STATUS: ACTIVE"
                        status_color = (0, 255, 255) if self.is_paused else (0, 0, 255)

                        cv2.putText(frame_out, f"{status_text}, Task: {self.current_task_id}", (5, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2, cv2.LINE_AA,)
                        cv2.putText(frame_out, f"Total: {self.total_output_cam}  AvgPPM: {self.ppm_average_cam:.2f}", (5, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA,)
                        cv2.putText(frame_out, f"Fastest PPM: {self.fastest_cam:.2f}", (5, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA,)
                    else:
                        cv2.putText(frame_out, "STATUS: WAITING TASK...", (5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
                        cv2.putText(frame_out, "Task will start from iPad", (5, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA,)

                try:
                    self.frame_queue.put((self.camera_name, frame_out), timeout=0.01)
                except queue.Full:
                    pass

            except Exception as e:
                print(f"Camera Error {self.camera_name}: {e}")
                break

            time.sleep(0.001)

        cap.release()
        print(f"Camera {self.camera_name} Stopped. Final Count: {self.total_output_cam}")


if __name__ == '__main__':

    if not object_area_data:
        print("Not found data of ROI, System can't be start. Log Out.")
        exit()
        
    threads = []

    for camera_id, camera_name in VIDEO_SOURCES.items():
        t = CameraWorker(camera_id, camera_name, object_area_data, object_bounding_rects, stop_event, frame_queue)
        threads.append(t)
        t.start()

    print("Camera Systems Start. Press 'q' or ESC to exit.")
    
    try:
        while not stop_event.is_set():
            try:
                camera_name, frame_out = frame_queue.get(timeout=0.001) 
                
                imS = cv2.resize(frame_out, DISPLAY_WINDOW_SIZE)
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