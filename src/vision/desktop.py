from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from .runtime import VisionRuntime
from .server import VisionHTTPServer


def run_desktop_shell(runtime: VisionRuntime, server: VisionHTTPServer, dashboard_url: str) -> None:
    """Run a small native shell around the same multi-agent runtime and API."""
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = tk.Tk()
    root.title("VISION · Multi-Agent Command Center")
    root.geometry("720x600")
    root.minsize(620, 480)
    root.configure(bg="#071016")

    title = tk.Label(root, text="VISION", font=("Segoe UI", 24, "bold"), fg="#5de7e1", bg="#071016")
    title.pack(anchor="w", padx=24, pady=(20, 0))
    subtitle = tk.Label(root, text="Coordinator online · specialist network ready", fg="#7fa6ad", bg="#071016")
    subtitle.pack(anchor="w", padx=26, pady=(0, 15))

    agents_frame = tk.LabelFrame(root, text="AGENT NETWORK", fg="#5de7e1", bg="#0d1a22", bd=1, relief="solid")
    agents_frame.pack(fill="x", padx=20, pady=8)
    agents = runtime.agent_specs()
    ttk.Style().configure("Vision.TLabel", background="#0d1a22", foreground="#d9f3f2")
    for index, agent in enumerate(agents):
        label = tk.Label(agents_frame, text=f"●  {agent['name']}  ·  {agent['role']}", anchor="w", fg="#d9f3f2", bg="#0d1a22")
        label.grid(row=index // 2, column=index % 2, sticky="ew", padx=12, pady=5)
    agents_frame.columnconfigure(0, weight=1)
    agents_frame.columnconfigure(1, weight=1)

    command_frame = tk.LabelFrame(root, text="DISPATCH COMMAND", fg="#5de7e1", bg="#0d1a22", bd=1, relief="solid")
    command_frame.pack(fill="x", padx=20, pady=8)
    prompt = tk.Entry(command_frame, bg="#071016", fg="#d9f3f2", insertbackground="#5de7e1", relief="flat")
    prompt.pack(side="left", fill="x", expand=True, padx=12, pady=12)
    log = tk.Text(root, height=14, bg="#071016", fg="#b9d7d5", insertbackground="#5de7e1", relief="flat", state="disabled")
    log.pack(fill="both", expand=True, padx=20, pady=8)

    def append(text: str) -> None:
        log.configure(state="normal")
        log.insert("end", text + "\n")
        log.see("end")
        log.configure(state="disabled")

    def dispatch() -> None:
        value = prompt.get().strip()
        if not value:
            return
        prompt.delete(0, "end")
        try:
            task = runtime.create_task(value)
            append(f"> {value}\n  dispatched to {task.route} [{task.risk} risk]")
            poll(task.id)
        except ValueError as exc:
            messagebox.showerror("VISION", str(exc))

    def poll(task_id: str) -> None:
        task = runtime.store.get_task(task_id)
        if not task:
            return
        if task["status"] in {"completed", "failed", "awaiting_approval", "cancelled"}:
            append(f"[{task['status']}] {task.get('result') or task.get('error') or 'approval required'}")
            return
        root.after(300, lambda: poll(task_id))

    def open_dashboard() -> None:
        webbrowser.open(dashboard_url)

    tk.Button(command_frame, text="DISPATCH", command=dispatch, fg="#5de7e1", bg="#0d343b", relief="flat").pack(side="right", padx=(0, 8), pady=8)
    tk.Button(root, text="OPEN WEB DASHBOARD", command=open_dashboard, fg="#ffc857", bg="#382b0d", relief="flat").pack(anchor="e", padx=20, pady=(0, 15))
    prompt.bind("<Return>", lambda _event: dispatch())
    append("VISION native shell ready. Dispatch a task to activate the network.")

    def close() -> None:
        server.shutdown()
        server.server_close()
        runtime.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()
