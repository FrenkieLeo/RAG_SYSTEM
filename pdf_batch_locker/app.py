from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from pdf_batch_locker.core import (
    BatchItemResult,
    EncryptionOptions,
    PdfBatchLockerError,
    PasswordValidationError,
    batch_encrypt_folder,
    summarize_results,
    validate_passwords,
)


class PdfBatchLockerApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("PDF 批量加密工具")
        self.root.geometry("820x640")
        self.root.minsize(760, 560)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.input_dir = StringVar()
        self.output_dir = StringVar()
        self.source_password = StringVar()
        self.open_password = StringVar()
        self.open_password_confirm = StringVar()
        self.owner_password = StringVar()
        self.owner_password_confirm = StringVar()

        self.enable_open_password = BooleanVar(value=False)
        self.restrict_print = BooleanVar(value=True)
        self.restrict_copy = BooleanVar(value=True)
        self.restrict_modify = BooleanVar(value=True)
        self.restrict_comment = BooleanVar(value=True)
        self.restrict_fill_forms = BooleanVar(value=True)
        self.restrict_assemble = BooleanVar(value=True)
        self.recursive = BooleanVar(value=False)
        self.overwrite = BooleanVar(value=False)

        self._build_ui()
        self._toggle_open_password_fields()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(6, weight=1)

        ttk.Label(main, text="批量给文件夹内 PDF 加密，并限制打印、复制、注释、插入/删除页面等操作。").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(main, text="输入文件夹").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(main, textvariable=self.input_dir).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(main, text="选择...", command=self._choose_input_dir).grid(row=1, column=2, sticky="ew", pady=4)

        ttk.Label(main, text="输出文件夹").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(main, textvariable=self.output_dir).grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(main, text="选择...", command=self._choose_output_dir).grid(row=2, column=2, sticky="ew", pady=4)

        options_frame = ttk.LabelFrame(main, text="批处理选项", padding=10)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        for column in range(4):
            options_frame.columnconfigure(column, weight=1)
        ttk.Checkbutton(options_frame, text="包含子文件夹", variable=self.recursive).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options_frame, text="覆盖已存在输出文件", variable=self.overwrite).grid(row=0, column=1, sticky="w")
        ttk.Label(options_frame, text="若源 PDF 已有打开密码，可在下方填写。").grid(row=0, column=2, columnspan=2, sticky="w")

        password_frame = ttk.LabelFrame(main, text="密码", padding=10)
        password_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        password_frame.columnconfigure(1, weight=1)
        password_frame.columnconfigure(3, weight=1)

        ttk.Label(password_frame, text="源 PDF 密码").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(password_frame, textvariable=self.source_password, show="*").grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=8, pady=4
        )

        ttk.Checkbutton(
            password_frame,
            text="设置打开密码",
            variable=self.enable_open_password,
            command=self._toggle_open_password_fields,
        ).grid(row=1, column=0, sticky="w", pady=(8, 4))
        self.open_entry = ttk.Entry(password_frame, textvariable=self.open_password, show="*")
        self.open_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(8, 4))
        ttk.Label(password_frame, text="确认打开密码").grid(row=1, column=2, sticky="w", pady=(8, 4))
        self.open_confirm_entry = ttk.Entry(password_frame, textvariable=self.open_password_confirm, show="*")
        self.open_confirm_entry.grid(row=1, column=3, sticky="ew", padx=8, pady=(8, 4))

        ttk.Label(password_frame, text="权限密码").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(password_frame, textvariable=self.owner_password, show="*").grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Label(password_frame, text="确认权限密码").grid(row=2, column=2, sticky="w", pady=4)
        ttk.Entry(password_frame, textvariable=self.owner_password_confirm, show="*").grid(
            row=2, column=3, sticky="ew", padx=8, pady=4
        )
        ttk.Label(password_frame, text="密码长度 6-128 位；权限密码用于解除限制，请妥善保存。").grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(4, 0)
        )

        permissions_frame = ttk.LabelFrame(main, text="禁止以下操作", padding=10)
        permissions_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        for column in range(3):
            permissions_frame.columnconfigure(column, weight=1)

        ttk.Checkbutton(permissions_frame, text="打印", variable=self.restrict_print).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Checkbutton(permissions_frame, text="复制/提取内容", variable=self.restrict_copy).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Checkbutton(permissions_frame, text="修改文档内容", variable=self.restrict_modify).grid(row=0, column=2, sticky="w", pady=2)
        ttk.Checkbutton(permissions_frame, text="注释", variable=self.restrict_comment).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Checkbutton(permissions_frame, text="填写表单和签名", variable=self.restrict_fill_forms).grid(
            row=1, column=1, sticky="w", pady=2
        )
        ttk.Checkbutton(permissions_frame, text="插入、删除、旋转页面", variable=self.restrict_assemble).grid(
            row=1, column=2, sticky="w", pady=2
        )
        ttk.Button(permissions_frame, text="全选禁止", command=lambda: self._set_restrictions(True)).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Button(permissions_frame, text="全部允许", command=lambda: self._set_restrictions(False)).grid(
            row=2, column=1, sticky="w", pady=(8, 0)
        )

        log_frame = ttk.LabelFrame(main, text="处理日志", padding=10)
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = ttk.Treeview(log_frame, columns=("status", "source", "message"), show="headings", height=10)
        self.log.heading("status", text="状态")
        self.log.heading("source", text="文件")
        self.log.heading("message", text="说明")
        self.log.column("status", width=80, anchor="center")
        self.log.column("source", width=360)
        self.log.column("message", width=300)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        bottom = ttk.Frame(main)
        bottom.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.start_button = ttk.Button(bottom, text="开始加密", command=self._start)
        self.start_button.grid(row=0, column=1)

    def _choose_input_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if not selected:
            return
        self.input_dir.set(selected)
        if not self.output_dir.get():
            path = Path(selected)
            self.output_dir.set(str(path.with_name(f"{path.name}_encrypted")))

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择输出文件夹")
        if selected:
            self.output_dir.set(selected)

    def _toggle_open_password_fields(self) -> None:
        state = "normal" if self.enable_open_password.get() else "disabled"
        self.open_entry.configure(state=state)
        self.open_confirm_entry.configure(state=state)
        if state == "disabled":
            self.open_password.set("")
            self.open_password_confirm.set("")

    def _set_restrictions(self, value: bool) -> None:
        self.restrict_print.set(value)
        self.restrict_copy.set(value)
        self.restrict_modify.set(value)
        self.restrict_comment.set(value)
        self.restrict_fill_forms.set(value)
        self.restrict_assemble.set(value)

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        try:
            options = self._read_options()
        except (PdfBatchLockerError, PasswordValidationError) as exc:
            messagebox.showerror("无法开始", str(exc))
            return

        self.log.delete(*self.log.get_children())
        self.progress.configure(value=0, maximum=100)
        self.start_button.configure(state="disabled")
        self._append_log("准备", Path(self.input_dir.get()), "开始扫描 PDF 文件")

        input_dir = Path(self.input_dir.get().strip())
        output_dir = Path(self.output_dir.get().strip())
        self.worker = threading.Thread(target=self._run_batch, args=(input_dir, output_dir, options), daemon=True)
        self.worker.start()
        self.root.after(100, self._poll_events)

    def _read_options(self) -> EncryptionOptions:
        input_raw = self.input_dir.get().strip()
        output_raw = self.output_dir.get().strip()
        if not input_raw:
            raise PdfBatchLockerError("请选择输入文件夹。")
        if not output_raw:
            raise PdfBatchLockerError("请选择输出文件夹。")
        input_dir = Path(input_raw)
        output_dir = Path(output_raw)

        restrictions_enabled = any(
            [
                self.restrict_print.get(),
                self.restrict_copy.get(),
                self.restrict_modify.get(),
                self.restrict_comment.get(),
                self.restrict_fill_forms.get(),
                self.restrict_assemble.get(),
            ]
        )
        validate_passwords(
            open_password_enabled=self.enable_open_password.get(),
            open_password=self.open_password.get(),
            open_password_confirm=self.open_password_confirm.get(),
            owner_password=self.owner_password.get(),
            owner_password_confirm=self.owner_password_confirm.get(),
            restrictions_enabled=restrictions_enabled,
        )

        return EncryptionOptions(
            source_password=self.source_password.get(),
            open_password=self.open_password.get() if self.enable_open_password.get() else "",
            owner_password=self.owner_password.get(),
            restrict_print=self.restrict_print.get(),
            restrict_copy=self.restrict_copy.get(),
            restrict_modify=self.restrict_modify.get(),
            restrict_comment=self.restrict_comment.get(),
            restrict_fill_forms=self.restrict_fill_forms.get(),
            restrict_assemble=self.restrict_assemble.get(),
            overwrite=self.overwrite.get(),
            recursive=self.recursive.get(),
        )

    def _run_batch(self, input_dir: Path, output_dir: Path, options: EncryptionOptions) -> None:
        def progress(index: int, total: int, result: BatchItemResult) -> None:
            self.events.put(("progress", (index, total, result)))

        try:
            results = batch_encrypt_folder(input_dir, output_dir, options, progress=progress)
        except Exception as exc:  # noqa: BLE001 - surface worker errors to the user.
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("done", results))

    def _poll_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "progress":
                index, total, result = payload  # type: ignore[misc]
                self.progress.configure(maximum=total, value=index)
                self._append_log("成功" if result.ok else "失败", result.source, result.message)
            elif event == "done":
                results = payload  # type: ignore[assignment]
                succeeded, failed = summarize_results(results)  # type: ignore[arg-type]
                self.start_button.configure(state="normal")
                messagebox.showinfo("处理完成", f"成功：{succeeded} 个\n失败：{failed} 个")
                return
            elif event == "error":
                self.start_button.configure(state="normal")
                messagebox.showerror("处理失败", str(payload))
                return

        if self.worker and self.worker.is_alive():
            self.root.after(100, self._poll_events)
        else:
            self.start_button.configure(state="normal")

    def _append_log(self, status: str, source: Path, message: str) -> None:
        self.log.insert("", "end", values=(status, str(source), message))
        children = self.log.get_children()
        if children:
            self.log.see(children[-1])


def main() -> None:
    root = Tk()
    PdfBatchLockerApp(root)
    root.mainloop()
