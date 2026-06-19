import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
from datetime import datetime

class ObjectTracking:
    def __init__(self):
        # モデル、動画、および設定ファイルのパス設定
        dir = os.path.dirname(os.path.abspath(__file__))
        weights_path = os.path.join(dir, 'best_openvino_model')
        self.video_path = os.path.join(dir, 'pos_cond.mov') 
        self.bytetrack_yaml_path = os.path.join(dir, 'bytetrack.yaml')
        
        # YOLOモデルの初期化
        self.model = YOLO(weights_path, task='detect')

        # フォントの設定
        font_path = os.path.join(dir, 'NotoSansJP-Regular.ttf')
        self.font = ImageFont.truetype(font_path, 32) if os.path.exists(font_path) else ImageFont.load_default()

    def track_object(self):
        # トラッキングの設定
        n_frames = 1
        image_scale = 1
        counted_ids = set()
        
        # 動画のキャプチャ（Webカメラを使用する場合は0を指定）
        # cap = cv2.VideoCapture(self.video_path)　
        cap = cv2.VideoCapture(0) 

        # フレームレートの取得と遅延時間の計算
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = int(1000 / fps) * n_frames

        # ウィンドウの作成
        cv2.namedWindow("frame", cv2.WINDOW_NORMAL)

        # トラッキングループ
        while True:

            # フレームの読み込み
            ret, frame = cap.read()
            if not ret: break
            
            # Webカメラの映像が左右反転している場合は、ここで反転を解除する
            frame = cv2.flip(frame, 1)

            # フレームのリサイズと中心線の計算
            height, width = frame.shape[:2]
            frame = cv2.resize(frame, (round(width / image_scale), round(height / image_scale)))
            new_height, new_width = frame.shape[:2]
            mid_line_x = new_width * 3 // 4

            # トラッキングの実行
            results = self.model.track(source=frame, persist=True, tracker=self.bytetrack_yaml_path, verbose=False)
            
            # PILを使用してフレームに描画するための準備
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            
            # 1. カウント数の表示
            draw.text((30, 20), f"数: {len(counted_ids)}", font=self.font, fill=(255, 0, 0))
            
            # 2. トラッキングされたオブジェクトの描画とカウント
            if results[0].boxes.id is not None:

                # トラッキングされたオブジェクトの座標とIDを取得
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                
                # オブジェクトが中心線を越えたかどうかを確認し、カウントする
                for box, id in zip(boxes, ids):
                    if (box[0] + box[2]) // 2 > mid_line_x:
                        counted_ids.add(id)

                    # バウンディングボックスの描画
                    draw.rectangle([box[0], box[1], box[2], box[3]], outline=(255, 0, 255), width=2)
                    
                    # オブジェクトIDの表示
                    draw.text((box[0], max(0, box[1] - 40)), f"おせち箱 {id}", font=self.font, fill=(255, 0, 255)) 

            # PILで描画したフレームをOpenCV形式に変換して表示
            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            # 中心線の描画
            cv2.line(frame, (mid_line_x, 0), (mid_line_x, new_height), (0, 255, 0), 2)
            
            # フレームの表示と終了条件の設定
            cv2.imshow("frame", frame)
            if cv2.waitKey(delay) & 0xFF == ord("q"): break
                
        # キャプチャの解放とウィンドウの破棄
        cap.release()
        cv2.destroyAllWindows()

        # カウント数をテキストファイルに保存
        output_dir = os.path.join(dir, 'tracking_data')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 現在の日時を取得してフォーマット
        now = datetime.now().strftime("%Y年%m月%d日 %H時")

        # カウント数をテキストファイルに保存
        file_path = os.path.join(output_dir, "result.txt")

        # ファイルに追記モードで書き込み
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{now} 数: {len(counted_ids)}\n")

        print(f"{file_path}に数を保存した。")

if __name__ == '__main__':
    ObjectTracking().track_object()