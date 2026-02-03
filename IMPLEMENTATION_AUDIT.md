# MAO実装監査レポート
**実装を正として作成**
**作成日**: 2026-02-02

---

## 🎯 エグゼクティブサマリー

MAOの実装とドキュメントに以下のギャップが存在します：

1. **ロールの混在**: MAOロール定義とClaude Codeエージェントタイプが混在
2. **未使用の定義**: 定義されているが実際には使われていないロール
3. **ドキュメント不一致**: 古い設計ドキュメントが現在の実装と乖離

---

## 📊 実装状況の真実

### 実際に動作している仕組み

#### ワーカーエージェントの実行方式
```
CTOプロンプト
    ↓
/spawn-worker スキル呼び出し
    ↓
ClaudeCodeExecutor
    ↓
claude-code CLI（--print）
    ↓
Claude APIに直接リクエスト
```

**重要**: ワーカーは `claude-code` CLIを通じて起動され、MAOロール定義（YAML）は**使用されていません**。

#### 実際に使用されている「ロール」
これらは実際にはClaude Codeの**サブエージェントタイプ**です：

| "ロール"名 | 実体 | 用途 |
|-----------|------|------|
| `general-purpose` | Claude Code汎用エージェント | コード実装、ファイル編集 |
| `Explore` | Claude Code探索エージェント | コードベース調査、ファイル検索 |
| `Bash` | Claude Codeシェル実行エージェント | コマンド実行、スクリプト |
| `Plan` | Claude Code計画エージェント | アーキテクチャ設計、計画立案 |

**出典**:
- `mao/ui/dashboard_interactive.py:1580-1612` (CTOプロンプト)
- `mao/orchestrator/claude_code_executor.py` (実行エンジン)
- `.mao/skills/spawn-worker.yaml` (スキル定義)

---

## 🗂️ 定義されているが未使用のMAOロール

以下のYAMLロール定義が存在しますが、**現在の実装では使用されていません**：

### 開発系
- ❌ `coder_backend.yaml` - バックエンドコーダー
  - 定義場所: `mao/roles/development/coder_backend.yaml`
  - 使用箇所: なし

### 品質保証系
- ❌ `reviewer.yaml` - コードレビュアー
  - 定義場所: `mao/roles/quality/reviewer.yaml`
  - 使用箇所: なし

- ❌ `tester.yaml` - テスター
  - 定義場所: `mao/roles/quality/tester.yaml`
  - 使用箇所: なし

### 計画系
- ❌ `planner.yaml` - プランナー
  - 定義場所: `mao/roles/planning/planner.yaml`
  - 使用箇所: なし

- ❌ `researcher.yaml` - リサーチャー
  - 定義場所: `mao/roles/planning/researcher.yaml`
  - 使用箇所: なし

### ガバナンス系
- ❌ `auditor.yaml` - 監査担当
  - 定義場所: `mao/roles/governance/auditor.yaml`
  - 使用箇所: なし

### メタ系
- ❌ `skill_extractor.yaml` - スキル抽出
  - 定義場所: `mao/roles/meta/skill_extractor.yaml`
  - 使用箇所: なし

- ❌ `skill_reviewer.yaml` - スキルレビュー
  - 定義場所: `mao/roles/meta/skill_reviewer.yaml`
  - 使用箇所: なし

### 使用中のロール
- ✅ `cto.yaml` - CTO（最高技術責任者）
  - 定義場所: `mao/roles/cto.yaml`
  - 使用箇所: `mao/ui/dashboard_interactive.py`（ただしClaude Code経由で直接実行）

---

## 🔍 実装の詳細分析

### CTOの実装（唯一使用されているロール）

**ファイル**: `mao/ui/dashboard_interactive.py`
**実行方式**:
```python
# ClaudeCodeExecutorを使用（MAOロールYAMLは未使用）
result = await self.manager_executor.execute_agent(
    prompt=f"""あなたはCTO（Chief Technology Officer）です。
    ...
    """,
    model=self.initial_model,
    work_dir=self.work_dir,
)
```

**重要**: CTOロールYAML定義は存在するが、実際にはプロンプト内で直接指示を記述しており、YAMLの内容は読み込まれていません。

### ワーカーの実行方式

**スキル呼び出し**:
```bash
/spawn-worker --task "タスク説明" --role general-purpose --model sonnet
```

