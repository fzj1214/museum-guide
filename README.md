# AI 博物馆导览 MVP

基于 Gradio + Supabase + ModelScope API + 智谱 GLM‑TTS 的“拍画即听”智能导览系统。

## 功能特性

- **艺术品自动识别**：通过 Qwen‑VL 结构化识别 + 文本向量检索
- **展厅定位**：自动关联艺术品所在展厅信息
- **风格化语音讲解**：
  - 专业版：艺术史专家视角的深度解读
  - 趣解版：轻松有趣的第一人称讲述

## 技术架构

```
前端 (Gradio) → 业务逻辑层 (Python) → 外部服务层
                    │
    ┌───────────────┼────────────────────┬─────────────────────┐
    │               │                    │                     │
    ▼               ▼                    ▼                     ▼
Supabase       ModelScope API      ModelScope API         智谱开放平台
(PostgreSQL +  (Qwen‑VL 识别)      (Embedding/LLM)        (GLM‑TTS 语音合成)
 pgvector)
```

## 项目结构

```
museum-guide-mvp/
├── app.py                      # Gradio 主入口
├── requirements.txt            # 依赖清单
├── config.py                   # 配置管理
├── services/                   # 核心服务
│   ├── supabase_client.py      # Supabase 客户端
│   ├── modelscope_client.py    # ModelScope API 客户端
│   ├── recognition.py          # 图像识别服务
│   ├── narration.py            # 讲解生成服务
│   └── tts.py                  # TTS 语音合成服务
├── utils/                      # 工具函数
│   ├── image_utils.py          # 图像处理工具
│   └── api_utils.py            # API 请求工具
├── prompts/                    # Prompt 模板
│   ├── professional.txt
│   └── casual.txt
├── data/                       # 初始数据
│   ├── halls.json
│   └── artworks.json
├── sql/                        # SQL 迁移脚本
│   ├── 001_enable_pgvector.sql
│   ├── 002_create_tables.sql
│   ├── 003_create_functions.sql
│   ├── 004_setup_rls.sql
│   └── 005_seed_data.sql
└── scripts/                    # 设置脚本
    ├── generate_embeddings.py
    └── setup_storage.py
```

## 快速开始

### 1. 环境配置

```bash
cd museum-guide-mvp

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 2. 数据库设置

在 Supabase SQL Editor 中依次执行 `sql/` 目录下的脚本：

1. `001_enable_pgvector.sql` - 启用向量扩展
2. `002_create_tables.sql` - 创建数据表
3. `003_create_functions.sql` - 创建 RPC 函数
4. `004_setup_rls.sql` - 设置行级安全
5. `005_seed_data.sql` - 插入示例数据

### 3. 存储配置

```bash
# 创建音频缓存 bucket
python scripts/setup_storage.py
```

### 4. 生成向量嵌入

```bash
# 为 artworks 表生成文本向量（embedding 列，维度默认 1536）
python scripts/generate_embeddings.py
```

### 5. 启动应用

```bash
python app.py
```

访问 http://localhost:7860 使用应用。

## 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `SUPABASE_URL` | Supabase 项目 URL | 是 |
| `SUPABASE_KEY` | Supabase anon key | 是 |
| `MODELSCOPE_API_KEY` | ModelScope API 密钥（识别/讲解/向量） | 是 |
| `MODELSCOPE_API_BASE` | ModelScope API 入口 (默认 https://api-inference.modelscope.cn/v1) | 否 |
| `VLM_MODEL` | 图像识别模型 (默认 Qwen/Qwen2.5-VL-7B-Instruct) | 否 |
| `NARRATION_MODEL` | 讲解生成模型 (默认 Qwen/Qwen3-32B) | 否 |
| `TEXT_EMBEDDING_MODEL` | 文本向量模型 (默认 Qwen/Qwen3-Embedding-4B) | 否 |
| `TEXT_EMBEDDING_DIM` | 向量维度 (默认 1536) | 否 |
| `SIMILARITY_THRESHOLD` | 向量相似度阈值 (默认 0.8) | 否 |
| `ZHIPU_API_KEY` | 智谱 API Key（语音合成） | 是 |
| `ZHIPU_API_BASE` | 智谱 API 入口 (默认 https://open.bigmodel.cn/api/paas/v4) | 否 |
| `TTS_MODEL` | TTS 模型 (默认 glm-tts) | 否 |
| `TTS_PROFESSIONAL_VOICE` | 专业版音色 (默认 tongtong) | 否 |
| `TTS_CASUAL_VOICE` | 趣解版音色 (默认 xiaochen) | 否 |
| `AUDIO_BUCKET` | 音频存储 bucket 名称 | 否 |

## 魔搭创空间部署

1. 在魔搭创空间创建新应用
2. 上传项目文件
3. 在 Settings → Environment Variables 中配置环境变量
4. 启动应用

## 技术说明

### 运行流程

1. 用户上传图片
2. **识别（VLM）**：调用 `VLM_MODEL` 输出结构化 JSON（名称、作者、年代、风格、简述）
3. **向量检索**：将识别结果拼成文本后，调用 `TEXT_EMBEDDING_MODEL` 得到 1536 维向量，在 Supabase(pgvector) 里执行相似度检索
4. **信息回填**：如果匹配到数据库作品，读取 artworks + halls 完整信息；否则使用 VLM 的识别结果作为兜底
5. **讲解生成**：调用 `NARRATION_MODEL` 生成“专业版/趣解版”文本
6. **语音合成**：调用智谱 `glm-tts` 生成 wav，并进行缓存

### 音频缓存策略

- 首次请求时生成语音并上传到 Supabase Storage
- 后续请求读取 `audio_cache` 表中的 URL，并下载为音频数据返回给前端播放
- 减少 TTS API 调用，提升响应速度

## 许可证

MIT License
