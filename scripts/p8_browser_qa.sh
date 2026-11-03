#!/usr/bin/env bash
# P8 browser QA — servers + browser + teardown in ONE invocation.
# Loads every public page at 1440px and 390px: console errors, 404 assets,
# horizontal overflow. Screenshots key pages for visual QA.
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="$KIT/site"
OUT="$KIT/scripts/p8_qa_out"
rm -rf "$OUT"; mkdir -p "$OUT"
PORT=8097
BASE="http://127.0.0.1:$PORT"

cd "$SITE"
python3 -m http.server "$PORT" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
sleep 1

PAGES=$(ls *.html | tr '\n' ' ')
FAILS=0
PREV404=""

check_page () {  # $1=page $2=width $3=label
  local page="$1" w="$2" tag="$3"
  agent-browser open "$BASE/$page" >/dev/null 2>&1
  agent-browser wait --load networkidle >/dev/null 2>&1
  sleep 0.8
  # console errors
  local errs
  errs=$(agent-browser errors --json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
items = d.get('errors', [])
print(len(items))" 2>/dev/null || echo "X")
  # NEW 404 assets since the previous page (request list accumulates per session)
  local nf new404
  nf=$(agent-browser network requests --json 2>/dev/null | python3 -c "
import json,sys
prev = set('''$PREV404'''.split())
try: d=json.load(sys.stdin)
except Exception: print('X'); sys.exit()
bad = sorted({r['url'] for r in d.get('data',{}).get('requests',[]) if str(r.get('status','')) == '404'} - prev)
print(len(bad)); print('\n'.join(bad), file=sys.stderr)" 2>"$OUT/last404.txt" || echo "X")
  new404=$(cat "$OUT/last404.txt" 2>/dev/null | head -2 | tr '\n' ' ')
  # horizontal overflow
  local ovf
  ovf=$(agent-browser eval "document.documentElement.scrollWidth - document.documentElement.clientWidth" 2>/dev/null | tail -1)
  # remember the 404 set for the next page
  PREV404=$(agent-browser network requests --json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit()
print(' '.join(sorted({r['url'] for r in d.get('data',{}).get('requests',[]) if str(r.get('status','')) == '404'})))" 2>/dev/null || echo "")
  local status=OK
  if [ "$errs" != "0" ] || [ "$nf" != "0" ] || [ "$(echo "$ovf > 1" | bc 2>/dev/null || echo 0)" = "1" ]; then
    status=FAIL; FAILS=$((FAILS+1))
    [ "$errs" != "0" ] && agent-browser errors 2>/dev/null | head -3
  fi
  agent-browser errors --clear >/dev/null 2>&1
  printf "%-4s %-6s %-42s errors=%s new404=%s overflow=%spx %s\n" "$status" "$tag" "$page" "$errs" "$nf" "$ovf" "$new404"
}

echo "== 1440px sweep =="
agent-browser set viewport 1440 900 >/dev/null 2>&1
for p in $PAGES; do check_page "$p" 1440 desk; done

echo ""
echo "== 390px sweep =="
agent-browser set viewport 390 844 >/dev/null 2>&1
for p in $PAGES; do check_page "$p" 390 mob; done

echo ""
echo "== screenshots (390px) =="
agent-browser set viewport 390 844 >/dev/null 2>&1
for p in index.html join-us.html contact.html partners.html policy-data-privacy.html results.html the-squad.html core-values.html feminin.html chairman-message.html our-story.html leadership-governance.html; do
  agent-browser open "$BASE/$p" >/dev/null 2>&1
  agent-browser wait --load networkidle >/dev/null 2>&1
  sleep 0.8
  agent-browser screenshot "$OUT/mob-${p%.html}.png" >/dev/null 2>&1
done
echo "saved to $OUT/mob-*.png"

echo ""
echo "== screenshots (1440px) =="
agent-browser set viewport 1440 900 >/dev/null 2>&1
for p in index.html join-us.html contact.html partners.html policy-data-privacy.html results.html; do
  agent-browser open "$BASE/$p" >/dev/null 2>&1
  agent-browser wait --load networkidle >/dev/null 2>&1
  sleep 0.8
  agent-browser screenshot "$OUT/desk-${p%.html}.png" >/dev/null 2>&1
done
echo "saved to $OUT/desk-*.png"

agent-browser close >/dev/null 2>&1
echo ""
echo "RESULT: $FAILS page-load failures"
[ "$FAILS" = "0" ] && echo "BROWSER QA PASS" || echo "BROWSER QA FAIL"
