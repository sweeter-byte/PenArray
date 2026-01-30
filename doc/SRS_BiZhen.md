# 软件需求规格说明书 (SRS) - 笔阵 (BiZhen)

**版本**: 1.0  
**日期**: 2026-01-30  
**密级**: 内部绝密 (Private & Confidential)

---

## 1. 引言 (Introduction)

### 1.1 项目背景 (Project Background)
“笔阵 (BiZhen)” 是一款专为中国高考（Gaokao）议论文写作设计的垂直领域多智能体（Multi-Agent）AI系统。当前通用大语言模型（LLM）在生成高考作文时，往往存在论证深度不足、缺乏逻辑结构、素材陈旧且未能精准对标评分标准等问题。本项目旨在通过模拟专家级写作团队的协作流程，利用国内领先的LLM技术，生成符合高考评分标准的高分议论文，辅助学生、教师及家长进行备考与教学。

### 1.2 产品范围 (Scope)
本系统专注于**高考议论文**的生成与优化。
- **核心功能**: 根据用户输入的题目（文本或图片），生成深度、文采、稳健三种风格的议论文，并提供评分与批注。
- **排他性声明**: 本系统**不**支持记叙文、散文、诗歌等其他体裁的生成与优化。
- **基础设施**: 仅依托中国大陆合规LLM API（如DeepSeek、阿里通义千问等），严禁使用OpenAI或Anthropic等境外API。

### 1.3 核心术语 (Definitions)
- **Multi-Agent System (MAS)**: 多智能体系统，指多个专门角色的AI代理（Agent）协作完成复杂任务的架构。
- **RAG (Retrieval-Augmented Generation)**: 检索增强生成，结合外部知识库（如名言警句、历史事实）来增强模型生成的准确性和丰富度。
- **Prompt Engineering**: 提示工程，设计和优化输入给AI模型的指令以获得特定输出的技术。

---

## 2. 总体描述 (Overall Description)

### 2.1 用户特征 (User Characteristics)
| 用户类别 | 特征描述 | 权限等级 |
| :--- | :--- | :--- |
| **学生 (Students)** | 主要终端用户，寻求高分范文与写作思路。 | 普通用户 (需持有Token) |
| **教师 (Teachers)** | 使用系统生成教学案例或批改辅助。 | 普通用户 (需持有Token) |
| **家长 (Parents)** | 辅助子女备考，关注生成质量。 | 普通用户 (需持有Token) |
| **管理员 (Administrator)** | 系统运维人员，负责Token发放与系统监控。 | 超级管理员 |

### 2.2 核心流程图 (High-Level Flow)
系统采用线性多智能体协作流：
1.  **输入**: 用户提交作文题目（Prompt/Image）。
2.  **策划 (Strategist)**: 审题，分析立意角度，确定中心论点。
3.  **搜查 (Librarian)**: 基于论点，通过RAG检索高频、新颖的论据素材。
4.  **构思 (Outliner)**: 生成结构化的写作大纲（如并列式、层进式）。
5.  **撰稿 (Writer)**: 根据大纲与素材撰写正文。
6.  **阅卷 (Grader)**: 依据高考评分标准打分。若分数未达标，触发由于反馈机制要求重写。
7.  **输出**: 展示最终的三篇范文及评语。

---

## 3. 功能性需求 (Functional Requirements)

### 3.1 身份验证模块 (Authentication)
本系统为私有化部署工具，不面向公众开放注册。
- **REQ-AUTH-01 (无注册入口)**: 登录页面不提供任何“注册”或“忘记密码”链接。
- **REQ-AUTH-02 (凭证登录)**: 用户仅能通过管理员分发的 **账号/密码** 组合或 **Access Token** 进行认证。
- **REQ-AUTH-03 (强制鉴权)**: 前端所有功能页面在加载前必须校验有效Session/Token，未登录用户将被强制重定向至登录页。

