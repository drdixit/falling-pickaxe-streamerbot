# Project Starting Guide
Always follow these steps to start and run the application.

## 1. Remove System Aliases

Windows often sets system-wide execution aliases for Python that can interfere with running the correct version. If you experience issues, run these commands in PowerShell first:

```powershell
Remove-Item Alias:python
Remove-Item Alias:python3
```

## 2. Environment Setup (One-time)

This project uses Python 3.11. To install the virtual environment, run:

```powershell
python3.11 -m venv .venv
```

## 3. Activate the Environment

You must activate the virtual environment **for each new terminal session** before running the app:

```powershell
.\.venv\Scripts\activate
```

## 4. Run the Application

Once the environment is activated, the app is ready to run:

```powershell
python ./src/main.py
```
