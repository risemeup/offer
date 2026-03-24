# Redis 面试核心薄弱点复习笔记

> 本笔记基于模拟面试生成，主要针对回答不够完整、不太清晰或直接要求给出答案的知识点进行了梳理，重点为**内存淘汰策略**、**RedLock 算法**、**大 Key / 热 Key 问题**以及**集群路由机制**。

---

## 核心薄弱点一：Redis 特殊数据类型

### 五大基础类型之外的补充类型
*   **Bitmap**：位操作，适合用户签到、布隆过滤器等场景。
*   **HyperLogLog**：基数统计，适合 UV 统计等不要求精确的大数据量去重。
*   **GeoHash**：地理位置，支持"附近的人"等 LBS 场景。
*   **Stream**（5.0+）：更完善的消息队列，支持消费者组，弥补了 List 做消息队列的不足。

---

## 核心薄弱点二：内存淘汰策略

### 1. 八种淘汰策略

```
noeviction        → 内存满了直接报错，不淘汰（默认）

# 从设置了过期时间的 key 中淘汰
volatile-lru      → LRU（最近最久未使用）
volatile-lfu      → LFU（最近最少使用）
volatile-ttl      → 淘汰 TTL 最短的
volatile-random   → 随机淘汰

# 从所有 key 中淘汰
allkeys-lru       → LRU
allkeys-lfu       → LFU
allkeys-random    → 随机淘汰
```

### 2. LRU vs LFU 核心区别
*   **LRU（Least Recently Used）**：看**最后一次访问时间**，淘汰最久没被访问的。
*   **LFU（Least Frequently Used）**：看**访问频率**，淘汰访问次数最少的。
*   **举例**：某个 key 一个月前被频繁访问了 10 万次，最近 1 小时没人访问。LRU 会优先淘汰它（很久没用），LFU 会倾向保留它（频率高）。

### 3. 实际选型建议

| 场景 | 推荐策略 |
|---|---|
| 通用缓存，大部分 key 都有过期时间 | `volatile-lru`（最常用） |
| 所有 key 都当缓存用，没设过期时间 | `allkeys-lru` |
| 有明显热点数据，希望热点不被淘汰 | `allkeys-lfu` |
| 数据不允许丢失，宁可报错 | `noeviction` |

### 4. 近似 LRU
Redis 的 LRU 并不是精确 LRU，而是**近似 LRU**——随机采样 N 个 key（默认 5 个），淘汰其中最久未访问的，避免了维护全局链表的开销。

---

## 核心薄弱点三：RedLock 算法

### 1. 解决什么问题
单机 Redis 作为锁服务存在**单点故障**问题，主从切换时可能导致锁丢失。

### 2. 核心流程
1.  部署 **N 个独立的 Redis 实例**（通常 5 个，互不主从）。
2.  客户端依次向所有实例发起加锁请求，记录总耗时。
3.  如果在**超过半数（N/2+1）** 的实例上加锁成功，且总耗时小于锁的过期时间，才认为加锁成功。
4.  释放锁时向所有实例发送释放请求。

### 3. 争议
Martin Kleppmann 曾撰文质疑其在网络分区和 GC 停顿下的安全性。实际生产中用得不多，很多团队会选择 **ZooKeeper 或 etcd** 做更强一致性的分布式锁。

---

## 核心薄弱点四：混合持久化细节

### AOF 重写时的混合格式（4.0+）
触发 `BGREWRITEAOF` 时，生成的**单个 AOF 文件**内容分两部分：

```
┌─────────────────────────────┐
│   RDB 二进制格式数据         │  ← fork 时刻的全量内存快照（紧凑、加载快）
├─────────────────────────────┤
│   AOF 增量命令               │  ← 重写期间新产生的写命令（保证数据完整）
└─────────────────────────────┘
```

**具体流程：**
1.  fork 子进程，子进程把当前内存中的全量数据以 RDB 格式写入新 AOF 文件的开头。
2.  在子进程写 RDB 的同时，主进程仍在接收新的写命令，这些命令暂存到 replication buffer。
3.  子进程写完 RDB 后，主进程把缓冲区中积累的增量命令以 AOF 文本格式追加到文件末尾。

**恢复时：** 先加载 RDB 部分（速度快），再回放 AOF 命令（数据完整）。

### AOF 重写触发条件
不是按固定时间间隔，而是根据**文件大小增长**触发：
```conf
auto-aof-rewrite-percentage 100    # AOF 文件比上次重写后增长了 100%
auto-aof-rewrite-min-size 64mb     # 且文件大小 ≥ 64MB
```
两个条件**同时满足**才触发。生产中 `min-size` 通常调大到 1GB~4GB，避免频繁重写。

---

## 核心薄弱点五：主从复制 repl_backlog

### repl_backlog 的作用
**支持断线后的增量同步，避免全量同步。**

