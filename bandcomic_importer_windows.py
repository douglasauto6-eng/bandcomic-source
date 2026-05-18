#!/usr/bin/env python3
"""
Aplicativo Windows simples para importar PDFs/pastas para o Bandcomic.

Ele usa o mesmo motor do converter_pdf_v3_1.py, gera images/<slug>/ localmente
e publica as imagens + catalogo no Vercel Blob privado atraves do proxy /admin.
"""

import json
import mimetypes
import os
import queue
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import converter_pdf_v3_1 as converter


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_API_URL = "https://bandcomic-source.vercel.app"
os.chdir(PROJECT_DIR)


class BandcomicImporter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bandcomic Importer")
        self.geometry("820x610")
        self.minsize(720, 540)

        self.paths = []
        self.log_queue = queue.Queue()
        self.worker = None

        self.profile_var = tk.StringVar(value=converter.DEFAULT_PROFILE)
        self.tags_var = tk.StringVar(value=", ".join(converter.DEFAULT_TAGS))
        self.api_url_var = tk.StringVar(value=DEFAULT_API_URL)
        self.admin_token_var = tk.StringVar(value="")
        self.upload_blob_var = tk.BooleanVar(value=True)

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

        ttk.Label(
            top,
            text="Redmi Watch 5 = melhor equilibrio; Mi Band 9 Pro = antigo; Premium = mais zoom.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(top, text="Tags").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.tags_var).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Label(
            top,
            text="Separe por virgula. Pesquise no relogio por PDF, Bandcomic, tag:nome ou #nome.",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        server = ttk.LabelFrame(root, text="Vercel Blob privado", padding=10)
        server.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        server.columnconfigure(1, weight=1)

        ttk.Label(server, text="API").grid(row=0, column=0, sticky="w")
        ttk.Entry(server, textvariable=self.api_url_var).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(server, text="Token").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(server, textvariable=self.admin_token_var, show="*").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Checkbutton(
            server,
            text="Enviar imagens e catalogo para o Vercel Blob apos converter",
            variable=self.upload_blob_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(
            server,
            text="Use o mesmo valor de ADMIN_TOKEN/SOURCE_TOKEN configurado no Vercel.",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

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
        self.run_button = ttk.Button(actions, text="Converter e publicar", command=self.run_conversion)
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
        if self.upload_blob_var.get() and not self.admin_token_var.get().strip():
            messagebox.showwarning("Bandcomic Importer", "Informe o token do Vercel antes de publicar.")
            return

        self.run_button.configure(state=tk.DISABLED)
        self.log_text.delete("1.0", tk.END)
        self.log("Iniciando conversao...")

        self.worker = threading.Thread(target=self._convert_worker, daemon=True)
        self.worker.start()

    def _api_base_url(self):
        return self.api_url_var.get().strip().rstrip("/")

    def _request(self, url, data, content_type, token):
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": content_type,
                "X-Admin-Token": token,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read().decode("utf-8", errors="replace")
                return response.status, body
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Falha de rede: {exc}") from exc

    def _local_file_for_ref(self, ref):
        if not ref or ref.startswith("http://") or ref.startswith("https://"):
            return None
        if "\\" in ref or ".." in ref:
            return None
        return PROJECT_DIR / Path(*ref.split("/"))

    def _iter_blob_files(self, entries):
        seen = set()
        for entry in entries:
            refs = [entry.get("cover")] + list(entry.get("pages") or [])
            for ref in refs:
                if not ref or ref in seen:
                    continue
                seen.add(ref)
                local_path = self._local_file_for_ref(ref)
                if local_path and local_path.exists():
                    yield ref, local_path
                else:
                    self.log(f"  aviso: arquivo local nao encontrado para {ref}")

    def _upload_blob_file(self, base_url, token, ref, local_path):
        query = urllib.parse.urlencode({"path": ref, "access": "private"})
        url = f"{base_url}/admin/blob?{query}"
        data = local_path.read_bytes()
        content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
        status, _ = self._request(url, data, content_type, token)
        self.log(f"  blob {status}: {ref} ({len(data) // 1024} KB)")

    def _upload_catalog(self, base_url, token, catalog):
        url = f"{base_url}/admin/catalog"
        data = json.dumps(catalog, ensure_ascii=False, indent=2).encode("utf-8")
        status, _ = self._request(url, data, "application/json; charset=utf-8", token)
        self.log(f"  catalog {status}: {len(catalog)} livro(s)")

    def _publish_to_vercel(self, catalog, entries):
        base_url = self._api_base_url()
        token = self.admin_token_var.get().strip()
        if not base_url:
            raise RuntimeError("Informe a URL da API Vercel.")
        if not token:
            raise RuntimeError("Informe o token ADMIN_TOKEN/SOURCE_TOKEN.")

        self.log("")
        self.log("Publicando no Vercel Blob privado...")
        for ref, local_path in self._iter_blob_files(entries):
            self._upload_blob_file(base_url, token, ref, local_path)
        self._upload_catalog(base_url, token, catalog)
        self.log("Publicacao concluida.")

    def _convert_worker(self):
        try:
            profile = converter.PROFILES[self.profile_var.get()]
            _, catalog, entries = converter.process_inputs(
                self.paths,
                profile,
                output_dir=PROJECT_DIR / "images",
                catalog_path=PROJECT_DIR / "catalog.json",
                storage="blob",
                tags=self.tags_var.get(),
                log=self.log,
            )
            if self.upload_blob_var.get():
                self._publish_to_vercel(catalog, entries)
            self.log("Concluido.")
            self.after(0, lambda: messagebox.showinfo("Bandcomic Importer", "Importacao concluida."))
        except Exception as exc:
            error_message = str(exc)
            self.log(f"ERRO: {error_message}")
            self.after(0, lambda: messagebox.showerror("Bandcomic Importer", error_message))
        finally:
            self.after(0, lambda: self.run_button.configure(state=tk.NORMAL))


if __name__ == "__main__":
    app = BandcomicImporter()
    app.mainloop()
