# 各平台后台导出数据字段对照表

本文档用于帮助你从各平台后台导出数据，并理解工具如何把不同平台的字段映射到统一指标。测试时照着「最小可用」清单导出即可。

> 工具对字段名的匹配是**归一化后包含匹配**：忽略大小写、空格、`%`、括号，所以字段名略有差异（例如 `播放量`、`播放量(次)`、`播放 量`）都能识别。

---

## 一、统一指标层

工具内部把所有平台归一化到同一套指标。你在后台导出时，只要字段能对应到下面任意一个指标，工具就能用它：

| 统一指标 | 含义 | 用途 |
|---|---|---|
| `title` | 标题 | 标题模式分析、题材推断 |
| `views` | 播放量 / 阅读量 | 核心播放指标（必需） |
| `subscribers_gained` | 涨粉数 / 新增关注 | 转粉效率（必需） |
| `ctr` | 点击率 | 包装效率（部分平台无） |
| `impressions` | 曝光量 / 展现量 | 系统推荐机会 |
| `retention` | 完播率 / 完读率 | 内容质量 |
| `avg_view_duration` | 平均观看 / 阅读时长 | 内容质量 |
| `video_duration` | 内容总时长 | 反推完播率 |
| `likes` | 点赞 | 互动质量 |
| `comments` | 评论 | 互动质量 |
| `shares` | 分享 / 转发 | 互动质量 |
| `favorites` | 收藏 | 互动质量 |
| `publish_date` | 发布时间 | 时间维度 |
| `topic` / `series` / `thumbnail_type` / `hook_type` | 题材 / 系列 / 封面类型 / 开头类型 | 可选手动补充，用于深度策略分析 |

**判断优先级**：无 `ctr`（点击率）的平台，工具会自动改用「互动率」（点赞+评论+分享+收藏 ÷ 播放量）替代包装效率判断。

---

## 二、各平台字段对照表

### 1. YouTube（YouTube Studio → 分析 → 高级模式）

导出维度选 **Video / 视频**。

| 后台字段名 | 映射指标 | 重要度 |
|---|---|---|
| `Video title` | title | ✅ 必需 |
| `Content` / `Video` | video_id | ○ 可选 |
| `Views` | views | ✅ 必需 |
| `Subscribers` | subscribers_gained | ✅ 必需 |
| `Thumbnail click-through rate (%)` | ctr | ⭐ 推荐 |
| `Thumbnail impressions` | impressions | ⭐ 推荐 |
| `Average percentage viewed` | retention | ⭐ 推荐 |
| `Average view duration` | avg_view_duration | ⭐ 推荐 |
| `Watch time (hours)` | watch_time_hours | ○ 可选 |
| `Duration` | video_duration | ○ 可选 |
| `Likes` | likes | ⭐ 推荐 |
| `Comments` | comments | ○ 可选 |
| `Video publish time` | publish_date | ○ 可选 |

**最小可用**：`Video title` + `Views` + `Subscribers`（+ `Thumbnail click-through rate (%)` 更佳）

---

### 2. 抖音（创作者中心 → 数据中心 → 内容数据）

| 后台字段名 | 映射指标 | 重要度 |
|---|---|---|
| `作品标题` | title | ✅ 必需 |
| `播放量` | views | ✅ 必需 |
| `涨粉数` | subscribers_gained | ✅ 必需 |
| `完播率` | retention | ⭐ 推荐 |
| `平均播放时长` | avg_view_duration | ⭐ 推荐 |
| `展现量` | impressions | ⭐ 推荐 |
| `点赞数` | likes | ⭐ 推荐 |
| `评论数` | comments | ⭐ 推荐 |
| `分享数` | shares | ⭐ 推荐 |
| `收藏数` | favorites | ○ 可选 |
| `发布时间` | publish_date | ○ 可选 |

**最小可用**：`作品标题` + `播放量` + `涨粉数`（+ `完播率` 更佳）

> 抖音后台通常不直接给「点击率」，工具会自动用互动率判断包装效果。

---

### 3. 小红书（创作者中心 → 数据中心 → 笔记数据）

