# MAO へのフィードバック方法

## フィードバックの送信

作業中に MAO 自体の改善案を発見した場合、以下のフォーマットで記録してください：

```
[MAO_FEEDBACK_START]
Title: 改善案のタイトル（簡潔に）
Category: bug | feature | improvement | documentation
Priority: low | medium | high | critical
Description: |
  詳細な説明をここに記載。
  - 現在の問題点
  - 提案する改善内容
  - 期待される効果
  - 実装のヒント（あれば）
[MAO_FEEDBACK_END]
```

## カテゴリの説明

- **bug**: バグや不具合の報告
- **feature**: 新機能の提案
- **improvement**: 既存機能の改善提案
- **documentation**: ドキュメントの改善

## 優先度の説明

- **low**: あると便利だが、急ぎでない
- **medium**: 改善すると効率が上がる
- **high**: 重要な改善、早めに対応すべき
- **critical**: 致命的な問題、すぐに対応が必要

## 例

```
[MAO_FEEDBACK_START]
Title: タスク分解の精度向上
Category: improvement
Priority: high
Description: |
  現在のタスク分解では、複雑なタスクを適切に分割できないことがある。

  提案:
  - タスクの依存関係を明示的に定義
  - サブタスクの優先順位付け機能を追加
  - タスク分解のテンプレートを充実させる

  期待される効果:
  - より正確なタスク割り当てが可能になる
  - 並行作業の効率が向上する
[MAO_FEEDBACK_END]
```

## 注意事項

- フィードバックは作業の邪魔にならない範囲で記録してください
- 些細なことでも構いません。小さな改善の積み重ねが重要です
- 実装方法が不明でも問題ありません。問題点の指摘だけでも価値があります
- ユーザーのプロジェクトではなく、MAO 自体に関するフィードバックを記録してください

## フィードバックの確認

ユーザーは以下のコマンドでフィードバックを確認できます：

```bash
# フィードバック一覧
mao feedback list

# 詳細表示
mao feedback show <ID>

# フィードバックに取り組む（MAO で MAO を改善）
mao feedback improve <ID>
```
