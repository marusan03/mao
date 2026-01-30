# Go コーディング規約

## 基本方針

- Effective Go に従う
- gofmt でフォーマット
- golangci-lint でリント
- テーブル駆動テスト

## スタイルガイド

### パッケージ構成

```go
// パッケージ名は短く、小文字のみ
package executor

import (
    "context"
    "fmt"

    "github.com/anthropics/anthropic-sdk-go"

    "github.com/marusan03/mao/internal/logger"
)
```

### エラーハンドリング

```go
// エラーは明示的に処理
func ExecuteAgent(ctx context.Context, prompt string) (*AgentResult, error) {
    client := anthropic.NewClient()

    resp, err := client.Messages.New(ctx, anthropic.MessageNewParams{
        Model:    anthropic.F("claude-sonnet-4-20250514"),
        Messages: anthropic.F([]anthropic.MessageParam{
            anthropic.NewUserMessage(anthropic.NewTextBlock(prompt)),
        }),
    })
    if err != nil {
        return nil, fmt.Errorf("failed to execute agent: %w", err)
    }

    return &AgentResult{
        Success:  true,
        Response: resp.Content[0].Text,
        Usage: &Usage{
            InputTokens:  resp.Usage.InputTokens,
            OutputTokens: resp.Usage.OutputTokens,
        },
    }, nil
}
```

### 構造体定義

```go
// AgentResult はエージェント実行結果を表します
type AgentResult struct {
    Success  bool
    Response string
    Usage    *Usage
    Error    error
}

// Usage はトークン使用量を表します
type Usage struct {
    InputTokens  int64
    OutputTokens int64
}

// コンストラクタ関数
func NewAgentExecutor(apiKey string) *AgentExecutor {
    return &AgentExecutor{
        client: anthropic.NewClient(
            option.WithAPIKey(apiKey),
        ),
    }
}
```

### インターフェース

```go
// 小さなインターフェース
type Executor interface {
    Execute(ctx context.Context, prompt string) (*AgentResult, error)
}

// インターフェース名は -er サフィックス
type Logger interface {
    Info(msg string, fields ...Field)
    Error(msg string, err error, fields ...Field)
}
```

## テスト

### テーブル駆動テスト

```go
func TestExecuteAgent(t *testing.T) {
    tests := []struct {
        name    string
        prompt  string
        want    bool
        wantErr bool
    }{
        {
            name:    "success",
            prompt:  "test prompt",
            want:    true,
            wantErr: false,
        },
        {
            name:    "empty prompt",
            prompt:  "",
            want:    false,
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            executor := NewAgentExecutor("test-key")
            result, err := executor.Execute(context.Background(), tt.prompt)

            if (err != nil) != tt.wantErr {
                t.Errorf("Execute() error = %v, wantErr %v", err, tt.wantErr)
                return
            }

            if result != nil && result.Success != tt.want {
                t.Errorf("Execute() success = %v, want %v", result.Success, tt.want)
            }
        })
    }
}
```

## ベストプラクティス

### Context の使用

```go
// context を第一引数に
func (e *AgentExecutor) Execute(ctx context.Context, prompt string) (*AgentResult, error) {
    // タイムアウト設定
    ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
    defer cancel()

    // context をAPI呼び出しに渡す
    return e.client.Execute(ctx, prompt)
}
```

### ゴルーチンとチャネル

```go
// 並列実行
func ExecuteMultiple(ctx context.Context, prompts []string) ([]*AgentResult, error) {
    results := make([]*AgentResult, len(prompts))
    errCh := make(chan error, len(prompts))

    var wg sync.WaitGroup
    for i, prompt := range prompts {
        wg.Add(1)
        go func(idx int, p string) {
            defer wg.Done()

            result, err := Execute(ctx, p)
            if err != nil {
                errCh <- err
                return
            }
            results[idx] = result
        }(i, prompt)
    }

    wg.Wait()
    close(errCh)

    if err := <-errCh; err != nil {
        return nil, err
    }

    return results, nil
}
```

### リソース管理

```go
// defer で確実にクローズ
func ReadConfig(path string) (*Config, error) {
    file, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    var config Config
    if err := yaml.NewDecoder(file).Decode(&config); err != nil {
        return nil, err
    }

    return &config, nil
}
```
