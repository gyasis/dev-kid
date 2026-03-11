# rclone → AWS S3 (twice bucket) — setup on another machine

Use this on **any other computer** (or agent) that will run rclone to send backup files to your personal S3 bucket. No AWS CLI needed; only rclone.

---

## Quick reference — S3 bucket & config

| What | Value |
|------|--------|
| **S3 bucket name** | `twice-rclone-backup-768419822031` |
| **rclone config file** (where AWS credentials live) | `~/.config/rclone/rclone.conf` |
| **Remote name** (in that config) | `twice-s3` |
| **Region** | `us-east-1` |
| **Where credentials come from** | Main machine: `docs/rclone-twice-s3-remote.conf` (Access Key ID + Secret Access Key) |

So: put the `[twice-s3]` block (with real `access_key_id` and `secret_access_key`) into **`~/.config/rclone/rclone.conf`** on this machine. That config is the only “AWS credentials list” rclone uses; there is no separate AWS CLI config needed.

---

## What you need from the main machine

On the machine where the bucket was created, open **`docs/rclone-twice-s3-remote.conf`** and note:

- **Access Key ID**
- **Secret Access Key**

(Or copy the whole `[twice-s3]` block and paste it into rclone config on this machine.)

---

## 1. Install rclone

**Linux (WSL/Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install -y rclone
```

**macOS:**
```bash
brew install rclone
```

**Windows:**  
Download from https://rclone.org/downloads/ and add to PATH.

Check:
```bash
rclone version
```

---

## 2. Configure the S3 remote

**Option A — Paste the full remote (easiest)**  
Copy the entire `[twice-s3]` section from `docs/rclone-twice-s3-remote.conf` on your main machine. On this machine:

```bash
mkdir -p ~/.config/rclone
nano ~/.config/rclone/rclone.conf   # or vim, code, etc.
```

Paste the block so it looks like:

```ini
[twice-s3]
type = s3
provider = AWS
env_auth = false
access_key_id = YOUR_ACCESS_KEY_ID
secret_access_key = YOUR_SECRET_ACCESS_KEY
region = us-east-1
acl = private
```

Save and exit.

**Option B — Interactive config**

```bash
rclone config
```

- `n` (new remote)
- Name: `twice-s3`
- Storage: `s3` (Amazon S3)
- Provider: `AWS`
- env_auth: `false`
- access_key_id: *(paste from main machine)*
- secret_access_key: *(paste from main machine)*
- region: `us-east-1`
- acl: `private` or leave default
- Edit/save/quit as prompted

---

## 3. Point rclone at the bucket and send files

**Bucket name:** `twice-rclone-backup-768419822031`  
**Remote name:** `twice-s3`  
**Region:** `us-east-1` (already in config)

**Test (list bucket — should be empty or show existing objects):**
```bash
rclone ls twice-s3:twice-rclone-backup-768419822031
```

**Backup a folder (sync — mirror local to S3):**
```bash
rclone sync /path/to/local/folder twice-s3:twice-rclone-backup-768419822031/backup-folder
```

**Copy (add files, keep existing):**
```bash
rclone copy /path/to/local/folder twice-s3:twice-rclone-backup-768419822031/backup-folder
```

**Use a subfolder inside the bucket (recommended):**
```bash
rclone sync /home/user/Documents twice-s3:twice-rclone-backup-768419822031/documents
```

---

## 4. One-line summary for another agent

On a new machine with rclone installed, add a remote `twice-s3` to `~/.config/rclone/rclone.conf` with type `s3`, provider `AWS`, region `us-east-1`, and the access key + secret from the machine that created the bucket. Then run:

`rclone sync <local-path> twice-s3:twice-rclone-backup-768419822031/<optional-prefix>`

to send files to AWS S3.
