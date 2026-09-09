# AI 输出契约 Skill

## 顶层结构

只允许输出 JSON 对象，禁止 Markdown 代码块、解释文字和注释：

```json
{
  "schema_version": "1.0",
  "cases": []
}
```

## 用例结构

分批生成时，只输出当前 Prompt 指定接口的用例，不要输出其他接口的用例。每次最多生成 20 条有依据的用例，实际数量由接口定义决定。

每条用例至少包含：`case_id`、`title`、`method`、`path`、`assertions`。

允许的测试类型为：`positive`、`negative`、`boundary`、`dependency`。

允许的优先级为：`P0`、`P1`、`P2`、`P3`。

每条用例的 `assertions` 必须是非空数组，每项至少包含：`target`、`operator`、`expected`；JSON 断言还必须包含 JSONPath `path`。

`extracts` 和 `depends_on` 没有内容时必须输出空数组，不要省略为字符串或 null。

## 禁止内容

- 禁止输出 `script`、`python`、`shell`、`command`、`code` 字段。
- 禁止输出 Python、Shell、SQL、JavaScript 或模板执行代码。
- 禁止引用输入接口定义中不存在的 method/path。
- 禁止重复 `case_id`。
- 禁止把无法确定的值伪装成确定的断言 expected。
- `depends_on` 只能引用 Prompt 中提供的已知 `case_id`。
