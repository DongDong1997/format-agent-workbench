# 项目进度存档

> 最后更新：2026-09-18
> 用途：切换对话/项目后快速恢复上下文

---

## 一、项目目标

做一个 **AI 文档排版工具**：用户提供**非正式**的格式要求（聊天记录、随手记、截图等，可能混杂格式要求和内容要求），AI 理解后按规范生成 Word 文档。

**核心痛点**：市面工具只做"格式迁移"（上传已排版文档 → 重排），无法处理"非正规叙述 → 正式格式"的语义归一化，也无法提取内容要求（如"封面必须含题目、姓名、学号"）。

---

## 二、技术选型与决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 底座项目 | format-agent-skill + format-agent-workbench | 已有成熟的多模态理解 + 确定性 OOXML 执行器 |
| 界面 | Streamlit（Workbench 自带） | 现成可用，无需从零开发 |
| 模型 | DeepSeek（deepseek-flash） | 支持多模态（图片输入），OpenAI 兼容，成本低 |
| 交互模式 | 表单式中间确认 | 非正式描述必然有模糊项，显式暴露给用户确认比模型猜更可靠 |
| 版本管理 | Fork 原作者仓库，保留 upstream | 便于同步原作者更新 |

**关键洞察**：多模态只是入口，真正难点是**语义归一化**——把"标题要显眼一点"翻译成"黑体二号加粗居中"。

---

## 三、已完成的工作

### 1. 环境搭建
- 克隆两个仓库到 F:\MyCode\auto_write\：
  - format-agent-skill/（Skill 本体）
  - format-agent-workbench/（Streamlit 界面）
- 在 workbench 创建 .venv，安装依赖
- 配置 .env：DeepSeek API（base_url / key / model=deepseek-flash）

### 2. 验证测试（已通过）
- DeepSeek 文本 JSON 调用
- DeepSeek 多模态（图片理解）
- 非正式描述 → 结构化格式（提取准确）
- 模糊项识别 + 建议值（6 条全部捕获）
- 内容要求提取（封面字段、摘要字数）
- 端到端：语义提取 → 确认合并 → FormatSpec 校验通过

### 3. 代码开发
新增文件：
- format-agent-workbench/core/semantic_extract.py
  - extract_semantic(spec_text, image_paths, llm) — 语义归一化主函数
  - 输出 format_spec + content_requirements + ambiguities
  - 含角色中文名、字号映射表（ROLE_LABELS / SIZE_PT_OPTIONS 等）

修改文件：
- format-agent-workbench/app.py
  - 插入"语义确认层"（在"开始排版"之后、Agent.run() 之前）
  - 用 st.session_state 管理确认状态
  - 三部分表单：已识别规则 / 模糊项确认 / 内容要求
  - 输入变化时自动重置确认状态
  - 确认后的 spec 回填到 kwargs["spec"]

### 4. 版本提交
- Commit：01d81a6 — feat: add semantic confirmation layer for informal format requirements
- 已推送到：https://github.com/DongDong1997/format-agent-workbench

---

## 四、Git 配置

origin   → git@github.com:DongDong1997/format-agent-workbench.git  （你的 fork）
upstream → https://github.com/KaguraNanaga/format-agent-workbench.git  （原作者）

同步原作者更新：
git fetch upstream
git merge upstream/main
git push origin main

---

## 五、环境与启动

工作目录：F:\MyCode\auto_write\format-agent-workbench

启动界面：
- 方式一：双击 启动工作台.bat
- 方式二：.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501

访问：http://127.0.0.1:8501

API 配置（.env，已被 gitignore）：
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-****（你的 key）
LLM_MODEL=deepseek-flash
LLM_TEMPERATURE=auto

---

## 六、待办事项

### 高优先级
1. 界面手动验证 — 尚未在浏览器真实操作过确认表单（Streamlit 的 text_area 无法用 JS 注入测试，必须手动）
   步骤：填入非正式要求 → 上传 docx → 点"开始排版" → 应出现确认表单
2. 内容要求填充 — 目前只展示 content_requirements，用户填的值还没接入文档生成

### 中优先级
3. 多模态入口 — 界面上还不支持上传图片/PDF 作为格式要求（后端 chat_vision_json 已就绪，只需接界面）
4. 外部依赖引导 — "页边距按学校标准"这类需外部信息的项，应引导用户补充

### 低优先级
5. 模糊项采纳/忽略的决策结果，目前未回写到最终 FormatSpec（只在内存中）

---

## 七、关键文件索引

| 文件 | 作用 |
|------|------|
| core/semantic_extract.py | 语义归一化（本项目新增核心） |
| app.py | Streamlit 界面（含确认层） |
| core/agent.py | 排版编排器（上游） |
| core/rules_from_text.py | 原始规范文字 → FormatSpec 的 prompt（上游） |
| core/schema.py | FormatSpec 校验器（上游） |
| core/llm.py | LLM 客户端（上游，支持 chat_json / chat_vision_json） |

---

## 八、已知限制

- Streamlit 的 text_area 无法用自动化脚本注入值——它只响应真实键盘事件。界面测试必须手动。
- DeepSeek 偶尔会在 JSON 里多返回 "type": "json_object" 回显字段，已在 _clean_json() 中过滤。
- 模型每次输出的模糊项措辞略有波动，属正常。
- format-agent-skill 只做"格式迁移"，不生成内容。内容生成是待开发的独立模块。

---

## 九、下次恢复时从这里开始

1. 启动 Workbench（见第五节）
2. 在浏览器手动测试确认表单（见第六节第 1 项）
3. 决定下一步做"内容要求填充"还是"多模态入口"
