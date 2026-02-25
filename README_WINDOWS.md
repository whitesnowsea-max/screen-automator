# 🖱️ Screen Automator — Windows 설치 및 실행 가이드

## 사전 요구사항

### 1. Python 3.10 이상
- [Python 공식 다운로드](https://www.python.org/downloads/)
- **설치 시 반드시 "Add Python to PATH" 옵션을 체크하세요**

### 2. Tesseract OCR (텍스트 인식 기능 사용 시)
- [Tesseract Windows 설치](https://github.com/UB-Mannheim/tesseract/wiki)
- 기본 경로(`C:\Program Files\Tesseract-OCR`)에 설치하면 자동 감지됩니다
- 한국어 인식이 필요하면 설치 시 "Additional language data" → "Korean" 선택

## 빌드 방법

### 방법 1: 원클릭 빌드 (권장)
```
build_windows.bat
```
더블클릭하면 자동으로:
1. Python 확인
2. 가상환경 생성 및 의존성 설치
3. `.exe` 파일 빌드
4. `dist\ScreenAutomator\` 폴더에 결과물 생성

### 방법 2: 수동 빌드
```cmd
python -m venv venv_win
venv_win\Scripts\activate.bat
pip install -r requirements.txt
pyinstaller --clean --noconfirm ScreenAutomator.spec
```

## 실행 방법

### 빌드 후 실행
```
dist\ScreenAutomator\ScreenAutomator.exe
```

### 소스에서 직접 실행 (개발용)
```cmd
venv_win\Scripts\activate.bat
python main.py
```

## 사용법

| 기능 | 설명 |
|------|------|
| **작업 추가** | 이미지 매칭 또는 텍스트(OCR) 인식으로 화면 요소 자동 클릭 |
| **시작/정지** | ▶️ 시작 버튼 또는 `Ctrl+Shift+S` 단축키 |
| **검사 간격** | 화면을 스캔하는 주기 (초 단위) |

## 배포

`dist\ScreenAutomator\` 폴더 전체를 압축(ZIP)하여 다른 PC에 배포할 수 있습니다.
- Python 설치 불필요
- Tesseract OCR은 텍스트 인식 기능 사용 시에만 별도 설치 필요

## 문제 해결

| 증상 | 해결 방법 |
|------|-----------|
| `python`이 인식되지 않음 | Python 설치 후 PATH에 추가 필요 |
| 빌드 중 `pip install` 실패 | `pip install --upgrade pip` 후 재시도 |
| 실행 시 DLL 오류 | [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 설치 |
| 텍스트 인식이 안 됨 | Tesseract OCR 설치 확인 |
| 한국어가 인식되지 않음 | Tesseract 한국어 언어팩 설치 필요 |
| 백신이 `.exe`를 차단 | 빌드된 `.exe`를 검역 예외에 추가 |
