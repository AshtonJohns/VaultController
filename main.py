from __future__ import annotations

import os
import string
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


CONFIG_PATH = Path(r"C:\Users\ashto\OneDrive\Personal Vault\veracrypt_vaultcontroller.yaml")
VERACRYPT_PATHS = (
    Path(r"C:\Program Files\VeraCrypt\VeraCrypt.exe"),
    Path(r"C:\Program Files (x86)\VeraCrypt\VeraCrypt.exe"),
)
def find_veracrypt() -> Path | None:
    for candidate in VERACRYPT_PATHS:
        if candidate.exists():
            return candidate
    return None


def read_config() -> tuple[list[tuple[str, str]], str | None]:
    try:
        raw_text = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], f"Config file not found:\n{CONFIG_PATH}"
    except PermissionError:
        return [], (
            "Config file is inaccessible.\n\n"
            "If your OneDrive Personal Vault is locked, unlock it first and try again."
        )
    except OSError as exc:
        return [], f"Could not read config file:\n{exc}"

    entries: list[tuple[str, str]] = []
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        separator_index = _find_mapping_separator(stripped)
        if separator_index is None:
            return [], (
                "Invalid config format on line "
                f"{line_number}.\n\nExpected a YAML-style entry like:\nF:/path/to/container.hc: mypassword"
            )

        container_path = _clean_yaml_token(stripped[:separator_index])
        password = _clean_yaml_token(stripped[separator_index + 1 :])

        if not container_path:
            return [], f"Missing container path on line {line_number}."

        entries.append((container_path, password))

    if not entries:
        return [], (
            "No vault entries were found.\n\n"
            "Add lines like:\nF:/path/to/container.hc: mypassword"
        )

    return entries, None


def _find_mapping_separator(line: str) -> int | None:
    in_single_quote = False
    in_double_quote = False

    for index, char in enumerate(line):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue

        if char != ":" or in_single_quote or in_double_quote:
            continue

        previous_char = line[index - 1] if index > 0 else ""
        next_char = line[index + 1] if index + 1 < len(line) else ""

        # Skip the drive-letter colon in paths like F:/vault.hc.
        if previous_char.isalpha() and next_char in ("\\", "/"):
            continue

        return index

    return None


