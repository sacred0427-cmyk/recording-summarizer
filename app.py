# -*- coding: utf-8 -*-
"""
녹음파일 자동 요약기
- 파일 열기 -> faster-whisper로 텍스트 변환 -> Gemini API로 형식에 맞춰 요약
- API 키는 로컬(%APPDATA%)에 저장되어 재실행해도 유지됨
- 여러 파일을 한 번에 선택하면 순서대로 처리
"""

import os
import sys
import json
import threading
import queue
import traceback
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

APP_NAME = "RecordingSummarizer"
GEMINI_MODEL = "gemini-2.5-flash"  # 무료 티어에서 사용 가능한 모델
WHISPER_MODEL_SIZE = "small"       # base / small / medium 중 선택 가능 (클수록 정확하지만 느림)

AUDIO_EXTS = [
    ("녹음파일", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma"),
    ("모든 파일", "*.*"),
]

PROMPT_TEMPLATE = """다음은 콜센터 상담 통화를 녹음한 뒤 음성인식으로 변환한 텍스트입니다.
아래 3개 항목 형식에 맞춰 한국어로 정리해 주세요.
내용상 해당 정보가 통화에서 확인되지 않으면 값 부분에 반드시 "확인필요" 라고만 적어주세요.
설명이나 추가 문장 없이 아래 형식 그대로만 출력하세요.

가맹점명: (여기에 값)
장애접수내용: (여기에 값)
조치내용: (여기에 값)

--- 통화 텍스트 ---
{transcript}
"""


def get_config_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, APP_NAME)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config.json")


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg):
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class ApiKeyDialog(tk.Toplevel):
    """API 키 입력을 위한 별도 창 (마스킹 처리)"""

    def __init__(self, parent, current_key=""):
        super().__init__(parent)
        self.title("Gemini API 키 입력")
        self.resizable(False, False)
        self.result = None

        tk.Label(self, text="Gemini API 키를 입력하세요:", padx=12, pady=8).pack()
        self.entry = tk.Entry(self, width=50, show="*")
        self.entry.insert(0, current_key)
        self.entry.pack(padx=12, pady=4)
        self.entry.focus()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="저장", width=10, command=self.on_save).pack(side="left", padx=6)
        tk.Button(btn_frame, text="취소", width=10, command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self.on_save())
        self.transient(parent)
        self.grab_set()

    def on_save(self):
        val = self.entry.get().strip()
        if not val:
            messagebox.showwarning("입력 필요", "API 키를 입력해 주세요.")
            return
        self.result = val
        self.destroy()


class RecordingSummarizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("녹음파일 자동 요약기")
        self.geometry("760x560")
        self.minsize(600, 400)

        self.config_data = load_config()
        self.whisper_model = None  # 지연 로딩 (처음 파일 열 때 로드)
        self.gemini_client = None

        self.ui_queue = queue.Queue()
        self._build_ui()
        self.after(100, self._poll_queue)

    # ---------------- UI ----------------
    def _build_ui(self):
        top = tk.Frame(self, pady=8, padx=8)
        top.pack(fill="x")

        open_btn = tk.Button(top, text="파일 열기", width=20, height=2,
                              bg="#1d5f7a", fg="white", command=self.on_open_files)
        open_btn.pack(side="left", padx=(0, 8), fill="x", expand=True)

        key_btn = tk.Button(top, text="API키 입력하고 저장", width=20, height=2,
                             bg="#1d5f7a", fg="white", command=self.on_set_api_key)
        key_btn.pack(side="left", fill="x", expand=True)

        self.status_var = tk.StringVar(value="대기 중")
        status_label = tk.Label(self, textvariable=self.status_var, anchor="w", padx=8)
        status_label.pack(fill="x")

        text_frame = tk.Frame(self, padx=8, pady=(0, 8))
        text_frame.pack(fill="both", expand=True)

        self.text_area = scrolledtext.ScrolledText(text_frame, wrap="word", font=("맑은 고딕", 11))
        self.text_area.pack(fill="both", expand=True)

    # ---------------- API 키 저장 ----------------
    def on_set_api_key(self):
        current = self.config_data.get("gemini_api_key", "")
        dlg = ApiKeyDialog(self, current)
        self.wait_window(dlg)
        if dlg.result:
            self.config_data["gemini_api_key"] = dlg.result
            save_config(self.config_data)
            self.gemini_client = None  # 다음 사용시 재생성
            messagebox.showinfo("저장 완료", "API 키가 저장되었습니다.\n다음 실행에도 계속 유지됩니다.")

    def get_api_key(self):
        return self.config_data.get("gemini_api_key", "")

    # ---------------- 파일 열기 ----------------
    def on_open_files(self):
        if not self.get_api_key():
            messagebox.showwarning("API 키 필요", "먼저 'API키 입력하고 저장' 버튼으로 Gemini API 키를 등록해 주세요.")
            return

        paths = filedialog.askopenfilenames(title="녹음파일 선택 (여러 개 선택 가능)", filetypes=AUDIO_EXTS)
        if not paths:
            return

        # 백그라운드 스레드에서 순서대로 처리 (GUI 멈춤 방지)
        threading.Thread(target=self._process_files_worker, args=(list(paths),), daemon=True).start()

    # ---------------- 백그라운드 처리 ----------------
    def _process_files_worker(self, paths):
        total = len(paths)
        try:
            self._ensure_whisper_loaded()
            self._ensure_gemini_client()
        except Exception as e:
            self.ui_queue.put(("error", f"초기화 실패: {e}\n{traceback.format_exc()}"))
            return

        for idx, path in enumerate(paths, start=1):
            filename = os.path.basename(path)
            self.ui_queue.put(("status", f"처리 중 ({idx}/{total}): {filename} - 음성 인식 중..."))
            try:
                transcript = self._transcribe(path)

                self.ui_queue.put(("status", f"처리 중 ({idx}/{total}): {filename} - 요약 중..."))
                summary = self._summarize(transcript)

                self.ui_queue.put(("append", filename, summary))
            except Exception as e:
                self.ui_queue.put(("append", filename, f"[오류 발생] {e}"))

        self.ui_queue.put(("status", "완료"))

    def _ensure_whisper_loaded(self):
        if self.whisper_model is None:
            from faster_whisper import WhisperModel
            self.ui_queue.put(("status", "음성 인식 모델 불러오는 중 (최초 1회, 다소 시간이 걸릴 수 있습니다)..."))
            self.whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

    def _ensure_gemini_client(self):
        if self.gemini_client is None:
            from google import genai
            self.gemini_client = genai.Client(api_key=self.get_api_key())

    def _transcribe(self, path):
        segments, _info = self.whisper_model.transcribe(path, language="ko")
        text = "".join(seg.text for seg in segments)
        return text.strip()

    def _summarize(self, transcript):
        if not transcript:
            transcript = "(음성 인식 결과 없음)"
        prompt = PROMPT_TEMPLATE.format(transcript=transcript)
        response = self.gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return (response.text or "").strip()

    # ---------------- 메인 스레드 UI 업데이트 ----------------
    def _poll_queue(self):
        try:
            while True:
                item = self.ui_queue.get_nowait()
                kind = item[0]
                if kind == "status":
                    self.status_var.set(item[1])
                elif kind == "append":
                    filename, summary = item[1], item[2]
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    block = f"===== {filename} ({timestamp}) =====\n{summary}\n\n"
                    self.text_area.insert("end", block)
                    self.text_area.see("end")
                elif kind == "error":
                    messagebox.showerror("오류", item[1])
                    self.status_var.set("오류 발생")
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)


def main():
    app = RecordingSummarizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
