# Deep Lake → AWS S3 Sync Plan

**Goal:** Keep your dataset local as source of truth, with one-way sync (including deltas) to an S3 bucket. Prevent data loss by always creating a full backup before any sync.

---

## 1. AWS setup (one-time)

### 1.1 Credentials (you already have them)

- **Location:** `~/.aws/credentials` and `~/.aws/config`
- **Usage:** The sync script and Deep Lake will use the **default** AWS credential chain:
  1. Env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
  2. If not set, **`~/.aws/credentials`** is read automatically (by `boto3` / AWS CLI / Deep Lake)

No need to copy credentials into the repo; point the script at your local dataset and S3 path.

### 1.2 S3 bucket

1. In AWS Console: **S3 → Create bucket** (e.g. `my-deeplake-rag`).
2. **Region:** Prefer `us-east-1` (good for Cursor/LLM latency; optional).
3. **Block all public access:** Leave ON.
4. **Bucket policy:** Not required if you use IAM user/keys that have access only to this bucket (recommended).

### 1.3 IAM (recommended: dedicated user for sync)

1. **IAM → Users → Create user** (e.g. `deeplake-sync`).
2. **Attach policy** (replace `BUCKET_NAME`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::BUCKET_NAME"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:PutObjectAcl"
      ],
      "Resource": ["arn:aws:s3:::BUCKET_NAME/*"]
    }
  ]
}
```

3. Create **Access key** for this user; put keys in `~/.aws/credentials` under a profile (e.g. `[deeplake-sync]`) or as default.

---

## 2. Your current Deep Lake usage

- **Local dataset:** You add/update data locally (path is wherever your Deep Lake RAG MCP points, e.g. a path under your home or project).
- **Sync direction:** Local → S3 only (one-way). No pull from S3 into local in this flow.

---

## 3. Workflow: backup → copy/sync (no data loss)

Before **any** upload to S3 we do a **full copy backup** of the dataset so you never lose data.

| Step | Action | When |
|------|--------|------|
| 1 | **Full backup** | Before first copy and (optionally) before each push. |
| 2 | **Initial copy** | Once: full `deeplake.copy(local → s3)`. |
| 3 | **Delta sync** | After local changes: `ds.commit()` then `ds.push(s3)`. |

### 3.1 Full backup (serialized / full copy)

- **Option A (recommended):** Copy the entire dataset to a local backup path with a timestamp:
  - `deeplake.copy(src=LOCAL_PATH, dst=f"{BACKUP_DIR}/deeplake_backup_{date})"`
- **Option B:** Use filesystem copy/tar of the dataset directory (same result: full snapshot).

Backup path example: `~/deeplake_backups/` or `./.deeplake_backups/` (keep one per run or prune old ones).

### 3.2 Initial copy (first time)

```python
import deeplake
deeplake.copy(
    src="/path/to/your/local/dataset",
    dst="s3://BUCKET_NAME/dataset_name"
)
# Uses AWS from ~/.aws/credentials or env
```

### 3.3 Delta sync (after you add data locally)

```python
import deeplake
ds = deeplake.open("/path/to/your/local/dataset")
# ... you already did ds.append(...) and ds.commit("message") ...
ds.push("s3://BUCKET_NAME/dataset_name")
```

---

## 4. Automation (bones)

- **Script:** `scripts/deeplake_s3_sync.py`
  1. **Backup:** Full copy of local dataset to `DEEPLAKE_BACKUP_DIR` (default `~/deeplake_backups`) with timestamp. Always runs before any S3 upload to prevent data loss.
  2. **Sync:** `--first-time` → `deeplake.copy(local, s3)`; otherwise → `deeplake.open(local).push(s3)` (deltas only).
- **Credentials:** Script uses the default AWS credential chain (reads **`~/.aws/credentials`** and `~/.aws/config`); no credentials in repo.
- **Config:** Env vars:
  - `DEEPLAKE_LOCAL_PATH` — path to your local Deep Lake dataset (required).
  - `DEEPLAKE_S3_URI` — e.g. `s3://your-bucket/dataset_name` (required for sync).
  - `DEEPLAKE_BACKUP_DIR` — optional; default `~/deeplake_backups`.

**Quick run:**

```bash
export DEEPLAKE_LOCAL_PATH="/path/to/your/local/dataset"
export DEEPLAKE_S3_URI="s3://your-bucket/dataset_name"
python3 scripts/deeplake_s3_sync.py --first-time   # once
python3 scripts/deeplake_s3_sync.py                # after local changes (backup + delta push)
```

---

## 5. Checklist

- [ ] S3 bucket created; public access blocked.
- [ ] IAM user with bucket-only policy; keys in `~/.aws/credentials`.
- [ ] Local dataset path and S3 URI set in script/env.
- [ ] Run backup once manually; then run initial copy.
- [ ] After local changes: commit in Deep Lake, then run script (backup + push).

---

## 6. References

- Deep Lake sync: `deeplake.copy()` (full), `ds.push()` (deltas), `ds.commit()` (required before push).
- AWS credentials: [Configuring credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html); Deep Lake uses same chain when no `creds` passed.
