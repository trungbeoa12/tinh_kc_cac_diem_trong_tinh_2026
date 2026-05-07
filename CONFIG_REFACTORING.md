# Config Refactoring Summary

## ✅ Hoàn tất: Loại bỏ Hardcode, Tập Trung Config

### Vấn Đề Trước
```python
# Mỗi script hardcode paths với 20260504
DEFAULT_INPUT = PROJECT_ROOT / "data_20260504/input/branches_20260504.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "data_20260504/input/crawl_pairs_20260504.xlsx"

# Column names cũng duplicate
DISTANCE_COL = "Khoảng cách đường bộ"  # Hardcode everywhere
COLUMN_MAP = {...}  # Duplicate trong build_crawl_pairs.py
```

**Kết quả:** Khi thay đổi phiên bản data, phải sửa cứng trong 5+ files.

---

## 🎯 Giải Pháp

### 1. Centralized Config Module (`scripts/config.py`)
- Một nơi duy nhất cho tất cả configuration
- `DATA_VERSION = "20260504"` - dễ thay đổi
- `get_data_paths(version)` - auto-generate paths cho phiên bản bất kỳ
- Tất cả constants (columns, regex, selectors)

### 2. Scripts Được Refactor

#### a) `build_crawl_pairs.py`
**Trước:**
```python
DEFAULT_INPUT = PROJECT_ROOT / "data_20260504/input/branches_20260504.xlsx"
COLUMN_MAP = {"Mã phòng ban": "ma_phong_ban", ...}
```

**Sau:**
```python
import config

# Imports COLUMN_MAP from config
points = df[list(config.COLUMN_MAP)].rename(columns=config.COLUMN_MAP)

# Accept --version flag
parser.add_argument("--version", default=config.DATA_VERSION)
```

#### b) `split_crawl_parts.py`
**Trước:**
```python
DEFAULT_SOURCE_FILE = PROJECT_ROOT / "data_20260504/input/crawl_pairs_20260504.xlsx"
if "Khoảng cách đường bộ" not in df.columns:
    df["Khoảng cách đường bộ"] = None
```

**Sau:**
```python
import config

paths = config.get_data_paths(config.DATA_VERSION)
parser.add_argument("--version", default=config.DATA_VERSION)

if config.DISTANCE_COL not in df.columns:
    df[config.DISTANCE_COL] = None
```

#### c) `finalize_results.py`
**Trước:**
```python
DEFAULT_SOURCE = PROJECT_ROOT / "data_20260504/input/crawl_pairs_20260504.xlsx"
DISTANCE_COL = "Khoảng cách đường bộ"
DISTANCE_RE = re.compile(r"...")
ERROR_RE = re.compile(r"...")
```

**Sau:**
```python
import config

DISTANCE_COL = config.DISTANCE_COL
DISTANCE_RE = config.DISTANCE_REGEX
ERROR_RE = config.ERROR_KEYWORDS

parser.add_argument("--version", default=config.DATA_VERSION)
```

#### d) `retry_failed.py`
**Updated:** Dùng `config.get_data_paths()` và `--version` flag

#### e) `crawl_part.py`
**Already updated:** Dùng `config` cho logging, rate-limit thresholds, Google Maps selectors

---

## 🚀 Cách Sử Dụng - Data Mới

### Trước (Hardcode - phải sửa 5+ files):
```python
# build_crawl_pairs.py
DEFAULT_INPUT = PROJECT_ROOT / "data_20260601/input/branches_20260601.xlsx"

# split_crawl_parts.py
DEFAULT_SOURCE_FILE = PROJECT_ROOT / "data_20260601/input/crawl_pairs_20260601.xlsx"

# finalize_results.py
DEFAULT_SOURCE = PROJECT_ROOT / "data_20260601/input/crawl_pairs_20260601.xlsx"
```

### Sau (Chỉ sửa 1 file):
```python
# scripts/config.py
DATA_VERSION = "20260601"  # ✅ Xong!
```

Tất cả scripts tự động adapt.

---

## 📊 Lợi Ích

| Tiêu Chí | Trước | Sau |
|----------|-------|-----|
| **Thay đổi phiên bản data** | 5+ files | 1 file |
| **Duplicate code** | 5 chỗ | 1 chỗ (config.py) |
| **Error risk** | Cao (quên sửa) | Thấp (automated) |
| **Command line** | Cần `--input --output` | Tự động |
| **Consistency** | Kỳ (dễ mismatch) | Tốt (một source) |

---

## ✅ Backward Compatibility

Tất cả scripts vẫn hỗ trợ override bằng command-line arguments:

```bash
# Auto-detect từ config (mặc định)
python scripts/build_crawl_pairs.py

# Override version
python scripts/build_crawl_pairs.py --version 20260601

# Override paths (vẫn hỗ trợ)
python scripts/build_crawl_pairs.py --input custom_input.xlsx --output custom_output.xlsx
```

---

## 📝 User Guide Updated

Hướng dẫn đã cập nhật để hướng dẫn:

1. **Setup data mới:**
   ```bash
   # Chỉ cần thay DATA_VERSION trong config.py
   # Tất cả commands sau đó tự động dùng paths đúng
   ```

2. **Simplified commands:**
   ```bash
   # Trước:
   python build_crawl_pairs.py --input data_20260601/input/branches_20260601.xlsx \
     --output data_20260601/input/crawl_pairs_20260601.xlsx

   # Sau:
   python build_crawl_pairs.py
   ```

3. **Optional version flag for testing:**
   ```bash
   python build_crawl_pairs.py --version 20260601
   ```

---

## 🔍 Files Modified

1. ✅ `scripts/config.py` - Enhanced with `get_data_paths()`
2. ✅ `scripts/build_crawl_pairs.py` - Use config + --version
3. ✅ `scripts/split_crawl_parts.py` - Use config + --version  
4. ✅ `scripts/finalize_results.py` - Use config + --version
5. ✅ `scripts/retry_failed.py` - Use config + --version
6. ✅ `scripts/crawl_part.py` - Already using config
7. ✅ `docs/user_guide.md` - Simplified, removed hardcoded paths

---

## 🎓 Best Practices Achieved

✅ **DRY (Don't Repeat Yourself)** - Configuration centralized
✅ **Single Source of Truth** - One DATA_VERSION to change
✅ **Scalable** - Easy to add new data versions
✅ **Maintainable** - Changes propagate automatically
✅ **User-Friendly** - Simpler commands, less error-prone
✅ **Backward Compatible** - Old command style still works

---

**Status:** ✅ Refactoring Complete
**Date:** May 7, 2026
