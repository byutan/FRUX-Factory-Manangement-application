# おせち箱・発見すること・数えること・システム<br><sub>Osechi-tracking-counting-system</sub>

生産ライン上の重箱をリアルタイムで検出し、計数するトラッキングシステム。
<br>A tracking system provides real-time counting of Osechi box moving on production line.

[![Python](https://img.shields.io/badge/Python-3.11.9-blue.svg)](https://www.python.org/)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


## 概要<br><sub>Overview<sub>

本プロジェクトは、既存の『おせち箱トラッキングアプリ』に自動計数システムを統合・アップデートすることを目的としています。コンピュータビジョン技術をモバイルプラットフォームへ連携させることで、生産ラインの監視と在庫管理をリアルタイムかつシームレスに実現します。
<br>**おせち箱管理モバイルアプリの詳細については、以下のリポジトリをご覧ください。[Osechi-Production-Management-App](https://github.com/byutan/Osechi-Production-Management-App)**
<br>This is a continuous development aims to update and intergrate counting system into current Osechi production management app.
<br>**For detail about Osechi mobile app, please visit [Osechi-Production-Management-App](https://github.com/duchuy1805/Osechi-Production-Management-App)**

## フォルダストラクチャ<br><sub>Folder Structure<sub>
```
.
├── .gitignore              # gitignoreファイル
├── NotoSansJP-Regular.ttf  # 日本語フォント
├── README.md               # プロジェクト資料·
├── bytetrack.yaml          # 設定ファイル
└── osechi_tracking.py      # トラッキングファイル
```

## クイックスタート - Quick Start

### 前提条件 - Prerequisites

1. **Pythonのバージョン確認 - Verify Python version**
```bash
python -v 
```
```3.11.9```を確認してください。
<br>Make sure the version is ```3.11.9```.

2. **Microsoft Visual C++ Redistributableを確認する - Verify Microsoft Visual C++ Redistributable**
```bash
Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* | Select-Object DisplayName | Where-Object { $_.DisplayName -like "*Visual C++*" }
```
まだインストールしない場合、以下のリリンクをご覧ください[Microsoft.com](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#latest-supported-redistributable-version)
<br>If not yet installed, please visit [Microsoft.com](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#latest-supported-redistributable-version)

Visual C++ v14ランタイムのセクションから、「X64」用実行ファイル（exe）を選択してください。
<br>Select **X64** exe file from **Visual C++ v14 Redistributable** section.

### セットアップ - Setup

1. Python仮想環境 - Python virtual environment
```bash
python -m venv venv
```

PSSecurityException」により「UnauthorizedAccess」エラーが発生した場合は、以下のコマンドを実行してください：
<br>If you get **UnauthorzedAccess** from **PSSecurityException**, use the command below:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser 
```

スタート
<br>Activate the virtual environment
```bash
.\venv\Scripts\activate
```

2. 依存関係のインストール - Installing dependencies
CPU Pytorch
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

Ultralytics
```bash
pip install ultralytics
```

OpenVINO
```bash
pip install openvino
```

Piplow
```bash
pip install Pillow
```

Lapx
```bash
pip install lapx
```

3. 実行 - Executing
- トラッキング用の動画（例: video.mp4）を入力する場合は、保存先のパスに変更してください。
<br>If you want to input a video for tracking (for example **video.mp4**), change the path to your destination
```bash
self.video_path = os.path.join(dir, 'video.mp4') 
cap = cv2.VideoCapture(self.video_path)
```

- best.ptをOpenVINOモデルにエクスポートします。
<br>Export best.pt to openvino model
```bash
yolo export model=best.pt format=openvino
```

- システムを実行します。
<br>Execute the system
```bash
python osechi_tracking.py
```

- カウントを終了するには、**q**キーを押してください。ルートフォルダに**tracking_data**フォルダが作成されます。
<br>To end counting, press **q** and a folder **tracking_data** will appear in the root folder.
