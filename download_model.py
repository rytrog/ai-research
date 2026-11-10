import os
import sys
import time
from huggingface_hub import hf_hub_download

TARGET_DIR = r"L:\New_AI_BACKUP\AI_RESEARCH\Qwen3-Embedding-0.6B"
REPO_ID = "Qwen/Qwen3-Embedding-0.6B"
FILENAME = "model.safetensors"

print(f"Downloading {FILENAME} from {REPO_ID} to {TARGET_DIR}...")
start_time = time.time()

try:
    file_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=TARGET_DIR,
        force_download=True,
    )
    elapsed = time.time() - start_time
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"\nSUCCESS: Downloaded {FILENAME} ({size_mb:.2f} MB) in {elapsed:.1f}s")
    print(f"Saved at: {file_path}")
except Exception as e:
    print(f"\nERROR: Download failed: {e}", file=sys.stderr)
    sys.exit(1)
