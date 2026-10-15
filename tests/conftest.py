import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path so 'backend' can be imported anywhere
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Ensure a writable temporary DATA_DIR exists for all tests
_temp_dir = tempfile.mkdtemp(prefix="appwatch_test_data_")
if "DATA_DIR" not in os.environ:
    os.environ["DATA_DIR"] = _temp_dir
os.environ["DISABLE_SCHEDULER"] = "1"
