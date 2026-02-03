#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import uuid
import tempfile

# Set up test environment
os.environ['SUMMARY'] = 'Successfully tested all MAO integration skills'
os.environ['FILES_CHANGED'] = 'mao-register.yaml,mao-log.yaml,mao-update-status.yaml,mao-complete.yaml'
os.environ['MAO_AGENT_ID'] = 'test-claude-code-1770029248'

# Simulate script from mao-complete.yaml (simplified for test)
summary = os.environ.get('SUMMARY', '')
files_changed = os.environ.get('FILES_CHANGED', '')
agent_id = os.environ.get('MAO_AGENT_ID', 'task-agent')

queue_dir = Path('approval_queue')
queue_dir.mkdir(exist_ok=True)

# Create approval item
item_id = str(uuid.uuid4())[:8]
item = {
    'id': item_id,
    'agent_id': agent_id,
    'task_description': summary,
    'status': 'pending',
    'created_at': datetime.utcnow().isoformat(),
    'changed_files': files_changed.split(',') if files_changed else [],
    'output': summary
}

# Save to queue
item_file = queue_dir / f"{item_id}.json"
with open(item_file, 'w', encoding='utf-8') as f:
    json.dump(item, f, indent=2, ensure_ascii=False)

# Update index with file locking
try:
    import fcntl
    has_fcntl = True
except ImportError:
    has_fcntl = False

index_file = queue_dir / 'index.json'
lock_file = queue_dir / '.index.lock'
lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)

try:
    if has_fcntl:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=queue_dir, suffix='.tmp', text=True)
    try:
        # Read existing data
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {'items': []}

        # Add new item
        index['items'].append({
            'id': item_id,
            'agent_id': agent_id,
            'status': 'pending',
            'created_at': item['created_at']
        })

        # Write to temp file
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as tmp_file:
            json.dump(index, tmp_file, indent=2, ensure_ascii=False)

        # Atomic replace
        os.replace(tmp_path, str(index_file))
        
        print(f"✅ Task completed and added to approval queue")
        print(f"📋 Summary: {summary}")
        print(f"🆔 Approval ID: {item_id}")

    except Exception as e:
        try:
            os.unlink(tmp_path)
        except:
            pass
        raise

finally:
    if has_fcntl:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.close(lock_fd)
