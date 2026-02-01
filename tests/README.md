# MAO Test Suite

包括的なテストスイートで、MAO（Multi-Agent Orchestrator）の全機能をテストします。

## テスト構成

```
tests/
├── conftest.py              # 共通フィクスチャとpytest設定
├── unit/                    # 単体テスト
│   ├── test_cli.py         # CLIコマンドのテスト
│   ├── test_project_loader.py  # ProjectLoaderのテスト
│   ├── test_config_loader.py   # ConfigLoaderのテスト
│   ├── test_task_dispatcher.py # TaskDispatcherのテスト
│   ├── test_skill_manager.py   # SkillManagerのテスト
│   ├── test_agent_executor.py  # AgentExecutorのテスト
│   └── test_version.py         # バージョン情報のテスト
├── integration/             # 統合テスト
│   └── test_full_workflow.py   # エンドツーエンドワークフロー
└── e2e/                     # E2Eテスト
    └── test_mao_commands.py    # 実際のCLIコマンド実行

```

## テストの実行

### すべてのテストを実行

```bash
pytest
```

### 特定のカテゴリのテストを実行

```bash
# 単体テストのみ
pytest tests/unit/

# 統合テストのみ
pytest tests/integration/

# E2Eテストのみ
pytest tests/e2e/
```

### 特定のテストファイルを実行

```bash
pytest tests/unit/test_cli.py
```

### 特定のテストクラスまたは関数を実行

```bash
# 特定のクラス
pytest tests/unit/test_cli.py::TestCLI

# 特定の関数
pytest tests/unit/test_cli.py::TestCLI::test_main_help
```

### マーカーを使用してテストを実行

```bash
# 単体テストのみ（マーカーが設定されている場合）
pytest -m unit

# 統合テストのみ
pytest -m integration

# 遅いテストをスキップ
pytest -m "not slow"
```

### 詳細な出力で実行

```bash
# より詳細な出力
pytest -vv

# 失敗したテストの詳細を表示
pytest --tb=long

# stdoutを表示
pytest -s
```

### カバレッジレポート付きで実行

```bash
# pytest-covをインストール
pip install pytest-cov

# カバレッジ測定
pytest --cov=mao --cov-report=html --cov-report=term

# カバレッジレポートを表示（htmlcov/index.htmlを開く）
open htmlcov/index.html
```

## テストの依存関係

必要なパッケージ：

```bash
pip install pytest pytest-asyncio
```

オプションのパッケージ：

```bash
pip install pytest-cov      # カバレッジレポート
pip install pytest-timeout  # テストタイムアウト
pip install pytest-xdist    # 並列実行
```

## テストフィクスチャ

### `temp_project_dir`
一時的なプロジェクトディレクトリを作成します。

```python
def test_example(temp_project_dir):
    # temp_project_dir は Path オブジェクト
    assert temp_project_dir.exists()
```

### `mao_project_dir`
`.mao`ディレクトリと設定ファイルを含む一時的なMAOプロジェクトを作成します。

```python
def test_example(mao_project_dir):
    # .mao ディレクトリが存在する
    assert (mao_project_dir / ".mao").exists()
```

### `mock_anthropic_api_key`
テスト用のモックAPIキーを環境変数に設定します。

```python
def test_example(mock_anthropic_api_key):
    # ANTHROPIC_API_KEY="sk-ant-test-mock-key-12345"
    pass
```

### `no_anthropic_api_key`
環境変数からAPIキーを削除します。

```python
def test_example(no_anthropic_api_key):
    # ANTHROPIC_API_KEY が設定されていない
    pass
```

## テストの書き方

### 単体テスト

個々のモジュールや関数を独立してテストします。

```python
def test_function():
    result = my_function(input_data)
    assert result == expected_output
```

### 統合テスト

複数のモジュールが連携して動作することをテストします。

```python
def test_workflow(mao_project_dir):
    # Step 1: 初期化
    loader = ProjectLoader(mao_project_dir)
    config = loader.load()

    # Step 2: 検証
    assert config.project_name == "test-project"
```

### E2Eテスト

実際のCLIコマンドを実行してテストします。

```python
def test_cli_command():
    result = subprocess.run(
        ["mao", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

## CI/CDでの実行

GitHub Actions設定例：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .[dev]
      - name: Run tests
        run: pytest
```

## トラブルシューティング

### テストが見つからない

```bash
# テスト検出を確認
pytest --collect-only
```

### 特定のテストが失敗する

```bash
# より詳細な出力
pytest tests/path/to/test.py -vv --tb=long
```

### 非同期テストの問題

`pytest-asyncio`がインストールされていることを確認：

```bash
pip install pytest-asyncio
```

## 継続的な改善

- テストカバレッジを確認し、カバーされていない部分を特定
- 失敗するテストを修正
- 新機能を追加する際は必ずテストも追加
- テストの実行速度を定期的に確認
