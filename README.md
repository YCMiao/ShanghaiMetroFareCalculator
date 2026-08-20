# Shanghai Metro Fare Calculator

输入上海地铁起点与终点站，计算仅按线路区间里程得到的理论最短路径与票价。

当前版本覆盖 1–18 号线及浦江线。换乘站以官方站点 ID 分开建模，换乘距离暂按 0 米计算；因此结果不包含站内步行距离、换乘时间或最少换乘偏好。

## 运行

需要 Python 3，无额外依赖。

```bash
python3 route_server.py
```

然后在浏览器打开 <http://127.0.0.1:8766>。

也可以直接在终端查询：

```bash
python3 route.py 莘庄 滴水湖
```

## 部署到 Render

创建 **Web Service**，连接本仓库，并填写：

- Runtime：`Python 3`
- Build Command：留空
- Start Command：`python3 route_server.py --host 0.0.0.0 --port $PORT`

服务器会读取 Render 自动提供的 `PORT` 环境变量。

## 票价

- 0–6 公里：3 元
- 超过 6 公里后，每满不足 10 公里加收 1 元

## 项目结构

- `data/metro-network.json`：最短路径计算使用的地铁图数据与站间距离。
- `data/metro-map.json`：前端线路图使用的站点坐标与线路颜色。
- `route.py`：Dijkstra 最短路径与票价计算。
- `route_server.py`：本地网页服务与路线查询接口。
- `ui/route/`：网页界面。

## 数据说明

本站点与线路信息基于上海地铁官方公开数据整理；站间距离按配线图人工复核录入。项目用于理论距离计算，不作为运营信息或票务依据。
