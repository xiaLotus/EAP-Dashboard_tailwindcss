"""
EAP_Ping.py — 通用網段 Ping 掃描器（三輪 + dead Buffer）

一支程式，多份 config.ini；換資料夾、換 config 即可用於不同樓層。
寫入的檔案：
  1. 來源 CSV 的 alive_or_dead 欄位（原地覆寫）
  2. <CSV所在資料夾>/backup/<csv名>/backup_yyyymmddHHMMSS.csv
  3. <buffer_file>（EAP / Switch 的 dead 清單，給派報程式讀）
  4. <log_dir>/<log_name>_ping_log_YYYY-MM-DD.log（保留 N 天）
  5. Floor.json（本次處理的樓層標 V）
"""
import os
import re
import sys
import glob
import json
import time
import shutil
import asyncio
import configparser
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from loguru import logger
from filelock import FileLock, Timeout

# =====================================================
# 基本路徑 / config
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_TS = datetime.now().strftime("%Y%m%d%H%M%S")          # 本次執行時間戳（備份檔名用）
RUN_TIME_STR = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

config = configparser.RawConfigParser()
config_path = os.path.join(BASE_DIR, "config.ini")
if not os.path.exists(config_path):
    print(f"❌ 找不到設定檔：{config_path}")
    sys.exit(1)
config.read(config_path, encoding="utf-8-sig")


def cfg(section, key, fallback=None):
    return config.get(section, key, fallback=fallback)


def cfg_list_float(section, key, fallback):
    raw = cfg(section, key, fallback)
    return [float(x) for x in raw.split(",") if x.strip()]


# [Paths]
LOG_DIR = cfg("Paths", "log_dir", os.path.join(BASE_DIR, "log")).rstrip("\\/")
LOG_NAME = cfg("Paths", "log_name", "EAP").strip()
BACKUP_DIR = cfg("Paths", "backup_dir", "").strip().rstrip("\\/")   # 空 = 放在各 CSV 所在資料夾的 backup\ 下
SOURCE_DIRS = [x.strip().rstrip("\\/") for x in cfg("Paths", "source_dirs", "").split(",") if x.strip()]
SOURCE_FILES_EXTRA = [x.strip() for x in cfg("Paths", "source_files", "").split(",") if x.strip()]


