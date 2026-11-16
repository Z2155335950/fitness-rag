# 网红训练法 · 训练对话系统

一个面向中文健美训练场景的多轮聊天助手。对话模型负责自然交流和计划组织，
本地 RAG 负责提供动作、肌肉和训练事实。没有配置模型 Key 时，系统仍能多轮
追问训练目标、频率和器械，并生成基础训练框架。

事实类回答采用严格文档引用：模型只能依据本轮 `<documents>` 回答，并用
`[1]`、`[2]` 标注来源。缺少资料时直接说明依据不足；缺少引用或引用不存在
的材料时，系统会丢弃模型回答并切换到本地文档答案。API 的 `citations`
返回实际被引用的片段，历史记录只保存这些实际引用来源。

## 功能

- 动作、肌肉别名和身体部位识别
- 多轮会话记忆与训练需求面板
- 计划类问题使用按肌群、目标和训练风格生成的多查询检索
- SQLite 持久化历史、搜索、自动标题、重命名和删除
- 缺信息时主动追问，信息足够后生成周训练计划
- 可替换的 OpenAI 兼容模型适配器
- 无 Key 的本地对话降级模式
- 四类查询意图：动作详情、肌肉找动作、条件筛选、开放语义问题
- BGE 向量、BM25、精确实体和肌肉反向索引多路召回
- RRF 融合与器械/难度/部位过滤
- FastAPI 网页与 JSON API
- 20 条问题的 Hit@5 与意图准确率评测

当前知识库包含 110 个训练动作和 34 个肌肉条目，覆盖胸、背、肩、手臂、腿和核心。
观点索引目前包含 222 条训练观点：谭成义 91 条、好人松松 40 条、
凯圣王 42 条、Jeff Nippard 49 条。

建库时还会为动作生成 294 条字段辅助 chunk，包括发力要点、常见错误、
训练提示和目标肌群。字段 chunk 保存在独立向量库和 BM25 索引中，查询命中
字段后会自动回查完整动作，不会替代实体级主文档。

## 安装

需要 Python 3.11。

```powershell
python -m pip install -r requirements.txt
```

首次建库会从 Hugging Face 下载 `BAAI/bge-small-zh-v1.5`。

## 建库

原始 Markdown 已放在 `data/raw/`。完整重建流程：

```powershell
python -m src.parsers.parse_actions
python -m src.parsers.parse_muscles
python -m src.parsers.parse_viewpoints "原始观点文件.jsonl"
python -m src.index.build_index
```

建库默认先写入临时目录，全部索引和派生文件成功后再切换，失败不会覆盖
现有可用索引。调试时可使用 `--no-atomic` 直接写入，但不应在正式环境使用。

索引会生成到 `db/`，肌肉到动作的反向索引会生成到 `data/parsed/reverse_index.json`。
观点会清洗到 `data/parsed/viewpoints.jsonl`，并以独立的 `viewpoint` 文档
进入向量库，不会和动作事实混成同一条记录。

建库还会生成 [action_viewpoints.json](data/parsed/action_viewpoints.json)，
提供 `action_id → 结构化人物观点列表` 的持久化关联。动作详情接口会返回
`action_detail.related_viewpoints`，也可单独查询：

```text
GET /api/actions/{action_id}/viewpoints
```

多个博主建议使用独立文件，例如：

```text
data/parsed/viewpoints.jsonl                   谭成义观点
data/parsed/viewpoints_haorensongsong.jsonl    好人松松观点
```

建库脚本会合并所有 `viewpoints*.jsonl`，同时保留各自的说话者和来源。

观点文件支持标准 JSON、JSONL 和格式化 JSON 对象流。转换器会：

- 把常见简称映射到现有 `action_id`，避免重复创建动作。
- 删除完全重复的观点。
- 检查动作 ID 是否存在。
- 修复缺失的说话者 ID 和标题。
- 标记缺失具体视频地址的来源为 `needs_source_link`。

如果 Hugging Face 主站访问超时，可以在当前 PowerShell 会话使用镜像：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

模型下载完成后，后续重建可加 `--offline`，避免再次探测网络：

```powershell
python -m src.index.build_index --offline
```

## 使用

