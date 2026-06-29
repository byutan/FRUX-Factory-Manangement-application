import os
import yaml
import numpy as np
import cv2
from datetime import datetime
import threading
import time
import queue
import mysql.connector
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import requests
import multiprocessing as mp


BACKEND_URL = 'http://127.0.0.1:3000/auto_count'

# MYSQL_CONFIG = {
#     'host': '34.97.183.142',
#     'port': 3306,
#     'user': 'FruxAdmin',
#     'password': 'Fruxadmin#2025',
#     'database': 'FRUX',
# }

VIDEO_SOURCES = {
    1: "Camera A (ID 1)",
    # 2: "Camera B (ID 2)",
    # 3: "Camera C (ID 3)",
    # 4: "Camera D (ID 4)",
    # 5: "Camera E (ID 5)",
    # 6: "Camera F (ID 6)",
}

CAMERA_TABLE_MAP = {
    "Camera A (ID 1)": "Aライン生産データ",
    # "Camera B (ID 2)": "Bライン生産データ",
    # "Camera C (ID 3)": "Cライン生産データ",
    # "Camera D (ID 4)": "Dライン生産データ",
    # "Camera E (ID 5)": "Eライン生産データ",
    # "Camera F (ID 6)": "Fライン生産データ",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_PATH = os.path.join(BASE_DIR, 'best_openvino_model')
BYTETRACK_YAML_PATH = os.path.join(BASE_DIR, 'bytetrack.yaml')
FONT_PATH = os.path.join(BASE_DIR, 'NotoSansJP-Regular.ttf')

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


DISPLAY_WINDOW_SIZE = (640, 480)
stop_event = threading.Event()
frame_queue = queue.Queue(maxsize=40) 

def log_count_to_mysql(camera_name, total_count, ppm, timestamp, is_check_only=False):
    """
    Save total_count in 自動数 and returns the active task_id and is_paused status.
    A task is paused if 中断時刻 IS NOT NULL and 再開時刻 IS NULL.
    is_check_only=True: Only check task_id and is_paused, not update 自動数.
    Returns: (task_id, is_paused) or (None, False)
    """
    # table_name = CAMERA_TABLE_MAP.get(camera_name)
    
    # if not table_name:
    #     print(f"[MySQL Log] ERROR: Camera name '{camera_name}' not found in CAMERA_TABLE_MAP.")
    #     return None, False

    # conn = cursor = None
    # task_id = None
    # is_paused = False 
    # try:
    #     conn = mysql.connector.connect(**MYSQL_CONFIG) 
    #     cursor = conn.cursor()

    #     cursor.execute(f"""
    #                    SELECT 商品コード, 中断時刻, 再開時刻
    #                    FROM {table_name}
    #                    WHERE 開始時刻 IS NOT NULL AND 終了時刻 IS NULL
    #                    ORDER BY 商品コード DESC
    #                    LIMIT 1
    #                    """)
    #     row = cursor.fetchone()
        
    #     if not row:
    #         return None, False 
        
    #     task_id = row[0]
    #     interruption_time = row[1] 
    #     resume_time = row[2]       

    #     if interruption_time is not None and resume_time is None:
    #          is_paused = True

    #     if not is_check_only and not is_paused: 
    #         cursor.execute(f"""
    #                        UPDATE {table_name}
    #                        SET 自動数 = %s WHERE 商品コード = %s
    #                        """, (total_count, task_id))
    #         conn.commit()
            
    #         if cursor.rowcount == 0:
    #              print(f"[MySQL Log] WARNING: No rows updated in {table_name}. Task ID not found.")
    # except mysql.connector.Error as err:
    #     print(f"[MySQL Error] Failed to process data in {table_name}: {err}")
    #     return None, False
    # except Exception as e:
    #     print(f"[General Error] Log function error: {e}")
    #     return None, False
    # finally:
    #     if 'cursor' in locals() and cursor:
    #         cursor.close()
    #     if 'conn' in locals() and conn and conn.is_connected():
    #         conn.close()
    dummy_task_id = "LOCAL_TASK_001"
    is_paused = False
    
    return dummy_task_id, is_paused


def send_count_to_backend(line_char, count):
    try:
        requests.post(BACKEND_URL, json={'line': line_char, 'total_count': count}, timeout=0.5)
    except:
        pass

class CameraWorker(threading.Thread):
    def __init__(self, source, camera_name, stop_event, frame_queue):
        super().__init__()
        self.source = source
        self.camera_name = camera_name
        self.stop_event = stop_event
        self.frame_queue = frame_queue

        self.counted_ids = set()

        self.tracked_left_ids = set()

        self.total_output_cam = 0
        self.current_task_id = None
        self.is_paused = False 

        self.start_time_cam = datetime.now()
        self.last_time_cam = datetime.now()
        self.ppm_cam = 0.0
        self.ppm_average_cam = 0.0
        self.fastest_cam = 0.0

        self.last_check_time = time.time() 
        self.check_interval = 2.0

    def reset_counter(self):
        """Reset total count when object start or finish."""
        if self.total_output_cam > 0:
            print(f"[{self.camera_name}] タスク{self.current_task_id} 終わった. {self.total_output_cam} からカウンターをリセット.")
        
        self.counted_ids.clear()

        self.tracked_left_ids.clear()
        
        self.total_output_cam = 0
        self.current_task_id = None
        self.is_paused = False 

        self.start_time_cam = datetime.now()
        self.last_time_cam = datetime.now()
        self.ppm_cam = 0.0
        self.ppm_average_cam = 0.0
        self.fastest_cam = 0.0

        line_char = self.camera_name.split(' ')[1]
        threading.Thread(target=send_count_to_backend, args=(line_char, 0)).start()

    def check_task_status(self):
        """check object active or not."""
        line_char = self.camera_name.split(' ')[1]
        try:
            res = requests.get(f"http://127.0.0.1:3000/api/camera/status/{line_char}", timeout=1.0)
            if res.status_code == 200:
                data = res.json()
                active_task_id = data.get("product")
                is_paused_server = data.get("paused", False)
                is_finished_server = data.get("finished", False)
            
                if is_finished_server or active_task_id is None:
                    if self.current_task_id is not None:
                        print(f"[{self.camera_name}] 終了している.")
                        self.current_task_id = None 
                        self.is_paused = False
                    return

                if self.current_task_id is not None and active_task_id == self.current_task_id:
                        if self.is_paused != is_paused_server:
                            if is_paused_server:
                                print(f"[{self.camera_name}] 中断している.")
                            else:
                                print(f"[{self.camera_name}] 再開している.")
                            self.is_paused = is_paused_server

                elif self.current_task_id is None and active_task_id is not None:
                        print(f"[{self.camera_name}] 開始している.")
                        self.reset_counter()
                        self.current_task_id = active_task_id
                        self.is_paused = is_paused_server

        except requests.exceptions.RequestException as e:
            pass
        except Exception as e:
            print(f"[{self.camera_name}] サーバーエラー: {e}")

    def run(self):
        print(f"[{self.camera_name}] Loading YOLO Model...")
        self.model = YOLO(WEIGHTS_PATH, task='detect')
        self.font = ImageFont.truetype(FONT_PATH, 32) if os.path.exists(FONT_PATH) else ImageFont.load_default()

        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print(f"Can't Open Camera {self.source} ({self.camera_name}). Passed this thread.")
            return

        print(f"Camera Opening {self.camera_name} (ID: {self.source})")

        self.reset_counter()
        self.check_task_status()

        alpha = 1.5 
        beta = 20   

        while cap.isOpened() and not self.stop_event.is_set():
            current_time_sec = time.time()
            if current_time_sec - self.last_check_time > self.check_interval:
                self.check_task_status()
                self.last_check_time = current_time_sec

            ret, frame = cap.read()
            if not ret:
                break 

            image_scale = 1
            height, width = frame.shape[:2]
            frame = cv2.resize(frame, (round(width / image_scale), round(height / image_scale)))
            new_height, new_width = frame.shape[:2]
            
            mid_line_x = new_width * 3 // 4

            start_line_x = new_width // 4

            enhanced_frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

            if self.current_task_id is not None and not self.is_paused:
                results = self.model.track(source=enhanced_frame, persist=True, tracker=BYTETRACK_YAML_PATH, conf=0.6, iou=0.4, verbose=False)
            else:
                results = None
            
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)

            # Tính toán logic đếm
            if results and len(results) > 0 and results[0].boxes and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                
                for box, obj_id in zip(boxes, ids):
                    center_x = (box[0] + box[2]) // 2
                    if center_x < start_line_x:
                        continue
                    elif center_x <= mid_line_x:
                        self.tracked_left_ids.add(obj_id)
                        
                        draw.rectangle([box[0], box[1], box[2], box[3]], outline=(255, 0, 255), width=2)
                        draw.text((box[0], max(0, box[1] - 40)), f"ID: {obj_id}", font=self.font, fill=(255, 0, 255)) 

                    else:
                        if obj_id not in self.counted_ids:
                            if obj_id in self.tracked_left_ids:
                                
                                current_time = datetime.now()
                                diff = current_time - self.last_time_cam
                                ct_cam = diff.total_seconds()
                                
                                if ct_cam >= 0.5 or self.total_output_cam == 0:
                                    self.counted_ids.add(obj_id)
                                    self.total_output_cam += 1
                                    
                                    self.ppm_cam = round(60 / ct_cam, 2) if ct_cam > 0 and self.total_output_cam > 1 else 0.0
                                    self.last_time_cam = current_time

                                    diff_total = current_time - self.start_time_cam
                                    minutes = diff_total.total_seconds() / 60
                                    self.ppm_average_cam = round(self.total_output_cam / minutes, 2) if minutes > 0 else 0.0

                                    if self.ppm_cam > self.fastest_cam:
                                        self.fastest_cam = self.ppm_cam

                                    line_char = self.camera_name.split(' ')[1] 
                                    
                                    api_thread = threading.Thread(target=send_count_to_backend, args=(line_char, self.total_output_cam), daemon=True)
                                    api_thread.start()
                                    
                                    log_count_to_mysql(self.camera_name, self.total_output_cam, self.ppm_cam, current_time, is_check_only=False)
                                    
                                    print(f"[{self.camera_name}] Count +1 = {self.total_output_cam} | Task: {self.current_task_id}")
                                else:
                                    self.counted_ids.add(obj_id)
                            else:
                                self.counted_ids.add(obj_id)
                        
                        continue

            # 5. Vẽ thông tin UI lên ảnh
            frame_out = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            # Vẽ vạch đếm
            color_line = (0, 0, 255) if self.is_paused else (0, 255, 0)
            cv2.line(frame_out, (mid_line_x, 0), (mid_line_x, new_height), color_line, 2)

            cv2.line(frame_out, (start_line_x, 0), (start_line_x, new_height), (0, 255, 255), 1)

            # Vẽ Overlay Information
            cv2.rectangle(frame_out, (1, 5), (410, 105), (0, 255, 0), 2)
            cv2.putText(frame_out, f"CAMERA: {self.camera_name}", (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

            if self.current_task_id is not None:
                status_text = "STATUS: PAUSED" if self.is_paused else "STATUS: ACTIVE"
                status_color = (0, 255, 255) if self.is_paused else (0, 0, 255)
                cv2.putText(frame_out, f"{status_text}, Task: {self.current_task_id}", (5, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
                cv2.putText(frame_out, f"Total: {self.total_output_cam}  AvgPPM: {self.ppm_average_cam:.2f}", (5, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                cv2.putText(frame_out, f"Fastest PPM: {self.fastest_cam:.2f}", (5, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            else:
                cv2.putText(frame_out, "STATUS: WAITING TASK...", (5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

            # 6. Đẩy frame ra queue để hiển thị
            try:
                self.frame_queue.put((self.camera_name, frame_out), timeout=0.01)
            except queue.Full:
                pass

        cap.release()
        print(f"[{self.camera_name}] Camera Stopped.")


if __name__ == '__main__':

    stop_event = mp.Event()
    frame_queue = mp.Queue(maxsize=40)

    processes = []

    for source, camera_name in VIDEO_SOURCES.items():
        t = CameraWorker(source, camera_name, stop_event, frame_queue)
        processes.append(t)
        t.start()

    print("Camera Systems Start. Press 'q' or ESC to exit.")
    
    try:
        while not stop_event.is_set():
            try:
                camera_name, frame_out = frame_queue.get(timeout=0.001) 
                
                imS = cv2.resize(frame_out, DISPLAY_WINDOW_SIZE)
                cv2.imshow(f'Output Counting - {camera_name}', imS)
                
            except mp.queues.Empty:
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

    while not frame_queue.empty():
        try:
            frame_queue.get_nowait()
        except mp.queues.Empty:
            break

    for p in processes:
        p.join(timeout=5)
        if p.is_alive():
            print(f"Force terminating process {p.name}...")
            p.terminate()
            p.join()

    cv2.destroyAllWindows()
    print("Shutdown Systems.")