### 3.2 作文生成工作台 (Generation Workbench)
- **REQ-GEN-01 (多模态输入)**: 支持纯文本输入作文题目，或上传包含题目的图片（需集成OCR功能）。
- **REQ-GEN-02 (过程可视化)**:
    - 界面需实时展示当前工作的Agent状态（例如：“策划正在审题...”、“搜查员正在检索名言...”、“阅卷人正在评分...”）。
    - 建议使用步骤条（Stepper）或动态日志流（Log Stream）展示思考链（Chain of Thought）。
- **REQ-GEN-03 (生成控制)**: 用户无法干预中间生成过程，但可随时中止任务。

### 3.3 多维度结果展示 (Result Display)
- **REQ-RES-01 (三维范文)**: 系统必须针对同一题目输出三篇不同风格的议论文：
    1.  **深刻型 (Profound)**: 侧重哲学思辨与逻辑深度。
    2.  **文采型 (Rhetorical)**: 侧重辞藻华丽与修辞运用。
    3.  **稳健型 (Steady)**: 侧重结构工整，确保保底高分。
- **REQ-RES-02 (阅卷批注)**:
    - 每篇文章需附带“阅卷Agent”的评分（总分/分项分）。
    - 鼠标悬停在特定段落或句子时，显示阅卷人的具体批注（如：“此处论证有力”、“事例略显陈旧”）。

---

## 4. 系统架构与技术栈 (System Architecture)

### 4.1 技术选型
- **前端 (Frontend)**: React.js 或 Vue.js (Modern Web Framework)，强调响应式与交互体验。
- **后端 (Backend)**: Python (FastAPI 或 Django)，提供RESTful API支持。
- **智能体编排 (Orchestration)**:
    - **LangGraph** 或 **CrewAI**: 用于定义和管理Agent之间的状态流转与任务分发。
- **模型供应商 (Model Provider)**:
    - **Hybrid Strategy (混合策略)**:
        - **DeepSeek-R1 (Reasoner)**: 负责高逻辑密度的任务，包括“策划(Strategist)”、“构思(Outliner)”、“深刻型撰稿(Writer_Profound)”及“阅卷(Grader)”。
        - **DeepSeek-V3 (Chat)**: 负责创意生成及工具调用任务，包括“搜查(Librarian)”、“文采型撰稿(Writer_Rhetorical)”及“稳健型撰稿(Writer_Steady)”。
    - **约束**: 禁止配置OpenAI、Anthropic等境外模型API接口，确保合规性。
- **数据库 (Database)**:
    - **Vector DB** (Chroma / Milvus): 存储名言、历史素材、高分范文片段，用于RAG。
    - **Relational DB** (PostgreSQL / MySQL): 存储用户日志、Token信息、历史生成记录。

### 4.2 架构约束
- 采用微服务或模块化单体架构，确保各Agent逻辑解耦，便于独立优化Prompt。

---

## 5. 非功能性需求 (Non-functional Requirements)

### 5.1 安全性 (Security)
- **NFR-SEC-01**: API Key存储必须加密（如使用环境变量或密钥管理服务），严禁硬编码。
- **NFR-SEC-02**: 用户Access Token需具备时效性与一次性验证机制（如适用），防止重放攻击。

### 5.2 性能 (Performance)
- **NFR-PER-01**: 针对长文本生成（Long-context generation），前端需实现长连接（WebSocket/SSE）以避免HTTP超时，并提供用户友好的等待提示。
- **NFR-PER-02**: 系统需在 180秒 内完成全流程（策划至阅卷）的初次生成。

### 5.3 合规性 (Compliance)
- **NFR-COM-01**: 所有生成内容必须经过敏感词过滤模块。
- **NFR-COM-02**: 内容必须符合社会主义核心价值观，确保积极向上，严禁生成涉及政治敏感、暴力、色情等违规内容。

---

## 6. 附录 (Appendix)

### 6.1 用户故事示例 (User Story Sample)
> **作为** 一名高三语文教师，
> **我希望** 输入2024年某地模拟考作文题“关于‘躺平’与‘内卷’的辩证思考”，
> **以便于** 系统能分别为我提供一篇侧重思辨深度的范文和一篇侧重文采斐然的范文，让我能在课堂上直接作为讲评素材，向学生展示不同的写作路径。
