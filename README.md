# Academic Paraphraser

Full-stack app: **React + Vite + TypeScript + Tailwind** (frontend) and **Python + FastAPI** (backend). The browser UI calls the backend through a dev proxy (`/api` → `http://localhost:8000`). Paraphrasing and streaming happen on the server.

This README explains how to run the project on **another computer** from a clean copy (USB, zip, or `git clone`).

---

## How running the app works (read this first)

You need **two terminals** open at the same time:

| Terminal | Folder        | What it runs                         | Typical URL / port   |
| -------- | ------------- | ------------------------------------ | -------------------- |
| **1**    | `backend/`    | Python API (FastAPI + pipeline)      | `http://localhost:8000` |
| **2**    | project root  | Vite dev server (React UI)           | `http://localhost:5173` (or next free port) |

**Order:** Start **backend** first (or at least before you click **Paraphrase**). Then start **frontend** and open the Local URL Vite prints.

---

## Part A — Install system software (once per computer)

### A1. Node.js (frontend)

1. Download **LTS** from [https://nodejs.org/](https://nodejs.org/) and install.
2. On Windows, restart the terminal (or sign out/in) after install.
3. Check:

```bash
node -v
npm -v
```

You should see a **Node** version (e.g. v20.x or v22.x) and an **npm** version.

### A2. Python (backend)

1. Download **Python 3.10 or newer** (3.11 is a good choice) from [https://www.python.org/downloads/](https://www.python.org/downloads/).
2. On **Windows**, during setup, check **“Add python.exe to PATH”**, then install.
3. Check:

**Windows (PowerShell or CMD):**

```powershell
python --version
```

**macOS / Linux:**

```bash
python3 --version
```

### A3. Disk space and network

- Reserve **about 3 GB free** on the drive where you create the Python `venv` and install packages (PyTorch and related libraries are large).
- First `pip install` may take **15–40+ minutes** depending on CPU and disk.
- The app needs **internet** for `pip install`, Hugging Face model cache, and OpenAI API calls when paraphrasing.

### A4. OpenAI API key

You need an **OpenAI API key** with access to the models your backend uses (see `backend` code — typically GPT‑4o family). You will paste it into `backend/.env` in a later step. **Never** share that key in chat or commit it to a public repo.

---

## Part B — Get the project onto the computer

### B1. Copy or clone

Use **one** of these:

- **Git:** `git clone <your-repo-url>` then `cd` into the repo folder.
- **Zip / USB:** unzip so you have a single folder that contains **`package.json`** at the top level and a **`backend`** subfolder.

### B2. Confirm folder layout

Open the project root. You should see **at least**:

```text
package.json
package-lock.json
vite.config.ts
index.html
src/
public/
backend/
  server.py
  requirements.txt
  main.py
  pipeline.py
  ...
```

If `package.json` or `backend/requirements.txt` is missing, the copy is incomplete.

---

## Part C — Frontend setup (project root)

All commands below use **the folder that contains `package.json`** (project root).

### C1. Open a terminal in the project root

**Windows (PowerShell):** use File Explorer → open your project folder → address bar → type `powershell` Enter, or:

```powershell
cd "D:\path\to\Acedemic Ai Para Tool"
```

(Replace with your real path.)

### C2. Install JavaScript dependencies

```bash
npm install
```

Wait until it finishes **without errors**. This creates **`node_modules/`** (do not upload that folder to GitHub; it is regenerated with `npm install`).

### C3. (Optional) Verify TypeScript

```bash
npm run typecheck
```

---

## Part D — Backend setup (`backend` folder)

### D1. Open a terminal in `backend`

**Windows (PowerShell):**

```powershell
cd "D:\path\to\Acedemic Ai Para Tool\backend"
```

### D2. Create a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv venv
```

**macOS / Linux:**

```bash
python3 -m venv venv
```

This creates a folder **`backend/venv`**. It is local to this machine; do not commit it to Git.

### D3. Activate the virtual environment

**Windows — PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

If you see an error about **execution policy**, run once for your user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try `.\venv\Scripts\Activate.ps1` again.

**Windows — Command Prompt (CMD):**

```cmd
cd D:\path\to\Acedemic Ai Para Tool\backend
venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

When activation works, your prompt usually shows **`(venv)`** at the beginning.

### D4. Upgrade pip (recommended, once per venv)

```bash
python -m pip install --upgrade pip
```

### D5. Install Python dependencies

With **`(venv)`** active and still inside **`backend/`**:

```bash
pip install -r requirements.txt
```

- This can take a long time the first time.
- If you see **“No space left on device”**, free several gigabytes and run the same command again.

### D6. Create the `.env` file with your API key

Still in **`backend/`**, create a new file named **`.env`** (note the leading dot on Windows you may need to name it `.env.` in Explorer or use an editor).

Put exactly this line (replace with your real key):

```env
OPENAI_API_KEY=sk-your-actual-key-here
```

Save the file as **`backend/.env`**.

If the repo includes **`backend/.env.example`**, you can copy it to `.env` and edit the key line.

**Security:** Do not email or commit `.env`. Each machine should have its own copy.

---

## Part E — Run the backend (Terminal 1)

1. Open a terminal.
2. `cd` into **`backend`**.
3. Activate the venv (same commands as **D3**).
4. Run:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### What “good” looks like

- You should see Uvicorn listening on **`http://0.0.0.0:8000`** (same as localhost from this PC).
- The **first** run may print model-loading messages; wait until the server is ready.

### Health check

In a browser on **this** computer, open:

```text
http://localhost:8000/api/health
```

You want JSON including **`"status":"ok"`** and **`"pipeline_loaded":true`**. If `pipeline_loaded` stays false, check `.env` and the terminal for errors.

**Leave this terminal running** while you use the website.

---

## Part F — Run the frontend (Terminal 2)

1. Open a **second** terminal (keep Terminal 1 running).
2. `cd` to the **project root** (where `package.json` is — **not** `backend`).
3. Run:

```bash
npm run dev
```

### Open the app

Vite prints a line like:

```text
➜  Local:   http://localhost:5173/
```

- Open that **exact** URL in Chrome, Edge, or Firefox.
- If port **5173** is busy, Vite may use **5174**, **5175**, etc. **Always use the URL from the terminal**, not an old bookmark.

### Proxy (why localhost is enough)

`vite.config.ts` proxies **`/api`** to **`http://localhost:8000`**. So the browser only talks to the Vite dev server; Vite forwards API calls to the backend. **The backend must still be running on port 8000** on the same PC for Paraphrase to work.

---

## Part G — Use the app

1. Confirm **Terminal 1**: backend running, health URL OK.  
2. Confirm **Terminal 2**: `npm run dev` running; browser on the Local URL.  
3. In the UI: paste text, set tone / humanization / protected terms, click **Paraphrase**.  
4. Text should **stream** into the output panel; a **progress** indicator shows while chunks are processing.

---

## Part H — Same Wi‑Fi (phone or second PC)

**Frontend on the LAN:**

From project root:

```bash
npm run dev -- --host
```

Use the **Network** URL Vite prints. You may need to allow the port in **Windows Firewall**.

**Backend from another device** is more involved: the default proxy targets **localhost**. For LAN-only demos, the usual approach is to run both on one PC and use `--host` only for the UI, or deploy backend and frontend with proper URLs. For day‑to‑day development, run both on one machine.

---

## Part I — Optional: production-style frontend build

From project root:

```bash
npm run build
npm run preview
```

`preview` serves the built files from `dist/`. That flow does **not** include the Python backend; you still need the API running separately (or a proper deployment) for paraphrasing.

---

## Reference commands

| Location     | Command |
| ------------ | ------- |
| Project root | `npm install` |
| Project root | `npm run dev` |
| Project root | `npm run build` |
| Project root | `npm run preview` |
| Project root | `npm run typecheck` |
| `backend/` (venv on) | `uvicorn server:app --host 0.0.0.0 --port 8000` |

---

## Troubleshooting

| Symptom | What to check |
| ------- | ------------- |
| “Cannot find module” / `npm` not found | Node.js not installed or terminal not restarted after install. |
| `python` not found (Windows) | Reinstall Python with **Add to PATH**, or use **Python Launcher** `py -m venv venv`. |
| `pip install` disk error | Free **3+ GB**; delete partial `venv` and recreate from **D2**. |
| Paraphrase error in the UI | Backend running? `http://localhost:8000/api/health` OK? `.env` key set? |
| Port 8000 already in use | Stop the other app using 8000, or change uvicorn port **and** `vite.config.ts` `server.proxy["/api"].target` to match. |
| Wrong Vite port | Use the **Local** URL from the **current** `npm run dev` output. |
| Antivirus / corporate proxy | May block pip or model download; try another network or allowlist tools. |

---

## Checklist — another computer (quick)

1. Install **Node.js LTS** and **Python 3.10+** (PATH on Windows).  
2. Copy project so **`package.json`** and **`backend/requirements.txt`** exist.  
3. **Root:** `npm install`.  
4. **`backend`:** `python -m venv venv` → activate → `pip install -r requirements.txt`.  
5. **`backend/.env`** with `OPENAI_API_KEY=...`.  
6. **Terminal A (`backend`, venv on):** `uvicorn server:app --host 0.0.0.0 --port 8000`.  
7. **Terminal B (root):** `npm run dev` → open **Local** URL → use **Paraphrase**.
