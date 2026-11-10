# Launch the unchanged production application

These commands use the environments already installed for this project. No installation or package update is required by this experiment. Production remains the original model at threshold **0.42**. Do not point the app at an experimental checkpoint without separate explicit integration approval.

If the application is already running, use its current endpoints instead of starting duplicate servers. Stop only a server you started, with Ctrl+C in its own terminal.

## Backend: Windows PowerShell, then WSL

```powershell
wsl.exe -d Ubuntu-24.04
```

Inside the WSL terminal:

```bash
cd /mnt/c/Users/mohda/OneDrive/Desktop/Deepfake-Image-Detection
source /home/mohdaafras/deeptrace-env/tf-gpu/bin/activate
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_NUM_INTRAOP_THREADS=4
export TF_NUM_INTEROP_THREADS=1
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8002
```

## Frontend: separate Windows PowerShell terminal

```powershell
Set-Location "C:\Users\mohda\OneDrive\Desktop\Deepfake-Image-Detection\deeptrace-ai---deepfake-image-detection-&-forensics"
npm run dev
```

## Check and open

```powershell
curl.exe --fail http://127.0.0.1:8002/api/v1/health
```

- Frontend: http://127.0.0.1:5173
- Backend: http://127.0.0.1:8002
- Swagger: http://127.0.0.1:8002/docs

For a legitimately labeled, permitted image you supply:

```powershell
curl.exe --fail-with-body -X POST http://127.0.0.1:8002/api/v1/predict -F "file=@C:\path\to\your-image.jpg"
```

That prediction writes an application history record. The placeholder path above is **not** a supplied demo image. No independently qualified demonstration filenames are currently available. Do not use training/validation samples or the old frozen test as a substitute for the requested independent pack.

## Experiment replay safety

The recorded experiment is under:

```text
/home/mohdaafras/deeptrace-experiments/final-model-correction-20261110-001/
```

Preparation and worker runners refuse existing output files/directories. Do **not** replay them into that run or invoke the legacy all-split evaluation CLI. A new reproduction requires a new run ID, the same approved source hashes, an explicitly reviewed configuration and a fresh output lock. The worker self-test performs no inference and can be run separately:

```bash
/usr/bin/python3 -I -B -S /home/mohdaafras/deeptrace-experiments/final-model-correction-20261110-001/validation_worker.py --self-test
```

The experiment does not train a new model or modify the decision threshold. It compares saved checkpoints on already-used validation data and cannot establish independent generalization.
