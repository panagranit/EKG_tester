import json
import mimetypes
import os
import queue
import sys
import threading
from pathlib import Path

# Re-launch with the project's .venv if the current Python lacks the packages
# (e.g. the Run triangle picked the system Python).
_venv_python = Path(__file__).with_name(".venv") / "bin" / "python"
try:
    import requests
    from dotenv import load_dotenv
except ModuleNotFoundError:
    if _venv_python.exists() and Path(sys.executable) != _venv_python:
        os.execv(str(_venv_python), [str(_venv_python), *sys.argv])
    raise

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText

from ekg_result import UNAVAILABLE, summarize_response

load_dotenv(Path(__file__).with_name(".env.landinglens"))

API_URL = "https://predict.app.landing.ai/inference/v1/predict"

# Transcribed from your LandingLens screenshot.
ENDPOINT_ID = "0a146bfa-1ccd-4201-aed1-f864eb3f7de1"

root = tk.Tk()
root.title("Cliff's EKG API Tester")
root.geometry("760x520")
root.withdraw()

api_key = os.environ.get("LANDINGLENS_API_KEY", "").strip()
if not api_key:
    api_key = simpledialog.askstring(
        "LandingLens API key",
        "No key found in .env.landinglens. Paste it here (it will not be saved).",
        show="*",
        parent=root,
    )

if not api_key or not api_key.strip():
    root.destroy()
    raise SystemExit

downloads = Path.home() / "Downloads"
samples = Path(__file__).with_name("sample_images")
filename = filedialog.askopenfilename(
    parent=root,
    title="Choose a deidentified EKG image",
    initialdir=str(samples if samples.is_dir() else downloads if downloads.exists() else Path.home()),
    filetypes=[
        ("Image files", "*.png *.jpg *.jpeg *.bmp"),
        ("All files", "*"),
    ],
)

if not filename:
    messagebox.showinfo("No file chosen", "No image was selected, so nothing was sent.", parent=root)
    root.destroy()
    raise SystemExit

image_path = Path(filename)
if not image_path.is_file() or image_path.stat().st_size == 0:
    messagebox.showerror(
        "Invalid file",
        "Choose an existing, non-empty EKG image (PNG/JPG/BMP).\n"
        "This dialog opens a file; it does not create one.",
        parent=root,
    )
    root.destroy()
    raise SystemExit

approved = messagebox.askyesno(
    "Confirm upload",
    f"Send {Path(filename).name} to LandingLens?\n\n"
    "Use only synthetic or properly deidentified images.\n"
    "Your deployment lists a cost of 1 credit per image.\n\n"
    "This is an experimental test, not clinical diagnosis.",
    parent=root,
)

if not approved:
    messagebox.showinfo("Cancelled", "Upload cancelled. Nothing was sent.", parent=root)
    root.destroy()
    raise SystemExit

root.deiconify()
last_result = ""


def save_result():
    if not last_result:
        messagebox.showinfo("Nothing to save", "No result yet.", parent=root)
        return
    path = filedialog.asksaveasfilename(
        parent=root,
        title="Save result",
        initialdir=str(downloads if downloads.exists() else Path.home()),
        initialfile=f"{image_path.stem}_result.json",
        defaultextension=".json",
        filetypes=[("JSON", "*.json"), ("Text", "*.txt"), ("All files", "*")],
    )
    if path:
        Path(path).write_text(last_result, encoding="utf-8")
        messagebox.showinfo("Saved", f"Saved to {path}", parent=root)


save_button = tk.Button(root, text="Save result...", command=save_result, state="disabled")
save_button.pack(side="bottom", pady=(0, 12))
output = ScrolledText(root, wrap="word", font=("TkFixedFont", 11))
output.pack(fill="both", expand=True, padx=12, pady=12)
output.insert("end", "Uploading image and waiting for the model...\n")
output.configure(state="disabled")
results = queue.Queue()


def call_api():
    try:
        content_type = mimetypes.guess_type(filename)[0]

        with open(filename, "rb") as image_file:
            response = requests.post(
                API_URL,
                params={"endpoint_id": ENDPOINT_ID},
                headers={"apikey": api_key.strip()},
                files={
                    "file": (
                        Path(filename).name,
                        image_file,
                        content_type or "application/octet-stream",
                    )
                },
                timeout=(10, 60),
            )

        summary = None
        try:
            payload = response.json()
            body = json.dumps(payload, indent=2)
            if response.ok:
                summary = summarize_response(payload)
        except ValueError:
            body = response.text
            if response.ok:
                summary = UNAVAILABLE

        heading = "Success" if response.ok else "API error"
        text = f"{heading} — HTTP {response.status_code}\n\n"
        if summary and summary != UNAVAILABLE:
            # Window shows only the prediction; Save result still writes the full response.
            results.put((summary, (text + body).replace(api_key.strip(), "[REDACTED]")))
            return
        if summary:
            text += f"{summary}\n\n--- Raw response ---\n"
        text += body
        results.put(text.replace(api_key.strip(), "[REDACTED]"))

    except requests.Timeout:
        results.put(
            "Request timed out. The server may still have processed it.\n"
            "Check LandingLens before retrying to avoid another charge."
        )
    except Exception as error:
        results.put(
            f"{type(error).__name__}: {error}".replace(
                api_key.strip(), "[REDACTED]"
            )
        )


def check_result():
    global last_result
    try:
        result = results.get_nowait()
    except queue.Empty:
        root.after(100, check_result)
        return

    if isinstance(result, tuple):
        shown, last_result = result
    else:
        shown = last_result = result
    save_button.configure(state="normal")
    output.configure(state="normal")
    output.delete("1.0", "end")
    output.insert("end", shown)
    output.configure(state="disabled")


threading.Thread(target=call_api, daemon=True).start()
root.after(100, check_result)
root.mainloop()