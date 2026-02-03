# 🔗 MAO Integration (必須)

**重要**: このエージェントはMAOシステム内で実行されています。以下のskillsを使用してMAOと統合してください。

## 必須手順

### 1. 起動時: MAOに登録

タスクを開始する前に、必ず自分をMAOに登録してください：

```
/mao-register --role [YOUR_ROLE] --task "[BRIEF_TASK_DESCRIPTION]"
```

例：
```
/mao-register --role researcher --task "Investigating authentication patterns"
/mao-register --role coder_backend --task "Implementing REST API"
```

これにより、MAOダッシュボードのAgent一覧に表示されます。

### 2. 作業中: 進捗をログ

作業の各ステップで、進捗をログに記録してください：

```
/mao-log --message "[WHAT_YOU_ARE_DOING]" --level INFO
/mao-update-status --status ACTIVE --task "[CURRENT_WORK]"
```

例：
```
/mao-log --message "Reading project documentation" --level INFO
/mao-update-status --status THINKING --task "Analyzing requirements"

/mao-log --message "Starting implementation" --level INFO
/mao-update-status --status ACTIVE --task "Writing code"
```

ログレベル:
- `DEBUG`: デバッグ情報
- `INFO`: 通常の進捗情報（デフォルト）
- `WARN`: 警告
- `ERROR`: エラー

ステータス:
- `THINKING`: 分析・調査中
- `ACTIVE`: 実装・作業中
- `WAITING`: 待機中
- `COMPLETED`: 完了

### 3. 完了時: 結果を報告

タスクが完了したら、必ず完了報告を送信してください：

```
/mao-complete --summary "[WHAT_YOU_ACCOMPLISHED]" --files-changed "[FILES]"
```

例：
```
/mao-complete --summary "Implemented user authentication API with JWT tokens" --files-changed "auth.py,user.py,test_auth.py"

/mao-complete --summary "Researched WebSocket libraries and recommended Socket.IO"
```

これにより、MAOの承認キューに追加され、CTOがレビューできます。

### 4. エラー時: エラーを報告

エラーが発生した場合：

```
/mao-log --message "[ERROR_DESCRIPTION]" --level ERROR
/mao-update-status --status ERROR --error-message "[ERROR_DETAILS]"
```

例：
```
/mao-log --message "Database connection failed" --level ERROR
/mao-update-status --status ERROR --error-message "Cannot connect to PostgreSQL: connection refused"
```

## 統合フロー例

```
# 1. 登録
/mao-register --role coder_backend --task "Implementing contact API"

# 2. 作業開始
/mao-log --message "Reading existing code" --level INFO
/mao-update-status --status THINKING --task "Understanding codebase"

# 3. 実装中
/mao-log --message "Creating API endpoint" --level INFO
/mao-update-status --status ACTIVE --task "Writing POST /api/contact"

# 4. テスト
/mao-log --message "Testing API endpoint" --level INFO
/mao-update-status --status ACTIVE --task "Running tests"

# 5. 完了
/mao-log --message "API implementation completed" --level INFO
/mao-complete --summary "Implemented POST /api/contact with validation" --files-changed "api/contact.py,test_contact.py"
```

## 注意事項

- **必ず登録してください**: `/mao-register`を実行しないと、MAOダッシュボードに表示されません
- **定期的にログ**: 進捗が分かるように、各ステップでログを記録してください
- **必ず完了報告**: タスクが完了したら`/mao-complete`を実行してください
- **エラーも報告**: 問題が発生したら、エラーログを送信してください

これらのskillsを使用することで、MAOダッシュボードでリアルタイムに進捗を確認できます。

---

**以下、あなたの役割固有の指示に従ってください。**
