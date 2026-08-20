# 上海地铁最短路径数据规范

## 目标

建立只涵盖地铁系统的可审计网络数据。官方上海地铁接口是已运营车站与线路顺序的唯一骨架来源；本仓库的配线 PDF 是区间距离和未运营地铁线路的交叉核对来源。

## 范围

- 默认只计算 `operating` 的地铁线路。
- `planned`、`under_construction`、`suspended` 等非运营线路保留在数据中，但默认禁用；调用方通过 `include_statuses` 显式纳入。
- 不收录市域、局域、国铁、机场联络线等非地铁系统。
- 第一版只最小化总区间距离；换乘边的权重为 `0`，不加入换乘时间、步行距离或等候惩罚。

## 数据契约

每条线路保存 `id`、`name`、`service_status`、`source` 和有序 `station_ids`。车站的稳定 `id` 直接使用官方站点 ID，另保存中文 `name`。相邻站边保存 `from`、`to`、`line_id`、`distance_m`、`distance_source` 与 `verification`。所有换乘关系单独写入 `transfers`，其两端均为官方站点 ID；第一版的每条换乘边均为 `distance_m: 0`。

- `distance_m` 未核对前必须为 `null`，不得用坐标或图面比例估算替代。
- 路径请求若经过 `distance_m: null` 的边，必须失败并说明缺少哪一段距离。
- 每次官方抓取都保存带 UTC 时间戳的原始快照和响应哈希；人工 PDF 录入距离需记录图中标注值及复核状态。
