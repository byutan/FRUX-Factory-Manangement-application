import os
from ultralytics import YOLO

if __name__ == '__main__':
    # 1. Xác định đường dẫn tuyệt đối tới file data.yaml để tránh lỗi nhận diện sai thư mục làm việc
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(BASE_DIR, "datasets", "osechi_dataset", "data.yaml")
    
    # 2. Khởi tạo cấu trúc mô hình YOLOv8m (Medium) gốc từ nhà phát hành
    # Nếu máy bạn chưa có file 'yolov8m.pt', Python sẽ tự động tải về bản pre-trained chuẩn
    model = YOLO("yolov8m.pt") 
    
    print("="*60)
    print("--- BẮT ĐẦU QUÁ TRÌNH HUẤN LUYỆN YOLOv8m NHẬN DIỆN HỘP OSECHI ---")
    print(f"File cấu hình Dataset: {yaml_path}")
    print("="*60)
    
    # 3. Cấu hình các tham số tối ưu để Train cho bài toán công nghiệp
    results = model.train(
        data=yaml_path,         # Đường dẫn file cấu hình hệ thống dữ liệu
        epochs=1,             # Lặp lại 100 lượt học (đủ để mô hình đạt độ chính xác cao ổn định)
        imgsz=640,              # Kích thước ảnh đầu vào chuẩn hóa
        batch=16,               # Số lượng ảnh nạp vào GPU cùng lúc. Nếu bị lỗi "Out of Memory", hãy hạ xuống 8 hoặc 4
        device=0,               # Chạy bằng GPU số 0 (Nvidia). Nếu máy không có card rời, hãy sửa thành 'cpu'
        workers=4,              # Số luồng CPU tham gia bóc tách và tiền xử lý ảnh (Mosaic, Augment)
        save=True,              # Tự động lưu lại các file checkpoint (.pt) sau mỗi lượt học tốt
        project="osechi_train_runs", # Tên thư mục tổng chứa kết quả
        name="yolov8m_run",     # Tên thư mục của lượt train này
        optimizer="AdamW",      # Bộ tối ưu hóa giúp hội tụ nhanh và ổn định
        lr0=0.001,              # Tốc độ học ban đầu phù hợp với kỹ thuật Transfer Learning
        close_mosaic=10         # Tắt tính năng ghép ảnh Mosaic ở 10 epoch cuối cùng để mô hình căn chỉnh tọa độ mịn hơn
    )
    
    print("\n" + "="*60)
    print("--- QUÁ TRÌNH TRAIN HOÀN TẤT ---")
    print("Mô hình chính xác nhất (best.pt) nằm tại:")
    print("osechi_train_runs/yolov8m_run/weights/best.pt")
    print("="*60)