def _natural_key(p: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", os.path.basename(p))]


def resolve_source_files() -> list:
    """source_dirs 底下第一層 *.csv（不含子資料夾、不含 backup）+ source_files 額外指定的檔案"""
    files = []
    for d in SOURCE_DIRS:
        if not os.path.isdir(d):
            print(f"⚠️ source_dir 不存在：{d}")
            continue
        found = sorted(glob.glob(os.path.join(d, "*.csv")), key=_natural_key)
        files.extend(found)
    for f in SOURCE_FILES_EXTRA:
        if f not in files:
            files.append(f)
    return files


SOURCE_FILES = resolve_source_files()
FLOOR_JSON = cfg("Paths", "floor_json", "").strip()
FLOOR_KEY = cfg("Paths", "floor_key", "").strip()        # 無法從路徑解析樓層時用（例：other_EAP）

# [Buffer]
BUFFER_FILE = cfg("Buffer", "buffer_file", os.path.join(BASE_DIR, "dead_buffer.csv")).strip()

# [Scan]
ROUND1_TIMEOUTS = cfg_list_float("Scan", "round1_timeouts", "0.5, 2")
ROUND2_TIMEOUT = float(cfg("Scan", "round2_timeout", "3"))
ROUND3_TIMEOUTS = cfg_list_float("Scan", "round3_timeouts", "3, 5")
ROUND3_DELAY_SEC = float(cfg("Scan", "round3_delay_sec", "1"))
MAX_CONCURRENT = int(cfg("Scan", "max_concurrent", "200"))
BACKUP_KEEP = int(cfg("Scan", "backup_keep", "5"))
LOG_RETENTION_DAYS = int(cfg("Scan", "log_retention_days", "90"))
DEVICE_NAME_REGEX = re.compile(cfg("Scan", "device_name_regex", r"\d{8}-W\d{2,3}").strip())

BUFFER_CATEGORIES = {"EAP", "SWITCH"}      # Buffer 只收這兩類（大小寫不分）
_INVALID = frozenset({"", "0", "nan", "none", "null", "<na>"})

# =====================================================
# logger
# =====================================================
os.makedirs(LOG_DIR, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add(
    os.path.join(LOG_DIR, f"{LOG_NAME}_ping_log_{{time:YYYY-MM-DD}}.log"),
    level="INFO",
    rotation="00:00",
    retention=f"{LOG_RETENTION_DAYS} days",
    encoding="utf-8",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# =====================================================
# 共用工具
# =====================================================
def is_valid(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    return str(val).strip().lower() not in _INVALID


def clean(val) -> str:
    return str(val).strip() if is_valid(val) else ""


def extract_building_floor(file_path: str):
    """從 ...\\source\\{棟別}\\{樓層}\\{檔名} 解析；特例：其他 / suixiu"""
    fname = os.path.basename(file_path).lower()
    if fname == "suixiu.csv":
        return "歲修", "歲修表單"
    if ("\\其他\\" in file_path or "/其他/" in file_path):
        return "其他", "其他"
    parts = Path(file_path).parts
    if "source" in parts:
        i = parts.index("source")
        if len(parts) > i + 2:
            return parts[i + 1].strip(), parts[i + 2].strip()
    return "", ""


# =====================================================
# Ping 核心（aioping 優先，失敗 fallback subprocess）
# =====================================================
try:
    import aioping
    AIOPING_AVAILABLE = True
except ImportError:
    AIOPING_AVAILABLE = False


async def ping_host_async(host: str, timeout: float) -> bool:
    if AIOPING_AVAILABLE:
        try:
            delay = await aioping.ping(host, timeout=timeout)
            return delay is not None
        except Exception:
            pass
    try:
        if sys.platform.startswith("win"):
            args = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
            flags = {"creationflags": 0x08000000}   # CREATE_NO_WINDOW
        else:
            args = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), host]
            flags = {}
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, **flags
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 2)
        out = (stdout or b"").decode("utf-8", errors="ignore").lower()
        return proc.returncode == 0 and ("ttl=" in out or "bytes from" in out)
    except Exception:
        return False


async def run_scan(targets: dict, timeout: float, desc: str) -> tuple[set, set]:
    """
    targets: {key: host}  key 通常是 IP，host 是實際要 ping 的字串（IP 或主機名）
    回傳 (alive_keys, dead_keys)
    """
    alive, dead = set(), set()
    if not targets:
        return alive, dead
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def one(key, host):
        async with sem:
            return key, await ping_host_async(host, timeout)

    tasks = [asyncio.create_task(one(k, h)) for k, h in targets.items()]
    with tqdm(total=len(tasks), desc=desc, unit="host") as pbar:
        for fut in asyncio.as_completed(tasks):
            key, ok = await fut
            (alive if ok else dead).add(key)
            pbar.update(1)
    return alive, dead


async def multi_timeout_scan(ips: list, timeouts: list, desc: str) -> tuple[set, set]:
    """依序用多段 timeout 掃描，上一段 dead 的才進下一段"""
    alive_all, pending = set(), set(ips)
    for i, t in enumerate(timeouts, 1):
        if not pending:
            break
        start = time.time()
        a, d = await run_scan({ip: ip for ip in pending}, t, f"{desc}-{i}(t={t}s)")
        logger.info(f"⏱️ {desc}-{i} timeout={t}s | {time.time()-start:.1f}s | alive={len(a)} dead={len(d)}")
        alive_all |= a
        pending = d
    return alive_all, pending


# =====================================================
# 備份（backup_yyyymmddHHMMSS.csv，保留 BACKUP_KEEP 份）
# =====================================================
def backup_dir_for(csv_path: str) -> str:
    """<CSV所在資料夾>\\backup\\<csv檔名去副檔名>；config 有設 backup_dir 則集中到那裡"""
    root = BACKUP_DIR if BACKUP_DIR else os.path.join(os.path.dirname(os.path.abspath(csv_path)), "backup")
    return os.path.join(root, os.path.splitext(os.path.basename(csv_path))[0])


def list_backups(csv_path: str) -> list:
    """回傳備份檔完整路徑，新→舊"""
    files = glob.glob(os.path.join(backup_dir_for(csv_path), "backup_*.csv"))
    return sorted(files, key=lambda p: os.path.basename(p), reverse=True)


def backup_csv(csv_path: str):
    bdir = backup_dir_for(csv_path)
    os.makedirs(bdir, exist_ok=True)
    dst = os.path.join(bdir, f"backup_{RUN_TS}.csv")
    try:
        shutil.copy2(csv_path, dst)
        logger.info(f"📦 備份 → {dst}")
    except Exception as e:
        logger.error(f"❌ 備份失敗 {csv_path}：{e}")
        return
    for old in list_backups(csv_path)[BACKUP_KEEP:]:
        try:
            os.remove(old)
            logger.info(f"🗑️ 刪除舊備份 {os.path.basename(old)}")
        except Exception as e:
            logger.warning(f"⚠️ 刪除舊備份失敗 {old}：{e}")


def alive_in_backups(csv_path: str, ip: str) -> tuple[list, bool]:
    """
    回傳 ([曾 alive 的備份時間戳...], 是否有任何備份檔)
    只看最新 BACKUP_KEEP 份
    """
    files = list_backups(csv_path)[:BACKUP_KEEP]
    hits = []
    for bf in files:
        try:
            df = pd.read_csv(bf, encoding="utf-8-sig", usecols=["Internal_IP", "alive_or_dead"], dtype=str)
        except Exception:
            continue
        m = df["Internal_IP"].astype(str).str.strip() == ip
        if (df.loc[m, "alive_or_dead"].astype(str).str.strip().str.lower() == "alive").any():
            hits.append(os.path.basename(bf)[len("backup_"):-len(".csv")])
    return hits, bool(files)


# =====================================================
# CSV 讀寫
# =====================================================
def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    for col in ["Internal_IP", "Device_Name", "Category", "Machine_ID", "是否派報", "alive_or_dead"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    return df


def save_csv(path: str, df: pd.DataFrame):
    df.to_csv(path, index=False, encoding="utf-8-sig")


# =====================================================
# Buffer 寫入
# =====================================================
BUFFER_COLS = ["First_Seen", "Last_Check", "IP", "Category", "Machine_ID", "Device_Name",
               "Building", "Floor", "Source_File", "Alive_In_Backup", "Dead_Rounds"]


def write_buffer(new_rows: list, processed_sources: set):
    os.makedirs(os.path.dirname(BUFFER_FILE) or ".", exist_ok=True)
    try:
        with FileLock(BUFFER_FILE + ".lock", timeout=60):
            if os.path.exists(BUFFER_FILE):
                try:
                    old = pd.read_csv(BUFFER_FILE, encoding="utf-8-sig", dtype=str, keep_default_na=False)
                except Exception as e:
                    logger.warning(f"⚠️ 讀取 Buffer 失敗，視為空：{e}")
                    old = pd.DataFrame(columns=BUFFER_COLS)
            else:
                old = pd.DataFrame(columns=BUFFER_COLS)
            for c in BUFFER_COLS:
                if c not in old.columns:
                    old[c] = ""

            # 延續 First_Seen / Dead_Rounds
            prev = {(r["IP"], r["Source_File"]): r for _, r in old.iterrows()}
            for row in new_rows:
                p = prev.get((row["IP"], row["Source_File"]))
                if p is not None:
                    row["First_Seen"] = p["First_Seen"] or RUN_TIME_STR
                    try:
                        row["Dead_Rounds"] = int(p["Dead_Rounds"] or 0) + 1
                    except ValueError:
                        row["Dead_Rounds"] = 1
                else:
                    row["First_Seen"] = RUN_TIME_STR
                    row["Dead_Rounds"] = 1

            keep = old[~old["Source_File"].isin(processed_sources)]
            removed = len(old) - len(keep)
            final = pd.concat([keep, pd.DataFrame(new_rows, columns=BUFFER_COLS)], ignore_index=True)[BUFFER_COLS]
            final.to_csv(BUFFER_FILE, index=False, encoding="utf-8-sig")
            logger.success(f"📝 Buffer 寫入 {BUFFER_FILE} | 移除舊列 {removed} | 新增 {len(new_rows)} | 總計 {len(final)}")
    except Timeout:
        logger.error(f"❌ Buffer FileLock 取得失敗：{BUFFER_FILE}")


# =====================================================
# Floor.json 標 V
# =====================================================
def update_floor_json():
    if not FLOOR_JSON:
        return
    if not os.path.exists(FLOOR_JSON):
        logger.warning(f"⚠️ Floor.json 不存在，略過：{FLOOR_JSON}")
        return
    keys = set()
    if FLOOR_KEY:
        keys.add(FLOOR_KEY)
    else:
        for p in SOURCE_FILES:
            m = re.search(r"[\\/](K\d+)[\\/](\d+F)[\\/]", p, re.IGNORECASE)
            if m:
                keys.add(f"{m.group(1).upper()}-{m.group(2).upper()}")
    if not keys:
        logger.warning("⚠️ 無法決定 Floor.json 的 key（請在 config 設 floor_key）")
        return
    try:
        with open(FLOOR_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated = [k for k in keys if data.get(k) != "V"]
        for k in keys:
            data[k] = "V"
        with open(FLOOR_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"✅ Floor.json 標 V：{sorted(keys)}（本次新標：{sorted(updated) or '無'}）")
    except Exception as e:
        logger.error(f"❌ 更新 Floor.json 失敗：{e}")


# =====================================================
# 主流程
# =====================================================
async def main_async():
    t0 = time.time()
    logger.info("🚀 EAP_Ping 啟動")
    logger.info(f"📋 log_name={LOG_NAME} | 來源檔 {len(SOURCE_FILES)} 個 | ping={'aioping' if AIOPING_AVAILABLE else 'subprocess'}")
    for p in SOURCE_FILES:
        logger.info(f"   • {p}")
    if not SOURCE_FILES:
        logger.error("❌ 沒有任何來源 CSV（請檢查 config 的 source_dirs / source_files）")
        return

    dfs: dict[str, pd.DataFrame] = {}            # path -> df
    candidates: dict[tuple, dict] = {}            # (path, ip) -> row info
    processed_sources = set()

    # ---------- 第一輪：每檔全部 IP ----------
    for path in SOURCE_FILES:
        if not os.path.exists(path):
            logger.error(f"❌ 檔案不存在：{path}")
            continue
        logger.info(f"📂 [{os.path.basename(path)}] 開始")
        backup_csv(path)
        df = load_csv(path)
        ips = [ip for ip in df["Internal_IP"].unique() if is_valid(ip)]
        alive, dead = await multi_timeout_scan(ips, ROUND1_TIMEOUTS, "R1")
        df["alive_or_dead"] = df["Internal_IP"].map(lambda ip: "alive" if ip in alive else "dead")
        save_csv(path, df)
        dfs[path] = df
        processed_sources.add(os.path.basename(path))
        logger.info(f"📊 [{os.path.basename(path)}] alive={len(alive)} dead={len(dead)} / {len(ips)}")

        building, floor = extract_building_floor(path)
        for _, r in df.iterrows():
            ip = r["Internal_IP"]
            if ip not in dead:
                continue
            if r["Category"].upper() not in BUFFER_CATEGORIES:
                continue
            if r["是否派報"].upper() == "N":
                continue
            candidates[(path, ip)] = {
                "IP": ip, "Category": r["Category"], "Machine_ID": clean(r["Machine_ID"]),
                "Device_Name": clean(r["Device_Name"]), "Building": building, "Floor": floor,
                "Source_File": os.path.basename(path),
            }
    logger.info(f"🧺 第一輪候選（EAP/Switch dead 且派報≠N）：{len(candidates)}")

    # ---------- 第二輪：Device_Name 主機名 ping ----------
    r2_targets = {k: v["Device_Name"] for k, v in candidates.items()
                  if v["Device_Name"] and DEVICE_NAME_REGEX.match(v["Device_Name"])}
    if r2_targets:
        a2, _ = await run_scan(r2_targets, ROUND2_TIMEOUT, "R2-DeviceName")
        for key in a2:
            path, ip = key
            logger.info(f"✅ R2 主機名通 {candidates[key]['Device_Name']} ({ip}) → alive")
            dfs[path].loc[dfs[path]["Internal_IP"] == ip, "alive_or_dead"] = "alive"
            candidates.pop(key)
        logger.info(f"🔁 第二輪 主機名 ping {len(r2_targets)} 台，恢復 {len(a2)}，剩餘候選 {len(candidates)}")
    else:
        logger.info("🔁 第二輪：無符合正則的 Device_Name，跳過")

    # ---------- 第三輪：IP 再 ping + 備份比對 ----------
    buffer_rows = []
    if candidates:
        if ROUND3_DELAY_SEC > 0:
            await asyncio.sleep(ROUND3_DELAY_SEC)
        a3, d3 = await multi_timeout_scan([k[1] for k in candidates], ROUND3_TIMEOUTS, "R3")
        for key in list(candidates):
            path, ip = key
            if ip in a3:
                logger.info(f"✅ R3 恢復 {ip} → alive")
                dfs[path].loc[dfs[path]["Internal_IP"] == ip, "alive_or_dead"] = "alive"
                candidates.pop(key)
                continue
            hits, has_backup = alive_in_backups(path, ip)
            if hits or not has_backup:
                row = {**candidates[key], "Last_Check": RUN_TIME_STR,
                       "Alive_In_Backup": ",".join(hits) if hits else "NO_BACKUP"}
                buffer_rows.append(row)
                logger.warning(f"🚨 留在 Buffer {ip} [{row['Category']}] {row['Device_Name']} | 歷史 alive: {row['Alive_In_Backup']}")
            else:
                logger.info(f"⏭️ 長期 dead，不進 Buffer {ip}（最近 {BACKUP_KEEP} 份備份皆無 alive）")

    # 第二 / 三輪轉 alive 的回寫 CSV
    for path, df in dfs.items():
        save_csv(path, df)

    write_buffer(buffer_rows, processed_sources)
    update_floor_json()
    logger.info(f"🏁 完成 | Buffer {len(buffer_rows)} 筆 | 總耗時 {time.time()-t0:.1f}s")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.warning("⚠️ 使用者中斷")
    except Exception as e:
        logger.exception(f"❌ 未預期錯誤：{e}")


if __name__ == "__main__":
    main()