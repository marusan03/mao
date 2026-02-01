# Interactive Mode Quick Reference

## Start Interactive Mode

```bash
mao start --interactive "Task description"
mao start -i "Task description"             # Short form
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+M` | Focus manager chat input |
| `Enter` | Send message to manager |
| `Esc` | Unfocus chat input |
| `↑` / `↓` | Select agent in list |
| `q` | Quit dashboard |
| `r` | Refresh display |

## Chat Message Types

- 💬 **You** (Cyan): Your messages
- 🤖 **Manager** (Green): Manager responses
- ℹ️ **System** (Yellow): Status notifications

## Common Tasks

### Plan a Task
```
You: タスクを3つのサブタスクに分解してください
```

### Ask Questions
```
You: どの認証方式を推奨しますか？
```

### Request Implementation
```
You: worker-1にログイン機能を実装させてください
```

### Check Status
```
You: 現在の進捗を教えてください
```

## Layout

```
┌──────────────────────┬─────────────────┐
│ Agents (30%)         │ Manager Chat    │
├──────────────────────┤ (90%)           │
│ Logs (70%)           │                 │
│                      ├─────────────────┤
│                      │ Input (10%)     │
└──────────────────────┴─────────────────┘
```

## Tips

✅ **DO:**
- Give clear, specific instructions
- Ask for plans before implementation
- Check progress regularly

❌ **DON'T:**
- Send vague requests like "これやって"
- Expect automatic task distribution (not yet implemented)
- Try to run multiple managers simultaneously

## See Also

- Full guide: `docs/INTERACTIVE_MODE.md`
- Implementation: `docs/INTERACTIVE_MODE_IMPLEMENTATION.md`
- Usage: `USAGE.md`
