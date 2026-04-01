# VaultController

Small Tkinter GUI for mounting and unmounting VeraCrypt containers from a YAML file stored in OneDrive Personal Vault.

## Run

```powershell
python main.py
```

## Config Format

The app reads:

`C:\Users\ashto\OneDrive\Personal Vault\veracrypt_vaultcontroller.yaml`

Use simple YAML-style entries:

```yaml
F:/path/to/container.hc: mypassword
G:/another/container.hc: anotherpassword
```

If OneDrive Personal Vault is locked, the app will show an inaccessible-file message.

## Build EXE

From the project folder:

```powershell
.\build.ps1
```

That script will:

1. install the optional PyInstaller build dependency with `uv`
2. create a windowed one-file executable with PyInstaller

The built executable will be written to `dist\VaultController.exe`.
