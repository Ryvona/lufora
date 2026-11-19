"""Post the next due entry of queue.json to X (one per run).

Secrets (env): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET.
DRY_RUN=1 prints what would be posted without calling X.
Entries: {"at": ISO time, "text": str, "poll": [opts]?, "poll_minutes": int?,
          "posted_at"/"post_id": filled after posting}.
"""
import base64, hashlib, hmac, json, os, secrets, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

QUEUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue.json")
ENDPOINT = "https://api.x.com/2/tweets"
MIN_GAP = timedelta(hours=18)  # never burst through a backlog: at most one post per ~day


def q(s):
    return urllib.parse.quote(str(s), safe="~-._")


def oauth1_header(method, url, ck, cs, tk, ts, extra=None, nonce=None, stamp=None):
    """OAuth 1.0a HMAC-SHA1. `extra` = query/form params that are signed (none for a JSON body)."""
    oa = {"oauth_consumer_key": ck, "oauth_nonce": nonce or secrets.token_hex(16),
          "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(stamp or int(time.time())),
          "oauth_token": tk, "oauth_version": "1.0"}
    base_url, _, query = url.partition("?")
    params = dict(oa, **(extra or {}), **dict(urllib.parse.parse_qsl(query)))
    pstr = "&".join(f"{k}={v}" for k, v in sorted((q(k), q(v)) for k, v in params.items()))
    base = "&".join([method.upper(), q(base_url), q(pstr)])
    sig = base64.b64encode(hmac.new(f"{q(cs)}&{q(ts)}".encode(), base.encode(), hashlib.sha1).digest()).decode()
    oa["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{q(k)}="{q(v)}"' for k, v in sorted(oa.items()))


def parse(t):
    return datetime.fromisoformat(t)


def main():
    queue = json.load(open(QUEUE, encoding="utf-8"))
    now = datetime.now(timezone.utc)
    done = [parse(e["posted_at"]) for e in queue if e.get("posted_at")]
    if done and now - max(done) < MIN_GAP:
        print("last post too recent; waiting"); return
    due = [e for e in queue if not e.get("posted_at") and parse(e["at"]) <= now]
    if not due:
        print("nothing due"); return
    e = min(due, key=lambda x: parse(x["at"]))
    body = {"text": e["text"]}
    if e.get("poll"):
        body["poll"] = {"options": e["poll"], "duration_minutes": e.get("poll_minutes", 1440)}
    if os.environ.get("DRY_RUN") == "1":
        print("DRY RUN, would post:\n" + json.dumps(body, ensure_ascii=False, indent=2)); return
    env = os.environ
    auth = oauth1_header("POST", ENDPOINT, env["X_API_KEY"], env["X_API_SECRET"],
                         env["X_ACCESS_TOKEN"], env["X_ACCESS_TOKEN_SECRET"])
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": auth, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.load(r)
    except urllib.error.HTTPError as err:
        print(f"X API error {err.code}: {err.read().decode(errors='replace')}"); sys.exit(1)
    e["posted_at"] = now.isoformat(timespec="seconds")
    e["post_id"] = res["data"]["id"]
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2); f.write("\n")
    print("posted", e["post_id"])


if __name__ == "__main__":
    main()
