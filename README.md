# 녹음파일 자동 요약기

## 이게 하는 일
1. **파일 열기** 버튼 -> 녹음파일(여러 개 선택 가능)을 순서대로 자동 처리
2. 음성 -> 텍스트 변환 (faster-whisper, 로컬/무료/오프라인)
3. 텍스트 -> 아래 3개 항목으로 자동 정리 (Gemini API, 무료 티어)
   ```
   가맹점명: ...
   장애접수내용: ...
   조치내용: ...
   ```
   내용이 통화에 없으면 자동으로 "확인필요"라고 표시됩니다.
4. 결과는 화면의 텍스트 박스에 파일별로 순서대로 쌓이며, 그대로 드래그해서 복사 가능합니다.
5. **API키 입력하고 저장** 버튼으로 한 번 입력한 키는 `%APPDATA%\RecordingSummarizer\config.json`에 저장되어, 프로그램을 껐다 켜도 다시 입력할 필요 없습니다.
6. 텍스트 파일 저장 기능은 없습니다 (화면 표시 + 복사만).

## 실제로 사용할 PC에 Python이 없다면 (exe 방식)

exe는 **만드는 PC**에서만 Python이 필요하고, 만들어진 exe 파일은 **Python 없는 PC에서도 그대로 실행**됩니다.

1. Python이 설치된 다른 PC (집 PC, 개인 노트북 등)를 준비
2. 그 PC에 `app.py`, `requirements.txt`, `build_exe.bat` 3개 파일을 저장
3. `build_exe.bat` 더블클릭 -> 자동으로 패키지 설치 + exe 빌드
4. 완료되면 `dist` 폴더 안에 생기는 **`RecordingSummarizer.exe`** 파일 하나만 복사
5. 그 exe 파일을 실제로 사용할 PC(회사 PC 등, Python 없어도 됨)로 옮겨서 더블클릭 실행

> ffmpeg는 exe 안에 자동으로 포함되지 않으므로, 실행할 PC에 ffmpeg 설치가 필요합니다 (아래 안내 참고). ffmpeg까지 exe 하나에 묶고 싶으시면 말씀해 주세요.

## Python이 있는 PC라면 (스크립트 방식, 더 간단)

1. `app.py`, `requirements.txt`, `run.bat`를 같은 폴더에 저장
2. `run.bat` 더블클릭 -> 첫 실행 시 패키지 자동 설치 후 바로 프로그램 실행
3. 다음부터는 `run.bat`만 더블클릭하면 됨

## 공통 준비물

### Python (exe를 만드는 PC에만 필요)
https://www.python.org/downloads/ 에서 Python 3.10 이상 설치
설치 시 **"Add Python to PATH"** 체크 필수

### ffmpeg (실행하는 모든 PC에 필요, 음성 인식용)
- https://www.gyan.dev/ffmpeg/builds/ 에서 다운로드
- 압축 해제 후 `bin` 폴더 경로를 시스템 환경변수 PATH에 추가
- 명령 프롬프트에서 `ffmpeg -version` 입력했을 때 버전 정보가 나오면 성공

### Gemini API 키
https://aistudio.google.com/app/apikey 에서 무료로 발급 (신용카드 불필요)

## 첫 실행 시 참고
- 프로그램이 뜨면 **API키 입력하고 저장**을 먼저 눌러 Gemini API 키를 등록하세요 (최초 1회만).
- **파일 열기**를 처음 누르면 음성 인식 모델(약 500MB 내외)을 자동으로 다운로드합니다. 이때만 인터넷이 필요하고, 이후에는 오프라인으로도 음성 인식이 동작합니다 (요약은 Gemini API 호출이라 인터넷 필요).
- 파일이 길수록 처리 시간이 늘어납니다. 여러 개를 선택하면 순서대로 자동 처리됩니다.

## 정확도/속도 조절 (선택)
`app.py` 상단의 다음 줄에서 모델 크기를 바꿀 수 있습니다:
```python
WHISPER_MODEL_SIZE = "small"   # base(빠름/부정확) < small < medium < large(느림/정확)
```
