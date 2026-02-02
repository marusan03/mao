# CTO Interactive Mode Quick Reference

## Start CTO Interactive Mode

```bash
mao start "Task description"
# CTO interactive mode is automatically enabled
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
- 🤖 **CTO** (Green): CTO responses
- ℹ️ **System** (Yellow): Status notifications

## MAO Roles (CTO automatically assigns)

| ロール | 用途 |
|--------|------|
| coder_backend | バックエンド実装 |
| reviewer | コードレビュー |
| tester | テスト作成・実行 |
| planner | タスク計画・設計 |
| researcher | 技術調査 |
| auditor | セキュリティ監査 |
| skill_extractor | スキル抽出 |
| skill_reviewer | スキルレビュー |

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
You: ログイン機能を実装してください
# CTOが自動的に適切なMAOロール（coder_backend等）にタスクを割り当て
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
- Manually specify worker IDs (CTO handles assignment)
- Try to run multiple CTO sessions simultaneously

## See Also

- Full guide: `docs/INTERACTIVE_MODE.md`
- Implementation: `docs/INTERACTIVE_MODE_IMPLEMENTATION.md`
- Usage: `USAGE.md`
