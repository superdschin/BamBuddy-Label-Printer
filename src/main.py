"""BamBuddy Etikettendrucker 1.4 – portable Windows-Oberfläche für NIIMBOT B1."""
import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

import keyring
from PIL import Image, ImageTk
from bambuddy_api import normalize_url, fetch_spool
from label import render_label, FORMATS, DEFAULT_FORMAT
from printer import print_label
from i18n import tr, set_language

KEYRING_SERVICE = 'BamBuddy-NIIMBOT-B1'
KEYRING_USER = 'api-key'
CONFIG_DIR = Path(os.environ.get('APPDATA', str(Path.home()))) / 'BamBuddy-Etikettendrucker'
CONFIG_FILE = CONFIG_DIR / 'einstellungen.json'
OUTPUT_DIR = Path.home() / 'Pictures' / 'BamBuddy-Etiketten'


class App:
    def __init__(self, root):
        self.root = root
        root.title('BamBuddy Label Printer 1.0 – NIIMBOT B1')
        try:
            icon_path = Path(__file__).resolve().parent.parent / 'assets' / 'app_icon.ico'
            if not icon_path.exists():
                icon_path = Path(getattr(__import__('sys'), '_MEIPASS', '')) / 'app_icon.ico'
            if icon_path.is_file():
                root.iconbitmap(str(icon_path))
        except (OSError, tk.TclError):
            pass
        self.config = self.read_config()
        set_language(self.config.get('language', 'de'))
        root.geometry(self.config.get('geometry', '850x650'))
        root.minsize(680, 580)
        self.server = tk.StringVar(value=self.config.get('server', ''))
        self.qr_server = tk.StringVar(value=self.config.get('qr_server', ''))
        try:
            saved_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ''
        except Exception:
            saved_key = ''
        self.api_key = tk.StringVar(value=saved_key)
        self.spool_number = tk.StringVar()
        saved_format = self.config.get('format', DEFAULT_FORMAT)
        self.format = tk.StringVar(value=saved_format if saved_format in FORMATS else DEFAULT_FORMAT)
        self.status = tk.StringVar(value=tr('Bereit. Spulennummer eingeben.'))
        self.current_image = None
        self.current_spool = None
        self.preview_photo = None
        self.busy = False
        self.jobs = queue.Queue()
        self.closed = False

        # Farben und Schriftbild: ruhige, moderne Windows-Oberflaeche
        root.configure(bg='#f2f5fa')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background='#f2f5fa', foreground='#19283c')
        style.configure('TFrame', background='#f2f5fa')
        style.configure('TLabel', background='#f2f5fa', foreground='#19283c')
        style.configure('TLabelFrame', background='#f2f5fa', bordercolor='#d8e1eb', relief='solid')
        style.configure('TLabelFrame.Label', background='#f2f5fa', foreground='#243b53', font=('Segoe UI', 10, 'bold'))
        style.configure('TEntry', padding=6, fieldbackground='white')
        style.configure('TCombobox', padding=5, fieldbackground='white')
        style.configure('TButton', padding=(12, 8), background='#e2eaf3', foreground='#1c334a', borderwidth=0)
        style.map('TButton', background=[('active', '#d3e1f0'), ('disabled', '#edf1f5')])
        style.configure('Accent.TButton', background='#1769b1', foreground='white', font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#10528e'), ('disabled', '#d8e1eb')], foreground=[('disabled', '#8190a1')])
        root.geometry(self.config.get('geometry', '850x650'))
        root.minsize(740, 590)

        outer = ttk.Frame(root, padding=(22, 16))
        outer.pack(fill='both', expand=True)
        header = ttk.Frame(outer)
        header.pack(fill='x', pady=(0, 12))
        ttk.Label(header, text=tr('BamBuddy Etikettendrucker'), font=('Segoe UI', 20, 'bold')).pack(side='left')
        ttk.Label(header, text='NIIMBOT B1  |  v1.0 Portable', foreground='#61758a').pack(side='right', pady=(10, 0))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x', pady=(0, 14))
        self.print_button = ttk.Button(toolbar, text=tr('Drucken'), style='Accent.TButton', command=self.start_print, state='disabled')
        self.print_button.pack(side='left')
        self.save_button = ttk.Button(toolbar, text=tr('PNG speichern'), command=self.save_png, state='disabled')
        self.save_button.pack(side='left', padx=9)
        ttk.Label(toolbar, text='Language / Sprache').pack(side='right', padx=(6, 0))
        self.language = tk.StringVar(value=self.config.get('language', 'de'))
        self.language_combo = ttk.Combobox(toolbar, textvariable=self.language, values=['de', 'en'], state='readonly', width=5)
        self.language_combo.pack(side='right')
        self.language_combo.bind('<<ComboboxSelected>>', self.change_language)
        ttk.Button(toolbar, text='About / Über', command=self.show_about).pack(side='right', padx=(8, 0))
        ttk.Button(toolbar, text=tr('Einstellungen zurücksetzen'), command=self.reset_settings).pack(side='right', padx=(8, 0))

        connection = ttk.LabelFrame(outer, text=tr('BamBuddy-Verbindung'), padding=12)
        connection.pack(fill='x')
        connection.columnconfigure(1, weight=1)
        ttk.Label(connection, text=tr('BamBuddy-Server')).grid(row=0, column=0, sticky='w', pady=4)
        server_entry = ttk.Entry(connection, textvariable=self.server)
        server_entry.grid(row=0, column=1, sticky='ew', padx=(12, 4), pady=4)
        self.add_hint(server_entry, self.server, tr('z. B. http://192.168.1.100:8000'))
        ttk.Label(connection, text=tr('Link für QR-Code')).grid(row=1, column=0, sticky='w', pady=4)
        qr_entry = ttk.Entry(connection, textvariable=self.qr_server)
        qr_entry.grid(row=1, column=1, sticky='ew', padx=(12, 4), pady=4)
        self.add_hint(qr_entry, self.qr_server, tr('z. B. https://meine-bambuddy-domain.de'))
        ttk.Label(connection, text='API-Key').grid(row=2, column=0, sticky='w', pady=4)
        ttk.Entry(connection, textvariable=self.api_key, show='●').grid(row=2, column=1, sticky='ew', padx=(12, 4), pady=4)
        ttk.Button(connection, text=tr('Speichern'), command=self.save_settings).grid(row=2, column=2, padx=(8, 0))
        ttk.Label(connection, text=tr('QR-Link: öffnet beim Scannen die Spule im Browser. Beide Adressen werden lokal gespeichert.'), foreground='#64748b').grid(row=3, column=1, columnspan=2, sticky='w', padx=(12, 0), pady=(4, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill='x', pady=(16, 12))
        ttk.Label(controls, text=tr('Spulennummer')).pack(side='left')
        self.number_entry = ttk.Entry(controls, textvariable=self.spool_number, width=9, font=('Segoe UI', 12))
        self.number_entry.pack(side='left', padx=(10, 8))
        self.load_button = ttk.Button(controls, text=tr('Spule laden'), style='Accent.TButton', command=self.load_spool)
        self.load_button.pack(side='left')
        ttk.Label(controls, text=tr('Etikettengröße')).pack(side='left', padx=(26, 9))
        self.size_combo = ttk.Combobox(controls, textvariable=self.format, values=list(FORMATS), state='readonly', width=21)
        self.size_combo.pack(side='left')
        self.size_combo.bind('<<ComboboxSelected>>', self.change_format)
        self.number_entry.bind('<Return>', lambda _event: self.load_spool())

        preview_frame = ttk.LabelFrame(outer, text=tr('Etikettenvorschau'), padding=10)
        preview_frame.pack(fill='both', expand=True)
        self.preview = ttk.Label(preview_frame, text=tr('Spulennummer eingeben und auf „Spule laden“ klicken.'), anchor='center')
        self.preview.pack(expand=True)
        self.info = ttk.Label(outer, text='', foreground='#4b6176')
        self.info.pack(anchor='w', pady=(8, 4))
        ttk.Separator(outer).pack(fill='x', pady=5)
        ttk.Label(outer, textvariable=self.status, foreground='#50677d', wraplength=790).pack(anchor='w', pady=(5, 0))
        self.number_entry.focus_set()
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.poll_jobs()

    @staticmethod
    def add_hint(entry, variable, example):
        # Der Beispieltext liegt ueber dem leeren Eingabefeld und wird nie als Wert gespeichert.
        hint = tk.Label(entry, text=example, fg='#8794a5', bg='white',
                        font=('Segoe UI', 9), anchor='w', cursor='xterm')
        hint.place(x=8, rely=0.5, anchor='w')
        def refresh(*_args):
            if variable.get().strip() or entry.focus_get() == entry:
                hint.place_forget()
            else:
                hint.place(x=8, rely=0.5, anchor='w')
        hint.bind('<Button-1>', lambda _event: entry.focus_set())
        entry.bind('<FocusIn>', refresh, add='+')
        entry.bind('<FocusOut>', refresh, add='+')
        variable.trace_add('write', refresh)
        refresh()

    def show_about(self):
        messagebox.showinfo('BamBuddy Label Printer 1.0',
            'BamBuddy Label Printer 1.0\nNIIMBOT B1 · Windows\n\n'
            'Independent open-source community project.\n'
            'Developed with programming assistance from ChatGPT by OpenAI.\n'
            'Not affiliated with BamBuddy, NIIMBOT or OpenAI.')

    def change_language(self, _event=None):
        self.config['language'] = self.language.get()
        try:
            self.persist_settings(require_all=False)
        except Exception:
            pass
        self.rebuild_ui()

    def rebuild_ui(self):
        # Alte Queue-Abfrage beenden, bevor eine neue App-Instanz startet.
        self.closed = True
        for child in self.root.winfo_children():
            child.destroy()
        App(self.root)

    def reset_settings(self):
        if self.busy:
            messagebox.showwarning(tr('Einstellungen'), tr('Bitte warten, bis der Vorgang abgeschlossen ist.'))
            return
        if not messagebox.askyesno(
            tr('Einstellungen zurücksetzen'),
            tr('Alle gespeicherten Verbindungsdaten, der API-Key und die Einstellungen werden gelöscht. Gespeicherte PNG-Dateien bleiben erhalten. Fortfahren?'),
            parent=self.root,
        ):
            return
        try:
            # Keyring zuerst löschen: bei Fehler darf kein scheinbar erfolgreicher Reset erfolgen.
            try:
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
            except keyring.errors.PasswordDeleteError:
                pass  # Kein Eintrag vorhanden.
            CONFIG_FILE.unlink(missing_ok=True)
        except Exception as exc:
            messagebox.showerror(tr('Einstellungen'), str(exc), parent=self.root)
            return
        # Die alte App-Instanz darf die gelöschten Werte nicht beim Schließen speichern.
        self.rebuild_ui()
        self.status.set(tr('Einstellungen wurden zurückgesetzt.'))

    def persist_settings(self, require_all=False):
        server_raw = self.server.get().strip()
        qr_raw = self.qr_server.get().strip()
        key = self.api_key.get().strip()
        if require_all and not (server_raw and qr_raw and key):
            raise ValueError(tr('Bitte BamBuddy-Server, Link für QR-Code und API-Key eingeben.'))
        # Nur gueltige, vollstaendige Adressen sichern.
        if server_raw:
            self.config['server'] = normalize_url(server_raw)
        if qr_raw:
            self.config['qr_server'] = normalize_url(qr_raw)
        self.config['format'] = self.format.get()
        self.config['language'] = self.language.get()
        self.config['geometry'] = self.root.geometry()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self.config, indent=2, ensure_ascii=False), encoding='utf-8')
        if key:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)

    @staticmethod
    def read_config():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def save_settings(self):
        try:
            self.persist_settings(require_all=True)
            self.status.set(tr('Serveradressen und API-Key dauerhaft gespeichert.'))
            self.invalidate_label()
        except Exception as exc:
            messagebox.showerror(tr('Einstellungen'), str(exc))

    def invalidate_label(self):
        self.current_image = None
        self.current_spool = None
        self.preview_photo = None
        self.preview.configure(image='', text=tr('Bitte Spule erneut laden.'))
        self.info.configure(text='')
        self.set_busy(self.busy)

    def set_busy(self, busy):
        self.busy = busy
        self.load_button.configure(state='disabled' if busy else 'normal')
        self.size_combo.configure(state='disabled' if busy else 'readonly')
        state = 'normal' if not busy and self.current_image is not None else 'disabled'
        self.print_button.configure(state=state)
        self.save_button.configure(state=state)

    def run_async(self, work, finished):
        self.set_busy(True)
        def runner():
            try:
                self.jobs.put((finished, work(), None))
            except Exception as exc:
                self.jobs.put((finished, None, exc))
        threading.Thread(target=runner, daemon=True).start()

    def poll_jobs(self):
        if self.closed:
            return
        try:
            while True:
                finished, result, error = self.jobs.get_nowait()
                finished(result, error)
        except queue.Empty:
            pass
        self.root.after(80, self.poll_jobs)

    def change_format(self, _event=None):
        if self.busy:
            return
        if self.current_spool is not None:
            try:
                self.current_image = render_label(self.current_spool, self.qr_server.get(), self.format.get())
                self.show_preview()
            except Exception as exc:
                self.invalidate_label()
                messagebox.showerror(tr('Etikettenformat'), str(exc))
        if self.format.get() != DEFAULT_FORMAT:
            self.status.set(tr('Testformat: Druckgröße und QR-Code bitte vor Nutzung prüfen.'))

    def show_preview(self):
        if self.current_image is None:
            return
        width = 245
        height = max(1, round(self.current_image.height * width / self.current_image.width))
        self.preview_photo = ImageTk.PhotoImage(self.current_image.resize((width, height), Image.Resampling.NEAREST))
        self.preview.configure(image=self.preview_photo, text='')

    def load_spool(self):
        if self.busy:
            return
        number = self.spool_number.get().strip()
        if not number.isdigit() or int(number) <= 0:
            messagebox.showwarning(tr('Spulennummer'), tr('Bitte eine gültige Spulennummer eingeben.'))
            return
        key = self.api_key.get().strip()
        if not key:
            messagebox.showwarning('API-Key', tr('Bitte den BamBuddy-API-Key eingeben.'))
            return
        try:
            server = normalize_url(self.server.get())
            qr_base = normalize_url(self.qr_server.get())
        except ValueError as exc:
            messagebox.showerror(tr('Serveradresse'), str(exc))
            return
        fmt = self.format.get()
        try:
            # Auch beim Laden automatisch sichern, selbst ohne Klick auf Speichern.
            self.persist_settings(require_all=True)
        except Exception as exc:
            messagebox.showerror('Einstellungen speichern', str(exc))
            return
        self.invalidate_label()
        self.preview.configure(text=tr('Lade Spule ...'))
        self.status.set(tr('Rufe BamBuddy-Daten ab ...'))
        def work():
            spool = fetch_spool(number, key, server)
            return (spool, render_label(spool, qr_base, fmt)) if spool else (None, None)
        self.run_async(work, self.loaded)

    def loaded(self, result, error):
        self.set_busy(False)
        if error:
            self.preview.configure(text=tr('Keine Vorschau verfügbar.'))
            self.status.set(tr('Fehler beim Abrufen.'))
            messagebox.showerror('BamBuddy', str(error))
            return
        spool, image = result
        if spool is None:
            self.preview.configure(text=tr('Spule nicht gefunden.'))
            self.status.set(tr('Spule nicht gefunden.'))
            return
        self.current_spool, self.current_image = spool, image
        self.show_preview()
        material = str(spool.get('material') or '-')
        if spool.get('subtype'):
            material += ' ' + str(spool['subtype'])
        self.info.configure(text=f"Spule #{spool['id']} · {material} · {spool.get('color_name') or '-'}")
        self.status.set(tr('Spule geladen. Druck bereit.'))
        self.set_busy(False)

    def save_png(self):
        if self.current_image is None:
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        suggested = f"etikett_spule_{self.current_spool['id']}.png"
        path = filedialog.asksaveasfilename(title=tr('Etikett als PNG speichern'), initialdir=str(OUTPUT_DIR),
                                            initialfile=suggested, defaultextension='.png',
                                            filetypes=[(tr('PNG-Bild'), '*.png')])
        if path:
            try:
                self.current_image.save(path)
                self.status.set(f'PNG gespeichert: {path}')
            except Exception as exc:
                messagebox.showerror(tr('PNG speichern'), str(exc))

    def start_print(self):
        if self.busy or self.current_image is None:
            return
        if self.format.get() != DEFAULT_FORMAT:
            if not messagebox.askyesno(tr('Testformat'), tr('Dieses Format wurde auf dem NIIMBOT B1 noch nicht getestet. Trotzdem drucken?')):
                return
        image = self.current_image.copy()
        self.status.set(tr('Verbinde mit NIIMBOT B1 und drucke ...'))
        self.run_async(lambda: print_label(image), self.printed)

    def printed(self, result, error):
        self.set_busy(False)
        if error:
            self.status.set(tr('Druck fehlgeschlagen.'))
            messagebox.showerror(tr('Druckfehler'), str(error))
        elif result:
            self.status.set(tr('Druck erfolgreich abgeschlossen.'))
            messagebox.showinfo('NIIMBOT B1', tr('Etikett gedruckt!'))
        else:
            self.status.set(tr('Druck nicht bestätigt. Bitte Etikett prüfen.'))

    def on_close(self):
        self.closed = True
        try:
            self.persist_settings(require_all=False)
        except Exception:
            # Ungueltige ungespeicherte Eingaben nicht in die Konfiguration schreiben.
            pass
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
