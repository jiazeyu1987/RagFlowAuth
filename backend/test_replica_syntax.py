#!/usr/bin/env python3
"""Test replica_service.py syntax"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from services.data_security.replica_service import BackupReplicaService
    print("✓ Import successful")
    print(f"✓ BackupReplicaService class exists")
    print(f"✓ Methods: {[m for m in dir(BackupReplicaService) if not m.startswith('_')]}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