```
repl_backlog（环形缓冲区，默认 1MB）

  ┌──────────────────────────────────┐
  │ cmd1 cmd2 cmd3 cmd4 cmd5 cmd6 ...│  ← 主节点不断写入新命令
  └──────────────────────────────────┘
         ▲                    ▲
     从节点的 offset      主节点的 offset
     (断线前同步到这)     (当前最新位置)
```

### 断线重连流程
1.  从节点重连，带着自己的 offset 发送 `PSYNC <replid> <offset>`。
2.  主节点检查 offset 是否还在 backlog 范围内。
    *   **在** → 增量同步，把 offset 之后的命令发给从节点。
    *   **不在**（已被覆盖）→ 退化为全量同步。

### 生产调优
*   默认 1MB 太小，写入量大的场景很容易被覆盖。
*   计算公式：`repl-backlog-size ≥ 主节点每秒写入量 × 预估最大断线秒数`。

---

## 核心薄弱点六：Raft 算法与集群路由

### 1. Raft 算法简介
分布式一致性算法，用于在多个节点中选出一个 leader。

**三个角色：**
*   **Leader**：唯一决策者，处理所有请求。
*   **Follower**：被动接收 Leader 的心跳和日志。
*   **Candidate**：竞选中的临时状态。

**选举流程：**
1.  Follower 超时没收到心跳 → 转变为 Candidate，发起投票。
2.  向其他节点发送 RequestVote。
3.  获得多数票（N/2+1）→ 成为 Leader；否则重新选举（随机超时避免活锁）。

在哨兵场景中，多个哨兵用 Raft 选出一个 leader 哨兵来执行主从切换操作。

### 2. 集群路由方案

#### 方案一：智能客户端（主流）
Jedis Cluster、Lettuce、Redisson 等主流客户端**内置了槽位路由**：
1.  客户端启动时向任意节点发送 `CLUSTER SLOTS`，获取完整槽位映射表。
2.  本地缓存路由表：`slot 0~5460 → node1, slot 5461~10922 → node2 ...`
3.  每次请求先算 `CRC16(key) % 16384`，直接发到对应节点。
4.  如果收到 `MOVED` → 更新本地路由表。

#### 方案二：Proxy 代理层（对客户端透明）
```
客户端 → Proxy → Redis Cluster
```
常见方案：Codis（豌豆荚）、Twemproxy（Twitter）、Predixy。
好处是客户端不感知集群，缺点是多一层网络跳转有性能损耗。

#### MOVED vs ASK
*   **MOVED**：槽位已永久迁移，客户端应更新本地路由表。
*   **ASK**：槽位正在迁移中，临时重定向，不更新路由表。

---

## 核心薄弱点七：大 Key 与热 Key 问题

### 1. 大 Key（Big Key）

**判定标准：**
*   String 类型 value 超过 **10KB**。
*   Hash、List、Set、ZSet 元素数量超过 **5000**。

**危害：** 读写耗时长阻塞单线程；删除时卡顿严重；拖慢主从同步和数据迁移。

**发现方式：**
```bash
redis-cli --bigkeys                  # 自带扫描
redis-cli MEMORY USAGE <key>         # 精确查看单个 key
```

**解决方案：**
*   **拆分**：大 Hash 按 ID 取模分桶，如 `user:info` → `user:info:0`, `user:info:1` ...
*   **异步删除**：`UNLINK` 代替 `DEL`，后台线程处理不阻塞主线程。
*   **压缩**：String 类型先 gzip 压缩再存储。

### 2. 热 Key（Hot Key）

**判定标准：** 某个 key 被高频访问，QPS 远高于其他 key（如热搜、秒杀商品）。

**危害：** 该 key 所在节点负载飙升，集群负载不均衡，严重时单节点被打满。

**发现方式：**
```bash
redis-cli --hotkeys                  # Redis 4.0+ 内置
```

**解决方案：**

| 方案 | 做法 |
|---|---|
| **本地缓存** | 应用层加一层本地缓存（Caffeine、Guava），热 Key 直接本地命中 |
| **读副本分散** | 把热 Key 复制多份 `hot_key:0`、`hot_key:1`... 客户端随机读不同副本，分散到多个节点 |
| **多级缓存** | CDN → 本地缓存 → Redis → DB，层层拦截 |

#### 读副本分散详解

**核心思路：** 把一个热 Key 复制成 N 份，后缀不同使其落到不同槽位 / 节点。

```java
// 读取时：随机选一个副本
public String getHotKey(String key) {
    int suffix = ThreadLocalRandom.current().nextInt(REPLICA_COUNT);
    return redis.get(key + ":" + suffix);
}

// 写入时：所有副本都要更新
public void setHotKey(String key, String value, int expireSeconds) {
    for (int i = 0; i < REPLICA_COUNT; i++) {
        redis.setex(key + ":" + i, expireSeconds, value);
    }
}
```

**注意事项：**
*   写放大：写 N 份，适合**读多写少**场景。
*   一致性：多副本短暂不一致，业务需能容忍。
*   副本数计算：`副本数 ≥ 热 Key QPS / 单节点 QPS 上限`。
*   过期时间加随机值：`expire = base + random(0, 60)`，避免所有副本同时过期。
