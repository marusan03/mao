# TypeScript コーディング規約

## 基本方針

- Airbnb TypeScript スタイルガイドに従う
- strict モードを有効化
- Prettier でフォーマット
- ESLint でリント

## スタイルガイド

### インポート

```typescript
// Node 組み込み
import { readFile } from 'fs/promises';
import path from 'path';

// サードパーティ
import Anthropic from '@anthropic-ai/sdk';
import { z } from 'zod';

// ローカル
import { AgentExecutor } from './executor';
import type { AgentConfig } from './types';
```

### 型定義

```typescript
// インターフェース優先
interface AgentResult {
  success: boolean;
  response?: string;
  usage?: {
    inputTokens: number;
    outputTokens: number;
  };
  error?: string;
}

// 型エイリアスは Union/Intersection で
type AgentStatus = 'idle' | 'running' | 'completed' | 'failed';

// ジェネリクス
interface Repository<T> {
  findById(id: string): Promise<T | null>;
  save(entity: T): Promise<void>;
}
```

### 関数定義

```typescript
// async/await
async function executeAgent(
  prompt: string,
  config: AgentConfig = defaultConfig
): Promise<AgentResult> {
  try {
    const response = await client.messages.create({
      model: config.model,
      messages: [{ role: 'user', content: prompt }],
    });

    return {
      success: true,
      response: response.content[0].text,
      usage: {
        inputTokens: response.usage.input_tokens,
        outputTokens: response.usage.output_tokens,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
```

### エラーハンドリング

```typescript
// カスタムエラークラス
class AgentExecutionError extends Error {
  constructor(
    message: string,
    public readonly agentId: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'AgentExecutionError';
  }
}

// エラーガード
function isAPIError(error: unknown): error is Anthropic.APIError {
  return error instanceof Anthropic.APIError;
}
```

## テスト

### Vitest の使用

```typescript
import { describe, it, expect, vi } from 'vitest';
import { AgentExecutor } from './executor';

describe('AgentExecutor', () => {
  it('should execute agent successfully', async () => {
    const executor = new AgentExecutor();
    const result = await executor.execute('test prompt');

    expect(result.success).toBe(true);
    expect(result.response).toBeDefined();
  });

  it('should handle API errors', async () => {
    const executor = new AgentExecutor();
    vi.spyOn(executor['client'].messages, 'create').mockRejectedValue(
      new Error('API error')
    );

    const result = await executor.execute('test');
    expect(result.success).toBe(false);
    expect(result.error).toBe('API error');
  });
});
```

## ベストプラクティス

### Null 安全

```typescript
// Optional chaining
const tokenCount = result.usage?.inputTokens ?? 0;

// Nullish coalescing
const model = config.model ?? 'claude-sonnet-4-20250514';
```

### 型ガード

```typescript
function isSuccessResult(result: AgentResult): result is Required<AgentResult> & { success: true } {
  return result.success && result.response !== undefined;
}

if (isSuccessResult(result)) {
  console.log(result.response); // string (not undefined)
}
```

### イミュータビリティ

```typescript
// readonly
interface Config {
  readonly model: string;
  readonly maxTokens: number;
}

// as const
const MODELS = {
  OPUS: 'claude-opus-4-20250514',
  SONNET: 'claude-sonnet-4-20250514',
  HAIKU: 'claude-haiku-4-20250514',
} as const;

type ModelName = typeof MODELS[keyof typeof MODELS];
```

### Zod でバリデーション

```typescript
import { z } from 'zod';

const AgentConfigSchema = z.object({
  model: z.string().default('claude-sonnet-4-20250514'),
  maxTokens: z.number().int().positive().default(4096),
  temperature: z.number().min(0).max(1).default(1.0),
});

type AgentConfig = z.infer<typeof AgentConfigSchema>;
```
