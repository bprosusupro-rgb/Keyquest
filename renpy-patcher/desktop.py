"""Desktop file picker for the Keyquest Ren’Py APK patcher."""
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from patch_apk import patch, pull_installed


def main():
    root = tk.Tk()
    root.title("Keyquest • Add an in-game keyboard")
    root.geometry("640x390")
    panel = ttk.Frame(root, padding=20)
    panel.pack(fill="both", expand=True)
    panel.columnconfigure(1, weight=1)
    ttk.Label(panel, text="Add a keyboard to a Ren’Py game", font=("", 18, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))
    variables = {}
    rows = [
        ("Downloaded APK", filedialog.askopenfilename, {"filetypes": [("Android APK", "*.apk")]}),
        ("Or installed package", None, {}),
        ("Matching Ren’Py SDK", filedialog.askdirectory, {}),
        ("Android build-tools", filedialog.askdirectory, {}),
        ("Save patched APK", filedialog.asksaveasfilename, {"defaultextension": ".apk"}),
    ]
    for row, (label, picker, options) in enumerate(rows, 1):
        variable = tk.StringVar()
        variables[label] = variable
        ttk.Label(panel, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)
        if picker is None:
            installed = ttk.Combobox(panel, textvariable=variable)
            installed.grid(row=row, column=1, sticky="ew", pady=5)

            def list_packages():
                try:
                    output = subprocess.check_output(
                        ["adb", "-d", "shell", "pm", "list", "packages", "-3"],
                        text=True, timeout=6, stderr=subprocess.STDOUT)
                    installed["values"] = sorted(line.removeprefix("package:").strip()
                                                 for line in output.splitlines()
                                                 if line.startswith("package:"))
                    notices.set("Select an installed game from the package list.")
                except (OSError, subprocess.SubprocessError):
                    notices.set("Connect your Quest, approve USB debugging, and check that adb is on PATH.")

            ttk.Button(panel, text="Load list", command=list_packages).grid(row=row, column=2, padx=(8, 0))
            continue

        ttk.Entry(panel, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=5)
        if picker:
            def choose(variable=variable, picker=picker, options=options):
                selected = picker(parent=root, **options)
                if selected:
                    variable.set(selected)
            ttk.Button(panel, text="Browse…", command=choose).grid(row=row, column=2, padx=(8, 0))

    notices = tk.StringVar(value="Choose an APK file, or enter an installed package with USB debugging connected.")
    ttk.Label(panel, textvariable=notices, wraplength=590).grid(
        row=7, column=0, columnspan=3, sticky="w", pady=(12, 0))
    results = queue.Queue()

    def poll():
        try:
            notices.set(results.get_nowait())
            button.state(["!disabled"])
        except queue.Empty:
            root.after(100, poll)

    def build():
        source, package, sdk, tools, output = (item.get().strip() for item in variables.values())
        if bool(source) == bool(package) or not all((sdk, tools, output)):
            notices.set("Select exactly one input and fill in the SDK, build-tools, and output fields.")
            return
        button.state(["disabled"])
        notices.set("Compiling the keyboard and signing the patched APK…")

        def worker():
            try:
                with tempfile.TemporaryDirectory(prefix="keyquest-input-") as temp:
                    apk = Path(source) if source else Path(temp) / "original.apk"
                    if package:
                        pull_installed(package, apk)
                    destination = Path(output)
                    result = patch(apk, destination, sdk, tools, destination.parent / "keyquest-sideload.p12")
                    results.put(f"Signed APK saved to {result}")
            except Exception as error:
                results.put(f"Build failed: {error}")

        threading.Thread(target=worker, daemon=True).start()
        poll()

    button = ttk.Button(panel, text="Build patched APK", command=build)
    button.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 0))
    root.mainloop()


if __name__ == "__main__":
    main()
