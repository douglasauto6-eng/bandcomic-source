#!/usr/bin/env python3
"""
Aplicativo Windows simples para importar PDFs/pastas para o Bandcomic.

Ele usa o mesmo motor do converter_pdf_v3_1.py, entao a estrutura final
continua sendo images/<slug>/ + catalog.json.
"""

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import converter_pdf_v3_1 as converter


PROJECT_DIR = Path(__file__).resolve().parent
os.chdir(PROJECT_DIR)


class BandcomicImporter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bandcomic Importer")
        self.geometry("760x560")
        self.minsize(680, 500)

        self.paths = []
        self.log_queue = queue.Queue()
        self.worker = None

        self.profile_var = tk.StringVar(value=converter.DEFAULT_PROFILE)
        self.github_user_var = tk.StringVar(value=converter.GITHUB_USER)
        self.github_repo_var = tk.StringVar(value=converter.GITHUB_REPO)
        self.github_branch_var = tk.StringVar(value=converter.GITHUB_BRANCH)
        self.tags_var = tk.StringVar(value=", ".join(converter.DEFAULT_TAGS))

        self._build_ui()
        self.after(100, self._drain_log_queue)

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        root.rowconfigure(5, weight=1)

        top = ttk.Frame(root)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Perfil").grid(row=0, column=0, sticky="w")
        profile = ttk.Combobox(
            top,
            textvariable=self.profile_var,
            values=list(converter.PROFILES.keys()),
            state="readonly",
            width=22,
        )
        profile.grid(row=0, column=1, sticky="w", padx=(8, 0))

        hint = ttk.Label(
            top,
            text="Redmi Watch 5 = melhor equilibrio; Mi Band 9 Pro = antigo; Premium = mais zoom.",
        )
        hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(top, text="Tags").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.tags_var).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Label(
            top,
            text="Separe por virgula. Pesquise no relogio por PDF, Bandcomic, tag:nome ou #nome.",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        repo = ttk.LabelFrame(root, text="GitHub das imagens", padding=10)
        repo.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        for i in range(6):
            repo.columnconfigure(i, weight=1)

        ttk.Label(repo, text="Usuario").grid(row=0, column=0, sticky="w")
        ttk.Entry(repo, textvariable=self.github_user_var).grid(row=0, column=1, sticky="ew", padx=(6, 12))
        ttk.Label(repo, text="Repo").grid(row=0, column=2, sticky="w")
        ttk.Entry(repo, textvariable=self.github_repo_var).grid(row=0, column=3, sticky="ew", padx=(6, 12))
        ttk.Label(repo, text="Branch").grid(row=0, column=4, sticky="w")
        ttk.Entry(repo, textvariable=self.github_branch_var).grid(row=0, column=5, sticky="ew", padx=(6, 0))

        files_box = ttk.LabelFrame(root, text="Entradas", padding=10)
        files_box.grid(row=2, column=0, sticky="nsew")
        files_box.columnconfigure(0, weight=1)
        files_box.rowconfigure(0, weight=1)

        self.path_list = tk.Listbox(files_box, height=8)
        self.path_list.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(files_box, orient=tk.VERTICAL, command=self.path_list.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.path_list.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(files_box)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Adicionar PDFs", command=self.add_pdfs).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Adicionar pasta", command=self.add_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(buttons, text="Limpar", command=self.clear_paths).pack(side=tk.LEFT, padx=(8, 0))

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 8))
        self.run_button = ttk.Button(actions, text="Gerar images/ e catalog.json", command=self.run_conversion)
        self.run_button.pack(side=tk.LEFT)
        ttk.Label(actions, text=f"Projeto: {PROJECT_DIR}").pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(root, text="Log").grid(row=4, column=0, sticky="w")
        self.log_text = tk.Text(root, height=10, wrap=tk.WORD)
        self.log_text.grid(row=5, column=0, sticky="nsew")

    def add_pdfs(self):
        selected = filedialog.askopenfilenames(
            title="Selecione PDFs",
            filetypes=[("PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        self._add_paths(selected)

    def add_folder(self):
        selected = filedialog.askdirectory(title="Selecione uma pasta com imagens ou PDFs")
        if selected:
            self._add_paths([selected])

    def _add_paths(self, new_paths):
        for item in new_paths:
            path = str(Path(item))
            if path not in self.paths:
                self.paths.append(path)
                self.path_list.insert(tk.END, path)

    def clear_paths(self):
        self.paths.clear()
        self.path_list.delete(0, tk.END)

    def log(self, message):
        self.log_queue.put(str(message))

    def _drain_log_queue(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.after(100, self._drain_log_queue)

    def run_conversion(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.paths:
            messagebox.showwarning("Bandcomic Importer", "Adicione um PDF ou uma pasta primeiro.")
            return

        self.run_button.configure(state=tk.DISABLED)
        self.log_text.delete("1.0", tk.END)
        self.log("Iniciando conversao...")

        self.worker = threading.Thread(target=self._convert_worker, daemon=True)
        self.worker.start()

    def _convert_worker(self):
        try:
            profile = converter.PROFILES[self.profile_var.get()]
            converter.process_inputs(
                self.paths,
                profile,
                output_dir=PROJECT_DIR / "images",
                catalog_path=PROJECT_DIR / "catalog.json",
                github_user=self.github_user_var.get().strip(),
                github_repo=self.github_repo_var.get().strip(),
                github_branch=self.github_branch_var.get().strip(),
                tags=self.tags_var.get(),
                log=self.log,
            )
            self.log("Concluido.")
            self.after(0, lambda: messagebox.showinfo("Bandcomic Importer", "Conversao concluida."))
        except Exception as exc:
            error_message = str(exc)
            self.log(f"ERRO: {error_message}")
            self.after(0, lambda: messagebox.showerror("Bandcomic Importer", error_message))
        finally:
            self.after(0, lambda: self.run_button.configure(state=tk.NORMAL))


if __name__ == "__main__":
    app = BandcomicImporter()
    app.mainloop()