def _clean_yaml_token(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def available_drive_letters() -> list[str]:
    used_letters = {
        Path(drive).drive[:1].upper()
        for drive in [f"{letter}:\\" for letter in string.ascii_uppercase]
        if os.path.exists(drive)
    }
    return [letter for letter in string.ascii_uppercase if letter not in used_letters]


class VaultControllerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("VeraCrypt Vault Controller")
        self.root.resizable(False, False)

        self.veracrypt_path = find_veracrypt()
        self.entries: list[tuple[str, str]] = []
        self.mounted_entries: list[tuple[str, str]] = []
        self.selected_container = tk.StringVar()
        self.selected_drive = tk.StringVar()
        self.status_text = tk.StringVar(value="Loading configuration...")

        self.build_ui()
        self.refresh_entries()

    def build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Vault").grid(row=0, column=0, sticky="w")
        self.vault_combo = ttk.Combobox(
            frame,
            textvariable=self.selected_container,
            state="readonly",
            width=60,
        )
        self.vault_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))

        ttk.Label(frame, text="Drive letter").grid(row=2, column=0, sticky="w")
        self.drive_combo = ttk.Combobox(
            frame,
            textvariable=self.selected_drive,
            state="readonly",
            width=8,
        )
        self.drive_combo.grid(row=3, column=0, sticky="w", pady=(4, 12))

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=2, sticky="ew")

        ttk.Button(button_row, text="Refresh", command=self.refresh_entries).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(button_row, text="Mount", command=self.mount_selected).grid(
            row=0, column=1
        )

        ttk.Label(frame, text="Mounted this session").grid(row=5, column=0, sticky="w", pady=(16, 4))
        self.mounted_list = tk.Listbox(frame, height=6, width=60, exportselection=False)
        self.mounted_list.grid(row=6, column=0, columnspan=2, sticky="ew")

        ttk.Button(frame, text="Unmount Selected", command=self.unmount_selected).grid(
            row=7, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Button(frame, text="Open Mounted Folder", command=self.open_selected_mount).grid(
            row=7, column=1, sticky="e", pady=(8, 0)
        )

        status_label = ttk.Label(
            frame,
            textvariable=self.status_text,
            foreground="steelblue",
            justify="left",
            wraplength=440,
        )
        status_label.grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def refresh_entries(self) -> None:
        self.entries, error = read_config()

        drive_values = available_drive_letters()
        self.drive_combo["values"] = drive_values
        if drive_values:
            preferred = self.selected_drive.get().rstrip(":").upper()
            self.selected_drive.set(preferred if preferred in drive_values else drive_values[0])
        else:
            self.selected_drive.set("")

        if error:
            self.vault_combo["values"] = []
            self.selected_container.set("")
            self.status_text.set(error)
            return

        container_paths = [container for container, _ in self.entries]
        self.vault_combo["values"] = container_paths
        if container_paths:
            current = self.selected_container.get()
            self.selected_container.set(current if current in container_paths else container_paths[0])

        veracrypt_message = (
            f"Ready. Loaded {len(self.entries)} vault entr"
            f"{'y' if len(self.entries) == 1 else 'ies'} from:\n{CONFIG_PATH}"
        )
        if not self.veracrypt_path:
            veracrypt_message += "\n\nVeraCrypt.exe was not found in the default install location."
        self.status_text.set(veracrypt_message)
        self.refresh_mounted_list()

    def refresh_mounted_list(self) -> None:
        selected_index = self.mounted_list.curselection()
        self.mounted_list.delete(0, tk.END)

        for drive_letter, container_path in self.mounted_entries:
            self.mounted_list.insert(tk.END, f"{drive_letter}:  {container_path}")

        if selected_index and selected_index[0] < len(self.mounted_entries):
            self.mounted_list.selection_set(selected_index[0])

    def remember_mount(self, drive_letter: str, container_path: str) -> None:
        normalized_drive = drive_letter.rstrip(":").upper()
        self.mounted_entries = [
            (existing_drive, existing_path)
            for existing_drive, existing_path in self.mounted_entries
            if existing_drive != normalized_drive and existing_path != container_path
        ]
        self.mounted_entries.append((normalized_drive, container_path))
        self.mounted_entries.sort(key=lambda item: item[0])
        self.refresh_mounted_list()

    def forget_mount(self, drive_letter: str) -> None:
        normalized_drive = drive_letter.rstrip(":").upper()
        self.mounted_entries = [
            (existing_drive, existing_path)
            for existing_drive, existing_path in self.mounted_entries
            if existing_drive != normalized_drive
        ]
        self.refresh_mounted_list()

    def mount_selected(self) -> None:
        if not self.veracrypt_path:
            messagebox.showerror(
                "VeraCrypt Not Found",
                "VeraCrypt.exe was not found.\n\nInstall VeraCrypt or update VERACRYPT_PATHS in main.py.",
            )
            return

        container_path = self.selected_container.get()
        drive_letter = self.selected_drive.get().rstrip(":").upper()

        if not container_path:
            messagebox.showerror("No Vault Selected", "Choose a vault entry first.")
            return

        if not drive_letter:
            messagebox.showerror("No Drive Letter", "Choose an available drive letter first.")
            return

        password = next(
            (stored_password for path, stored_password in self.entries if path == container_path),
            None,
        )
        if password is None:
            messagebox.showerror("Missing Password", "The selected vault entry could not be resolved.")
            return

        if not Path(container_path).exists():
            messagebox.showerror(
                "Container Not Found",
                f"The container file does not exist or is inaccessible:\n{container_path}",
            )
            return

        command = [
            str(self.veracrypt_path),
            "/v",
            container_path,
            "/l",
            drive_letter,
            "/p",
            password,
            "/q",
            "/s",
        ]

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            messagebox.showerror("Launch Failed", f"Could not start VeraCrypt:\n{exc}")
            return

        if completed.returncode == 0:
            self.remember_mount(drive_letter, container_path)
            self.refresh_entries()
            self.status_text.set(f"Mounted {container_path} to {drive_letter}:")
            messagebox.showinfo("Mounted", f"Mounted to drive {drive_letter}:")
            return

        error_text = completed.stderr.strip() or completed.stdout.strip() or "Unknown VeraCrypt error."
        messagebox.showerror("Mount Failed", error_text)
        self.status_text.set(f"Mount failed for {container_path}")

    def unmount_selected(self) -> None:
        if not self.veracrypt_path:
            messagebox.showerror(
                "VeraCrypt Not Found",
                "VeraCrypt.exe was not found.\n\nInstall VeraCrypt or update VERACRYPT_PATHS in main.py.",
            )
            return

        selection = self.mounted_list.curselection()
        if not selection:
            messagebox.showerror("No Mounted Vault Selected", "Choose a mounted vault from the list first.")
            return

        drive_letter, container_path = self.mounted_entries[selection[0]]
        command = [
            str(self.veracrypt_path),
            "/q",
            "/s",
            "/d",
            drive_letter,
        ]

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            messagebox.showerror("Launch Failed", f"Could not start VeraCrypt:\n{exc}")
            return

        if completed.returncode == 0:
            self.forget_mount(drive_letter)
            self.refresh_entries()
            self.status_text.set(f"Unmounted {container_path} from {drive_letter}:")
            messagebox.showinfo("Unmounted", f"Unmounted drive {drive_letter}:")
            return

        error_text = completed.stderr.strip() or completed.stdout.strip() or "Unknown VeraCrypt error."
        messagebox.showerror("Unmount Failed", error_text)
        self.status_text.set(f"Unmount failed for {drive_letter}:")

    def open_selected_mount(self) -> None:
        selection = self.mounted_list.curselection()
        if not selection:
            messagebox.showerror("No Mounted Vault Selected", "Choose a mounted vault from the list first.")
            return

        drive_letter, _container_path = self.mounted_entries[selection[0]]
        mount_path = f"{drive_letter}:\\"

        if not os.path.exists(mount_path):
            messagebox.showerror(
                "Mount Not Available",
                f"The mounted drive is no longer accessible:\n{mount_path}",
            )
            self.forget_mount(drive_letter)
            self.refresh_entries()
            return

        try:
            os.startfile(mount_path)
        except OSError as exc:
            messagebox.showerror("Open Failed", f"Could not open mounted folder:\n{exc}")
            return

        self.status_text.set(f"Opened mounted folder {mount_path}")


def main() -> None:
    root = tk.Tk()
    app = VaultControllerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