复制模型配置模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
LLM_PROVIDER=deepseek
LLM_API_KEY=your-api-key
LLM_MODEL=deepseek-flash
LLM_BASE_URL=https://api.deepseek.com
```

DeepSeek-V4.1-Flash 在 API 中使用模型名 `deepseek-flash`，不要把展示版本号
作为 `LLM_MODEL`。项目也支持其他兼容 Chat Completions 的服务，例如本地
Ollama 或其他模型供应商。没有 Key 时会自动进入本地训练助手模式。

原检索命令行仍然可用：

```powershell
python -m src.cli "深蹲怎么做"
python -m src.cli "家里没哑铃怎么练胸" --json
```

网页和 API：

```powershell
.\start.ps1
```

打开 `http://127.0.0.1:8000`。API 示例：

`start.ps1` 会自动切换到项目目录，因此可以从任意位置启动。若 PowerShell
禁止执行本地脚本，可临时使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

```powershell
$body = @{
  message = "我是新手，给我推荐一份训练计划"
  session_id = $null
} | ConvertTo-Json

$reply = Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/chat `
  -ContentType "application/json" `
  -Body $body

$body = @{
  message = "想增肌，每周3天，家里有哑铃"
  session_id = $reply.session_id
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/chat `
  -ContentType "application/json" -Body $body
```

单轮检索接口 `/api/query` 仍然保留，供旧调用方使用。

## 测试与评测

```powershell
python -m unittest discover -s tests -v
python data/eval/run_eval.py --write-report
```

本机一次运行编译、测试和依赖检查：

```powershell
python scripts/check.py
```

`/health` 会读取 `db/manifest.json` 并校验索引文件树哈希；索引缺失、损坏
或与 manifest 不一致时返回 `ready=false`。

评测报告写入 `data/eval/latest_report.json`。

## 目录

```text
data/raw/       原始知识库 Markdown
data/parsed/    结构化 JSONL、别名和反向索引
data/eval/      评测题和评测脚本
src/parsers/    Markdown 解析
src/parsers/parse_viewpoints.py  人物观点清洗与动作关联
src/query/      实体识别与意图路由
src/retrieval/  多路召回与融合
src/index/      向量、BM25 和反向索引构建
src/embedding/  EmbeddingProvider 接口与 BGE 实现
src/vectorstore/ VectorStore 接口、Chroma 与内存实现
src/index/bm25_store.py  BM25Index 构建、保存和查询
src/rag.py      单轮 RAG 检索与知识回答
src/chat/profile.py       训练需求槽位解析
src/chat/session.py       会话历史和记忆存储
src/chat/knowledge.py     对话层到 RAG 的适配
src/chat/query_planner.py 计划类问题的多查询规划
src/chat/prompts.py       提示词和上下文拼装
src/chat/providers.py     OpenAI 兼容模型适配器
src/chat/plan.py          无模型时的训练计划基线
src/chat/fallback.py      本地对话降级逻辑
src/chat/orchestrator.py  对话流程协调
src/chat/analytics.py     检索事件与回答反馈持久化
src/chat/api.py           聊天 API
src/chat/page.py          聊天页面
app.py          FastAPI 网页/API
```

## 说明

历史存储已升级为 SQLite，数据库位于 `db/chat_history.sqlite3`；服务重启后
历史对话、消息和训练资料仍会保留。

每个浏览器通过签名的 HttpOnly Cookie 获得独立匿名用户身份。会话列表、
读取、改名、删除、反馈和分析汇总均按该身份隔离。部署到公网时应配置
`APP_SECRET_KEY`，启用 HTTPS 后设置 `APP_COOKIE_SECURE=true`；未配置密钥时
应用会在 `db/.auth_secret` 本地生成。

历史管理 API：

```text
GET    /api/chat/conversations
POST   /api/chat/conversations
PATCH  /api/chat/conversations/{id}
GET    /api/chat/{id}
DELETE /api/chat/{id}
POST   /api/feedback
GET    /api/chat/analytics/summary
```

每条助手回答都有唯一 `request_id`，前端提供赞/踩、失败原因和可选备注。
检索链路会记录命中 ID、最终来源、模式、模型和耗时，反馈通过
`request_id` 与分析事件关联；模型调用还会记录输入和输出 Token 数量。
删除会话时会同步删除该会话的分析事件和反馈。`LLM_THINKING` 只对 DeepSeek
生效，其他 OpenAI 兼容供应商不会收到该专属参数。

对于伤病、疼痛和康复问题，系统不做医学诊断。难度字段目前由动作名称和动作
类型启发式推断；如果要用于正式训练计划，建议在原始数据中补充经过审核的动作
难度、禁忌人群和器械要求。
