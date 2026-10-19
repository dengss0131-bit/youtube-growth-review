# YouTube 频道数据复盘工具 (YouTube Growth Review Tool)

一款为创作者打造的本地化、注重隐私的 YouTube 数据分析复盘工具。它能将从 YouTube Studio 导出的 CSV 数据转化为战略增长报告，帮助创作者了解是什么在驱动播放量、订阅量、包装表现（标题/封面）以及可复制的内容模式。

该应用通过 Python 在本地运行，不会将分析数据上传到任何第三方服务。
<img width="1580" height="1279" alt="image" src="https://github.com/user-attachments/assets/0612c274-1dfd-48fb-ad3f-de8ae3b3ccce" />

<img width="1560" height="1290" alt="image" src="https://github.com/user-attachments/assets/97c53d44-ca8a-446c-9340-7368c7f0c36f" />

<img width="1555" height="1290" alt="image" src="https://github.com/user-attachments/assets/a937b0e7-4fe2-4038-b39b-de6b6222261b" />

## 功能特点

- 上传或粘贴 YouTube Analytics（数据分析）的 CSV 数据
- 无需前端 JavaScript：报告由本地 Python HTTP 服务器生成
- 支持常见的 YouTube Studio 导出列，包括：
  - `Video title`（视频标题）
  - `Views`（观看次数）
  - `Subscribers`（订阅人数）
  - `Thumbnail impressions`（缩略图展示次数）
  - `Thumbnail click-through rate (%)`（缩略图点击率）
  - `Watch time (hours)`（观看时长/小时）
  - `Duration`（视频总时长）
- 自动跳过 `Total`（总计）汇总行
- 在需要时，可根据观看时长和观看次数自动估算平均观看时长
- 生成多维度的战略复盘报告：
  - 增长诊断
  - 真正的增长引擎
  - 高播放低涨粉的流量陷阱
  - 值得重新包装的隐藏宝藏
  - 高点击率的包装赢家
  - 题材四象限分析
  - 标题模式拆解
  - 可复用的标题公式
  - 系列化与栏目化建议
  - 下周内容方向规划
  - 旧视频二次包装候选
  - 具体的可执行动作

## 项目结构

```text
youtube-growth-review/
├── src/
│   ├── __init__.py
│   └── app.py
├── examples/
│   └── sample_youtube_analytics.csv
├── docs/
│   ├── export-youtube-analytics.md
│   └── user-guide-zh.md
├── tests/
│   └── test_parser.py
├── youtube_growth_review_server.py
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

## 快速开始

推荐使用 Python 3.10+。本工具无需任何第三方依赖。

```bash
python youtube_growth_review_server.py
```

然后在浏览器中打开：

```text
http://127.0.0.1:8765
```

## 文档

- [中文完整使用教程](docs/user-guide-zh.md)
- [如何导出 YouTube 数据分析 CSV](docs/export-youtube-analytics.md)

## 使用示例数据

本仓库包含虚构的示例数据：

```text
examples/sample_youtube_analytics.csv
```

您可以在网页界面中上传该文件，或者直接点击“使用示例数据”按钮来体验功能。

## 从 YouTube Studio 导出数据

请参阅：

```text
docs/export-youtube-analytics.md
```

## 隐私说明

本工具专为本地使用而设计。您的数据分析 CSV 文件只会保存在您的计算机上，除非您主动将其分享到其他地方。

为了降低意外将私人分析数据提交到代码库的风险，本仓库在 `.gitignore` 中默认排除了 CSV、TSV、XLS 和 XLSX 格式的文件。

## 开源协议

MIT 许可证 (MIT License)。
