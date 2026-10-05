"""WAF probing: send common attack signatures to identify whether they are blocked"""
import re


WAF_SIGNATURES = {
    "Cloudflare":   [r"cloudflare", r"cf-ray", r"__cfduid"],
    "AWS WAF":      [r"awselb", r"x-amzn-RequestId"],
    "ModSecurity":  [r"ModSecurity", r"mod_security", r"NAXSI"],
    "SafeDog":      [r"safedog", r"waf\.safedog", r"安全狗"],
    "D-Safe":       [r"d_safe", r"D盾"],
    "Alibaba Cloud WAF": [r"aliyun", r"alibaba", r"aliyundun"],
    "Tencent Cloud WAF": [r"tencent", r"qcloud"],
    "BT Panel WAF": [r"btwaf", r"bt\.waf"],
    "360 WAF":      [r"360wzws", r"wangzhan\.360"],
    "Imperva":      [r"imperva", r"incapsula"],
    "F5 BIG-IP":    [r"big-ip", r"BIGIP"],
}


# Text snippets typically found on interception / block pages.
# The Chinese entries are deliberately kept verbatim: Chinese WAF products and vendor
# block pages contain them exactly as written, so translating or removing them would
# make those pages undetectable. The English entries cover the rest of the world.
WAF_KEYWORDS = [
    "拦截", "阻断", "安全狗", "防火墙", "非法请求",
    "blocked", "forbidden", "access denied", "not acceptable",
    "security policy", "illegal request", "hacker detected",
]


class WAFDetector:
    def __init__(self, requester, log=None):
        self.req = requester
        self.log = log
        self.detected = None

    def detect(self):
        print("[*] WAF probing...")
        payloads = [
            "' OR 1=1--",
            "<script>alert(1)</script>",
            "../../etc/passwd",
            "1 AND SLEEP(5)",
            "UNION SELECT NULL",
        ]
        scores = {}
        for p in payloads:
            r = self.req.send(p, use_cache=False)
            if r["status"] == -1:
                continue
            text = r["text"]
            if r["status"] in (403, 406, 501, 999):
                scores["generic"] = scores.get("generic", 0) + 1
            for waf, patterns in WAF_SIGNATURES.items():
                for pat in patterns:
                    if re.search(pat, text, re.IGNORECASE):
                        scores[waf] = scores.get(waf, 0) + 1
            if any(k in text.lower() for k in WAF_KEYWORDS):
                scores["keyword_waf"] = scores.get("keyword_waf", 0) + 1

        if scores:
            top = max(scores, key=scores.get)
            self.detected = top
            print(f"[!] WAF signature: {top} (matched {scores[top]} times)")
            print("[!] Suggestion: --stealth --delay 2 --random-agent --proxy-file")
        else:
            print("[+] No obvious WAF signature detected")
        return self.detected

    def is_waf_response(self, response):
        if response["status"] in (403, 406, 501, 999):
            return True
        text = response["text"]
        for waf, patterns in WAF_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    return True
        if any(k in text.lower() for k in WAF_KEYWORDS):
            return True
        return False