| 后台字段名 | 映射指标 | 重要度 |
|---|---|---|
| `笔记标题` | title | ✅ 必需 |
| `阅读量` | views | ✅ 必需 |
| `涨粉数` | subscribers_gained | ✅ 必需 |
| `曝光量` | impressions | ⭐ 推荐 |
| `点击率` | ctr | ⭐ 推荐 |
| `平均阅读时长` | avg_view_duration | ⭐ 推荐 |
| `完读率` | retention | ○ 可选 |
| `点赞` | likes | ⭐ 推荐 |
| `收藏` | favorites | ⭐ 推荐 |
| `评论` | comments | ⭐ 推荐 |
| `分享` | shares | ○ 可选 |
| `发布时间` | publish_date | ○ 可选 |

**最小可用**：`笔记标题` + `阅读量` + `涨粉数`（+ `点击率` / `曝光量` 更佳）

---

### 4. B站（创作中心 → 数据中心 → 稿件数据）

| 后台字段名 | 映射指标 | 重要度 |
|---|---|---|
| `稿件标题` | title | ✅ 必需 |
| `播放量` | views | ✅ 必需 |
| `新增关注` | subscribers_gained | ✅ 必需 |
| `完播率` | retention | ⭐ 推荐 |
| `平均播放时长` | avg_view_duration | ⭐ 推荐 |
| `点赞` | likes | ⭐ 推荐 |
| `投币` | （未映射，忽略即可） | — |
| `收藏` | favorites | ⭐ 推荐 |
| `分享` | shares | ⭐ 推荐 |
| `评论` | comments | ⭐ 推荐 |
| `发布时间` | publish_date | ○ 可选 |

**最小可用**：`稿件标题` + `播放量` + `新增关注`（+ `完播率` 更佳）

> B站「投币」是平台特色指标，当前工具暂不纳入互动率计算。

---

### 5. 视频号（视频号助手 → 数据中心 → 视频数据）

| 后台字段名 | 映射指标 | 重要度 |
|---|---|---|
| `视频标题` | title | ✅ 必需 |
| `播放量` | views | ✅ 必需 |
| `涨粉` | subscribers_gained | ✅ 必需 |
| `完播率` | retention | ⭐ 推荐 |
| `点赞` | likes | ⭐ 推荐 |
| `评论` | comments | ⭐ 推荐 |
| `转发` | shares | ⭐ 推荐 |
| `收藏` | favorites | ○ 可选 |
| `发布时间` | publish_date | ○ 可选 |

**最小可用**：`视频标题` + `播放量` + `涨粉`（+ `完播率` 更佳）

---

### 6. TikTok（TikTok Studio / Creator Center → Analytics → Content）

| 后台字段名 | 映射指标 | 重要度 |
|---|---|---|
| `Title` | title | ✅ 必需 |
| `Views` | views | ✅ 必需 |
| `Followers gained` | subscribers_gained | ✅ 必需 |
| `Average watch time` | avg_view_duration | ⭐ 推荐 |
| `Retention rate` | retention | ⭐ 推荐 |
| `Likes` | likes | ⭐ 推荐 |
| `Comments` | comments | ⭐ 推荐 |
| `Shares` | shares | ⭐ 推荐 |
| `Date` | publish_date | ○ 可选 |

**最小可用**：`Title` + `Views` + `Followers gained`（+ `Average watch time` 更佳）

---

## 三、快速测试清单

测试时按这个顺序，从最简单开始：

1. **先点「使用示例数据」**：页面下拉框切换平台 → 点按钮，确认报告能生成。
2. **再上传一个平台的真实导出**：优先选你手头最方便导出的平台（建议 YouTube，字段最全）。
3. **核对「识别平台」提示**：报告顶部绿色状态条会显示识别到的平台和内容条数，看是否和你导出的一致。
4. **字段不全时降级测试**：故意只导出「标题 + 播放量 + 涨粉数」三列，确认工具仍能跑（只是分析变浅）。

## 四、导出注意事项

- **时间范围**：建议导出最近 7 天或 28 天，样本太少（< 5 条）时四象限和题材分析会不稳定。
- **导出格式**：CSV 或 TSV（制表符）都支持，Excel 另存为 CSV 即可。
- **不要手填汇总行**：工具会自动跳过 `Total` / `合计` / `总计` 行，导出时保留或删除都行。
- **字段名别改**：保持后台默认字段名，工具靠字段名识别；想补深度字段可另加 `题材`/`系列` 等列。
- **隐私**：数据只在本地处理，不会上传到任何服务器。