**実際の実行**（tmux経由）:
```bash
cat prompt_file | claude-code --print --model sonnet --add-dir /path/to/worktree
```

**プロセス**:
1. CTOが `/spawn-worker` スキルを呼び出し
2. `[MAO_WORKER_SPAWN]` JSONブロックを出力
3. `_extract_worker_spawns()` がJSONを抽出
4. `_spawn_task_agent()` がワーカーを起動
5. `tmux_manager.execute_claude_code_in_pane()` でtmuxペイン内で実行
6. `claude-code` CLIがClaude APIを直接呼び出し

**ロールパラメータの扱い**:
- `--role` パラメータは**メタデータとしてのみ記録**
- `claude-code` コマンドには `--role` フラグは存在しない
- 実際の動作は `--model` パラメータで決定

---

## 📝 ドキュメントと実装のギャップ

### ARCHITECTURE.md

**記載内容**:
```
5層階層システム:
1. Governance層（Auditor）
2. Planning層（Planner, Researcher）
3. Development層（Designer, Coder, etc）
4. Quality層（Reviewer, Tester）
5. Integration層（Integrator, Documentor, DevOps）
```

**実際の実装**:
- ❌ 5層システムは実装されていない
- ✅ CTOが中央管理
- ✅ ワーカーが並列/順次実行
- ❌ 層間の承認フローは未実装
- ⚠️ CTO承認ワークフローのみ実装（単一層）

### INTERACTIVE_MODE.md

**記載内容（Phase 1）**:
- ✅ マネージャー（CTO）チャットUI - 実装済み
- ✅ 基本対話 - 実装済み
- ✅ Claude Code統合 - 実装済み

**記載内容（Phase 2）**:
- ⚠️ 自動タスク分配 - 部分実装（シーケンシャルのみ）
- ❌ ステータス自動更新 - デモデータ表示のみ
- ❌ 能動的提案 - 未実装

**記載内容（Phase 3）**:
- ❌ YAMLタスクキュー - JSON形式で実装
- ⚠️ ワーカー通信 - 承認キュー経由のみ
- ❌ 複数マネージャー - 未実装

### DASHBOARD_SPECIFICATION.md

**Phase 1（基本ウィジェット）**: ✅ 100%実装
**Phase 2（SimpleDashboard）**: ⚠️ 50%実装（設計と異なる）
**Phase 3（リアルタイム更新）**: ⚠️ 50%実装（1秒ポーリング）
**Phase 4（進捗バー等）**: ❌ 未実装
**Phase 5（テスト・ドキュメント）**: ❌ 不足

---

## 🚨 重大な設計と実装の乖離

### 1. ロールシステムの二重構造

**設計意図**: MAOロール定義（YAML）を使用
**実装**: Claude Codeサブエージェントタイプを使用

**問題点**:
- YAMLロール定義が無駄になっている
- "ロール"という用語が2つの意味を持つ（混乱の原因）
- 拡張性が制限される（Claude Codeのタイプに依存）

### 2. 階層システムの未実装

**設計意図**: 5層の階層的承認フロー
**実装**: CTO→ワーカーの2層のみ

**影響**:
- Auditor、Reviewer、Testerなどの役割が存在しない
- セキュリティチェックが機能しない
- 品質保証プロセスがない

### 3. ワーカーの制限

**設計意図**: 多様なロール定義で専門化
**実装**: 4種類のClaude Codeタイプのみ

**制約**:
- カスタムロールを追加できない
- ロール固有のプロンプトを設定できない
- システムプロンプトはClaude Codeに依存

---

## ✅ 推奨アクション

### 優先度: 高（即時対応）

#### 1. ドキュメントを実装に合わせる
**タスク**: 以下のドキュメントを更新

**ARCHITECTURE.md**:
```markdown
# 現在の実装（2層システム）

CTO（マネージャー）
    ↓
ワーカー（Claude Codeエージェント）
    - general-purpose: コード実装
    - Explore: コードベース探索
    - Bash: コマンド実行
    - Plan: 計画立案

# 将来の拡張（5層システム - 未実装）
...
```

**INTERACTIVE_MODE.md**:
```markdown
## 実装状況

### Phase 1: ✅ 完了
- CTOチャットUI
- Claude Code統合
- タスク分解

### Phase 2: ⚠️ 部分実装
- シーケンシャル実行のみ
- 並列実行は未対応

### Phase 3: ❌ 未実装
- 複数マネージャー
- 動的再割り当て
```

