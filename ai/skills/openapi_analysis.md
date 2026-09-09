# OpenAPI 分析 Skill

## 目标

根据 OpenAPI/Swagger 接口定义识别可测试的请求、响应和约束。测试设计必须以输入文档为依据。

## 必须遵守

- 每条用例的 `method` 和 `path` 必须来自输入接口定义。
- 路径参数必须使用文档中的参数名；不要擅自改名或增加路径层级。
- 请求参数优先使用 `required`、`schema.type`、`enum`、`default`、`example`、`minimum`、`maximum`、`minLength`、`maxLength` 等文档信息。
- 请求体必须匹配文档中的媒体类型和字段结构；没有请求体定义时不要擅自添加 JSON body。
- 响应断言优先使用文档声明的状态码、响应字段、字段类型、必填字段和示例。
- 认证信息只能根据 `securitySchemes`、全局 `security` 或操作级 `security` 推导。

## 信息不足时

- 可以生成状态码、响应结构、字段存在性和字段类型断言。
- 不能凭空猜测数据库内容、用户名、业务状态、错误文案或资源数量。
- 无法确定的内容写入 `notes`，不要用看似准确的固定值代替。
