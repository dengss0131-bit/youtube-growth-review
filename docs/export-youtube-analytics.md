# 导出 YouTube Analytics 数据

本指南说明如何从 YouTube Studio 导出视频级分析数据，供复盘工具使用。

## 推荐导出方式

1. 打开 YouTube Studio。
2. 进入 **Analytics / 分析**。
3. 打开 **Advanced mode / 查看更多**。
4. 选择时间范围，例如最近 7 天、28 天或 90 天。
5. 将主维度设置为 **Video / 视频**。
6. 将当前视图导出为 CSV。
7. 将 CSV 上传或粘贴到本地复盘工具。

## 推荐导出的字段

工具在导出包含以下字段时效果最佳：

| 字段 | 用途 |
|---|---|
| Video title | 识别视频并分析标题模式 |
| Views | 衡量触达 |
| Subscribers | 衡量订阅转化 |
| Thumbnail impressions | 衡量推荐机会 |
| Thumbnail click-through rate (%) | 衡量标题/缩略图包装 |
| Watch time (hours) | 反推平均观看时长 |
| Duration | 反推平均完播率 |
| Comments | 衡量讨论深度 |
| Likes | 衡量正向反馈 |
| Video publish time | 对比发布时间段 |

## 可选手动补充字段

你可以手动添加以下字段，以获得更准确的策略分析：

| 字段 | 示例 |
|---|---|
| topic | AI productivity、open-source tools、creator workflow |
| series | Tool review、tutorial、growth analysis |
| thumbnail_type | comparison table、bold text、product screenshot |
| hook_type | real test、problem diagnosis、conclusion first |

如果缺少这些字段，工具会根据标题推断粗略分类。