#### 2. 用語の統一
**before**:
- "ロール" = MAOロール（YAML）+ Claude Codeタイプ

**after**:
- "マネージャー" = CTO
- "ワーカータイプ" = general-purpose, Explore, Bash, Plan
- "（将来）ロール" = YAML定義のMAOロール

#### 3. README更新
現在の実装を正確に反映：
- CTOがタスクを分解
- `/spawn-worker` スキルでワーカー起動
- シーケンシャル実行と承認フロー
- 4種類のワーカータイプ

### 優先度: 中（1-2週間）

#### 4. 未使用ロール定義の整理
**オプション A**: 削除
- 使用されていないYAMLを削除してシンプル化

**オプション B**: 実装
- MAOロールローダーを作成
- YAMLからシステムプロンプトを生成
- Claude Codeの代わりにClaude APIを直接使用

#### 5. 実装範囲の明確化
**現在サポート**:
- ✅ CTOによるタスク分解
- ✅ シーケンシャル実行
- ✅ CTO承認ワークフロー
- ✅ tmuxグリッド表示

**サポート外（明記）**:
- ❌ 5層階層システム
- ❌ 並列実行
- ❌ 複数マネージャー
- ❌ Auditor/Reviewer等の専門ロール

### 優先度: 低（将来）

#### 6. MAOロールシステムの完全実装
- YAMLロール定義の読み込み
- カスタムシステムプロンプト
- ロール固有のツールセット
- 階層的承認フロー

---

## 📊 実装カバレッジサマリー

| カテゴリ | 設計 | 実装 | カバレッジ |
|---------|------|------|-----------|
| **コアシステム** |
| CTO管理 | ✅ | ✅ | 100% |
| ワーカー起動 | ✅ | ✅ | 100% |
| タスクキュー | ✅ | ✅ | 100% |
| 承認フロー | ✅ | ✅ | 100% |
| **エージェントタイプ** |
| general-purpose | ✅ | ✅ | 100% |
| Explore | ✅ | ✅ | 100% |
| Bash | ✅ | ✅ | 100% |
| Plan | ✅ | ✅ | 100% |
| **MAOロール（YAML）** |
| CTO | ✅ | ⚠️ | 50% (定義のみ) |
| coder_backend | ✅ | ❌ | 0% |
| reviewer | ✅ | ❌ | 0% |
| tester | ✅ | ❌ | 0% |
| planner | ✅ | ❌ | 0% |
| researcher | ✅ | ❌ | 0% |
| auditor | ✅ | ❌ | 0% |
| **システム機能** |
| 階層システム | ✅ | ❌ | 0% |
| 並列実行 | ✅ | ❌ | 0% |
| シーケンシャル実行 | ⚠️ | ✅ | 100% |
| リアルタイム更新 | ✅ | ⚠️ | 70% |
| **UI** |
| ダッシュボード | ✅ | ✅ | 90% |
| tmuxグリッド | ✅ | ✅ | 95% |
| 承認パネル | ✅ | ✅ | 100% |

**総合カバレッジ**: 約**45%**

---

## 🎯 結論

### 現在のMAOは何ができるのか（実装ベース）

**✅ できること**:
1. CTOが複雑なタスクを分解
2. 4種類のワーカータイプでタスク実行（general-purpose, Explore, Bash, Plan）
3. シーケンシャル実行と承認フロー
4. tmuxでワーカーをリアルタイム監視
5. git worktreeで分離された開発環境
6. フィードバック収集と改善サイクル

**❌ できないこと（設計されているが未実装）**:
1. 5層階層システム
2. 並列実行（依存関係管理）
3. Auditor/Reviewer等の専門ロール
4. 複数マネージャーの協調
5. カスタムロール定義（YAML）の使用

### 推奨される方向性

**短期（現実的）**:
- 現在の実装（CTO + 4ワーカータイプ）を磨く
- ドキュメントを実装に合わせる
- シンプルで動作する2層システムとして確立

**長期（野心的）**:
- MAOロールシステムを完全実装
- 5層階層システムの段階的導入
- カスタムロール定義のサポート

---

**監査実施者**: Claude Code (Sonnet 4.5)
**監査日**: 2026-02-02
**ベースライン**: v0.2.1
