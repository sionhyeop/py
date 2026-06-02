# 기능 이식 가이드 — ① 곡 검색 · ② 가사 가져오기

> 대상: 이 두 기능만 **다른 앱(또는 새 화면)에 옮겨 넣어야 하는 에이전트**.
> 목적: "어떻게 동작하는가(원리)" + "왜 이렇게 짰는가(시행착오)" 를 함께 전달해서,
> 코드를 그대로 복사하든 새로 짜든 **같은 함정에 다시 빠지지 않게** 한다.
>
> 이 문서만 읽으면 PitchRoom 본체를 몰라도 두 기능을 재현할 수 있도록 자급자족(self-contained)하게 작성했다.

---

## 0. 30초 요약

| 기능 | 데이터 출처 | 호출 위치 | 키 필요 | 핵심 함정 |
|------|-------------|-----------|---------|-----------|
| **곡 검색** | YouTube **Data** API v3 `/search` | 브라우저에서 직접 `fetch` | ✅ `VITE_YOUTUBE_API_KEY` | 제목이 HTML 엔티티로 옴 / 제목에서 곡·아티스트 추출이 지저분함 |
| **가사 가져오기** | lrclib.net (싱크 LRC 가사) | **Python 백엔드 프록시** 경유 (브라우저 직접 호출은 fallback) | ❌ (lrclib 무료) | CORS·광고차단·**DNS 필터링**·**Cloudflare WAF** 때문에 브라우저 직접 호출이 자주 깨짐 → 백엔드가 DoH+TLS 위장으로 우회 |

두 기능은 **서로 독립**이지만, 한 군데에서 만난다:
곡 검색 결과의 **영상 제목**을 파싱(`titleParser`)해서 → 가사 검색의 **(곡명, 아티스트)** 쿼리로 넘긴다.
이 접점만 알면 둘을 따로 떼어내거나 같이 붙일 수 있다.

```
[곡 검색]                                  [가사 가져오기]
 YouTube Data API ──> 영상목록 ──선택──> parseVideoTitle(title)
                                          → { trackName, artistName, alternate }
                                                     │
                                                     ▼
                                       useLyrics({track, artist, alternate, freeText})
                                                     │
                              VITE_LYRICS_API 있음? ──┴── 없음
                                     │                    │
                              Python 백엔드          브라우저에서
                              /api/lyrics            lrclib 직접 호출
                                     │                    │
                              lrclib.net (DoH+curl_cffi 우회)
                                     │
                                LRC 문자열 ──> parseLrc() ──> [{time, text}, ...]
```

---

## 1. 의존성 & 환경변수

### 프론트엔드 (이식 시 추가로 필요한 것 — 거의 없음)
- 곡 검색: **외부 라이브러리 0개**. 순수 `fetch` + 브라우저 내장 `document`(엔티티 디코딩용).
- 가사: **외부 라이브러리 0개**. 순수 `fetch` + 자체 `parseLrc`.
- 상태관리는 예시로 zustand 를 쓰지만 **필수 아님** — 그냥 props/useState 로 대체 가능.

### 환경변수 (`.env`, Vite 기준)
```bash
# 필수: 곡 검색용. Google Cloud Console > YouTube Data API v3 에서 발급.
VITE_YOUTUBE_API_KEY=발급받은_키

# 선택: 가사 백엔드 주소. 비워두면 브라우저가 lrclib 을 직접 호출(fallback).
#       설정하면 백엔드 프록시를 우선 사용(권장 — 방화벽/DNS 환경에서 안정적).
VITE_LYRICS_API=http://127.0.0.1:8000
```
> Vite 는 `VITE_` 접두사가 붙은 변수만 클라이언트에 노출한다. 접두사 빼먹으면 `import.meta.env` 에서 `undefined`.
> **주의**: YouTube 키가 클라이언트 번들에 그대로 박힌다. 공개 배포 시엔 키에 **HTTP 리퍼러 제한**을 걸거나, 검색도 백엔드로 프록시할 것. (MVP/로컬에선 클라이언트 직접 호출 허용.)

### 백엔드 (가사 프록시를 쓸 때만)
```
fastapi>=0.110
uvicorn[standard]>=0.29
curl_cffi>=0.7      # ★ 핵심. DNS 우회 + Chrome TLS 지문 위장. requests/httpx 로는 대체 불가.
```

---

## 2. 기능 ① — 곡 검색

### 2.1 원리

- **YouTube Data API v3 `search.list`** 엔드포인트를 그냥 HTTP GET 한다.
  IFrame Player API(영상 재생)와 **다른 API**다. 검색=Data API(키 필요), 재생=IFrame API(키 불필요). 이 둘을 헷갈리지 말 것.
- 노래방 용도이므로 검색어 뒤에 **`"MR Instrumental"`** 을 강제로 붙여 반주(MR) 영상이 우선 나오게 유도한다.
- `videoEmbeddable=true` 로 **앱 안에서 재생 가능한 영상만** 받는다. (이걸 안 걸면 "소유자가 외부 재생 차단"한 영상이 섞여 IFrame 에서 안 틀어진다.)

### 2.2 핵심 코드 (그대로 이식 가능)

```js
async function searchYouTube(query, apiKey) {
  const q = encodeURIComponent(`${query} MR Instrumental`)
  const url =
    `https://www.googleapis.com/youtube/v3/search` +
    `?part=snippet&type=video&videoEmbeddable=true&maxResults=12&q=${q}&key=${apiKey}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`YouTube API ${res.status}`)
  const data = await res.json()
  return (data.items || []).map((item) => ({
    videoId: item.id.videoId,
    title: item.snippet.title,                 // ⚠ HTML 엔티티 포함 상태
    channelTitle: item.snippet.channelTitle,
    thumbnail:
      item.snippet.thumbnails?.medium?.url ||
      item.snippet.thumbnails?.default?.url,
    description: item.snippet.description,
  }))
}

// YouTube 제목은 &amp; &#39; &quot; 같은 엔티티로 인코딩돼 온다.
// textarea.innerHTML 트릭으로 한 번에 디코딩.
function decodeEntities(str) {
  if (!str) return ''
  const el = document.createElement('textarea')
  el.innerHTML = str
  return el.value
}
```

호출 패턴(요지):
```js
const apiKey = import.meta.env.VITE_YOUTUBE_API_KEY
if (!apiKey) { /* "키 미설정" 안내 */ }
try {
  const items = await searchYouTube(query.trim(), apiKey)
  if (items.length === 0) /* "검색 결과 없음" */
} catch (err) { /* err.message = "YouTube API 403" 등 */ }
```

### 2.3 시행착오 (★ 여기서 배운 것)

1. **제목이 HTML 엔티티로 온다.**
   `item.snippet.title` 은 `아이유(IU) &amp; 친구들 &#39;밤편지&#39;` 처럼 인코딩돼 있다.
   화면 표시 직전에 `decodeEntities()` 로 풀어야 사람이 읽을 수 있고, **가사 검색 정확도도 올라간다**(엔티티가 섞이면 매칭 실패).
2. **`videoEmbeddable=true` 는 옵션이 아니라 필수.**
   빼면 검색은 잘 되는데 막상 IFrame 에 넣으면 "동영상 소유자가 다른 웹사이트에서 재생을 사용 중지함" 으로 까만 화면이 뜬다. 검색 단계에서 걸러야 한다.
3. **403 의 두 가지 원인.** `YouTube API 403` 이 뜨면 (a) 키의 일일 쿼터 소진, (b) 키 제한(HTTP 리퍼러/IP) 걸려서 현재 출처가 막힌 경우. 둘 다 메시지가 같아서 콘솔의 응답 본문(`reason`)을 봐야 구분된다.
4. **`maxResults` 는 12 정도가 체감 최적.** 너무 크면 쿼터를 빨리 먹고(검색 1회 = 100 유닛, 기본 일일 10,000 유닛 → 하루 ~100회), 너무 작으면 MR 영상이 안 보인다.
5. **검색어에 `"MR Instrumental"` 강제 삽입은 양날의 검.** 반주 영상을 잘 띄우지만, 사용자가 이미 "노래제목 MR" 로 검색하면 "MR MR" 이 되어 살짝 정확도가 떨어진다. (개선 여지: 이미 MR/Inst 가 포함됐는지 검사 후 조건부 삽입.)

---

## 3. 기능 ② — 가사 가져오기

이 기능이 분량이 많고 함정도 많다. **핵심 통찰: 브라우저에서 lrclib 을 직접 부르는 건 환경을 탄다.** 그래서 "백엔드 우선 + 브라우저 fallback" 2단 구조로 짰다.

### 3.1 원리 — 2단 소스 전략

```
useLyrics()
 ├─ VITE_LYRICS_API 설정됨 → 백엔드 /api/lyrics 호출 (searchViaBackend)
 │     └─ 네트워크 자체가 완전 실패하면 → 브라우저 직접 lrclib (searchViaLrclib) 로 fallback
 └─ 설정 안 됨 → 처음부터 브라우저 직접 lrclib
```

- **백엔드 경로**: 브라우저 → 우리 Python → lrclib. CORS·광고차단·DNS·WAF 문제를 서버가 대신 흡수한다.
- **lrclib 직접 경로**: 백엔드 없이도 일단 돌아가게 하는 안전망.
- 두 경로 모두 **여러 파라미터 조합을 순서대로 시도**한다(아래 3.4).

### 3.2 백엔드의 진짜 핵심 — DNS 필터링 & Cloudflare 우회 (`backend/lyrics.py`)

> 이게 이 프로젝트에서 가장 비싸게 얻은 노하우다. 학교/회사망(OpenDNS Umbrella 등)이 `lrclib.net` 도메인을 DNS 단에서 막거나, Cloudflare WAF 가 봇으로 보고 차단하는 상황을 정면 돌파한다.

**원리 3단계:**
1. **DoH(DNS-over-HTTPS) 로 진짜 IP 를 직접 조회.**
   로컬 DNS 가 `lrclib.net` 을 막아도, `https://8.8.8.8/resolve?name=lrclib.net&type=A` 같은 공개 DoH 엔드포인트로 A 레코드를 받아온다. (HTTPS 라서 DNS 필터가 못 본다.)
2. **`curl_cffi` 의 `CURLOPT_RESOLVE` 로 그 IP 에 직접 접속.**
   `lrclib.net:443:<IP>` 매핑을 박아서, OS 의 막힌 DNS 를 거치지 않고 바로 그 IP 로 붙는다. 이때 **SNI/Host 헤더는 원 도메인(`lrclib.net`)을 유지**하므로 인증서/라우팅은 정상.
3. **`impersonate="chrome"` 으로 Chrome TLS 지문 위장.**
   Cloudflare 는 TLS 핸드셰이크 지문(JA3)으로 봇을 가린다. `curl_cffi` 는 실제 Chrome 의 TLS 지문을 흉내 내서 WAF 를 통과한다. → **이게 `requests`/`httpx` 로 대체 불가능한 이유.**

```python
from curl_cffi import requests as ccrequests
from curl_cffi import CurlOpt

LRCLIB_HOST = "lrclib.net"
DOH_RESOLVERS = [               # 차례로 시도. 하나 막히면 다음.
    "https://8.8.8.8/resolve",
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query",
]
_ip_cache = {}                  # 프로세스 생애주기 동안 IP 캐시

def _resolve_via_doh(hostname):
    if hostname in _ip_cache: return _ip_cache[hostname]
    for url in DOH_RESOLVERS:
        try:
            r = ccrequests.get(url,
                params={"name": hostname, "type": "A"},
                headers={"accept": "application/dns-json"},
                impersonate="chrome", timeout=8, verify=False)
            if r.status_code != 200: continue
            ips = [a["data"] for a in (r.json().get("Answer") or [])
                   if a.get("type") == 1 and "data" in a]
            if ips:
                _ip_cache[hostname] = ips
                return ips
        except Exception:
            continue
    return []

def _lrclib_get(path, params):
    ips = _resolve_via_doh(LRCLIB_HOST)
    if not ips: raise RuntimeError("could not resolve via DoH")
    for ip in ips:
        try:
            r = ccrequests.get(f"https://{LRCLIB_HOST}/api{path}",
                params=params, impersonate="chrome", timeout=15,
                verify=False,                       # 신뢰는 RESOLVE+SNI 로 대체
                headers={"Accept": "application/json",
                         "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"},
                curl_options={CurlOpt.RESOLVE: [f"{LRCLIB_HOST}:443:{ip}"]})
            if r.status_code == 404: return None
            if r.status_code != 200: continue
            return r.json()
        except Exception:
            continue
    return None
```

### 3.3 FastAPI 래퍼 (`backend/main.py`)

```python
app = FastAPI(title="PitchRoom Lyrics API")
app.add_middleware(CORSMiddleware,           # 개발 단계: 전 출처 허용
    allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"ok": True}

@app.get("/api/lyrics")
def get_lyrics(track: str = Query(..., min_length=1),
               artist: Optional[str] = Query(None)):
    result = search_lyrics(track=track, artist=artist)
    if result is None:
        raise HTTPException(status_code=404, detail="Lyrics not found")
    return result    # {"synced": str|None, "plain": str|None, "matched_*":..., "query":...}
```

실행:
```bash
cd backend
uv venv --python 3.12 .venv          # 또는 python -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn main:app --port 8000 --host 127.0.0.1
# 확인: curl "http://127.0.0.1:8000/api/lyrics?track=Dynamite&artist=BTS"
```

### 3.4 다중 파라미터 조합 시도 (양쪽 경로 공통 패턴)

lrclib 매칭은 입력이 조금만 달라도 빗나가므로, **넓은 쿼리 → 좁은 쿼리** 순으로 여러 번 시도하고 첫 히트를 채택한다.

백엔드(`search_lyrics`)와 프론트(`buildLrclibAttempts`) 둘 다 같은 철학:
```
1) {track_name, artist_name}      # 가장 정확
2) {track_name}                   # 아티스트 빼고
3) {q: "artist track"}            # 자유 텍스트 통검색
(+ 제목 파서가 준 alternate 조합도 추가로 시도 — 곡/아티스트가 뒤바뀐 케이스 대비)
```
그리고 결과 중 **`syncedLyrics`(싱크 가사)가 있는 항목을 최우선**, 없으면 첫 결과:
```js
function pickBest(results) {
  const synced = results.find((d) => d.syncedLyrics)
  return synced || results[0] || null
}
```

### 3.5 프론트엔드 훅 (`useLyrics`) — 요지

```js
const LYRICS_API = import.meta.env.VITE_LYRICS_API
const LRCLIB = 'https://lrclib.net/api'

// 결과 정규화: synced 있으면 parseLrc, 없으면 plain 텍스트만
function hitToResult(hit) {
  if (hit?.syncedLyrics) return { lines: parseLrc(hit.syncedLyrics), plain: hit.plainLyrics||'', matched:{...} }
  if (hit?.plainLyrics)  return { lines: [], plain: hit.plainLyrics, matched:{...} }
  return null
}

export function useLyrics({ trackName, artistName, alternate, freeText }) {
  // status: 'idle' | 'loading' | 'ok' | 'notfound' | 'error'
  // 1) trackName/freeText 없으면 idle 로 리셋
  // 2) LYRICS_API 있으면 백엔드 우선, 네트워크 완전실패 시 lrclib fallback
  // 3) abort 플래그로 경쟁 조건(빠른 재검색) 방지
  // 반환: { lines, plain, status, matched, errorMessage, source }
}
```
> 의존성 배열에 `alternate?.trackName, alternate?.artistName, freeText` 까지 넣어야 재검색이 트리거된다. (객체 자체를 넣으면 매 렌더 새 참조라 무한 루프.)

### 3.6 LRC 파서 (`lrcParser.js`) — 그대로 이식 가능

```js
// "[00:12.00][01:30.00]가사" → [{time:12, text:'가사'}, {time:90, text:'가사'}]
const TIME_RE = /\[(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?\]/g
export function parseLrc(lrcText) { /* 한 줄에 여러 타임스탬프 처리, time 오름차순 정렬 */ }

// 현재 재생시간(초)에 해당하는 라인 인덱스 — 이진 탐색
export function findLineIndex(lines, currentTime) { /* lines[mid].time <= currentTime 최대 인덱스 */ }
```
> 싱크가 200ms 주기로 `player.getCurrentTime()` 갱신되어도 `findLineIndex` 가 O(log n) 이라 매 프레임 호출해도 가볍다.

### 3.7 시행착오 (★ 여기서 배운 것)

1. **브라우저 직접 호출은 환경을 심하게 탄다.**
   - **CORS**: lrclib 은 CORS 를 열어줘서 보통은 되지만,
   - **광고차단 확장(uBlock 등)** 이 lrclib 도메인을 트래커로 오인해 막고,
   - **학교/회사 DNS 필터(OpenDNS Umbrella)** 가 도메인 자체를 죽이고,
   - **Cloudflare WAF** 가 가끔 봇으로 보고 challenge 를 띄운다.
   → 그래서 **백엔드 프록시가 정답**이고, 직접 호출은 fallback 으로만 남겼다.
2. **`requests`/`httpx` 로는 Cloudflare 를 못 뚫었다.** TLS 지문이 봇 티가 나서 막힘. **`curl_cffi` 의 `impersonate="chrome"`** 으로만 통과. (이게 requirements 에 curl_cffi 가 박힌 이유.)
3. **DNS 필터는 DoH 로 우회.** OS DNS 가 막혀도 `https://8.8.8.8/resolve` 는 HTTPS 라 필터가 못 본다. 받은 IP 를 `CURLOPT_RESOLVE` 로 직접 꽂되 **SNI/Host 는 원 도메인 유지**(안 그러면 Cloudflare 가 어느 사이트인지 몰라서 거절).
4. **`verify=False` 를 쓴 이유와 안전성.** IP 직결이라 기본 검증 체인이 꼬일 수 있어 끔. 대신 SNI 로 올바른 호스트에 붙으므로 실질 위험은 낮다. (운영에선 핀닝 권장.)
5. **백엔드 README 와 실제 구현이 다르다(문서 부채).** README 는 `syncedlyrics` 라이브러리를 쓴다고 적혀 있지만, **실제 `lyrics.py` 는 `curl_cffi` 로 lrclib 을 직접 친다.** `syncedlyrics` 가 같은 차단 문제를 못 넘어서 직접 구현으로 갈아탄 흔적. → **이식할 땐 README 말고 코드(`lyrics.py`)를 신뢰할 것.**
6. **싱크 가사 우선순위.** lrclib 검색은 plain-only 항목이 먼저 나올 때가 많다. `syncedLyrics` 가진 항목을 명시적으로 골라야(`pickBest`) 노래방 하이라이트가 산다.
7. **한 줄에 타임스탬프 여러 개.** LRC 표준상 `[00:12][00:40]후렴` 처럼 반복 줄이 압축돼 온다. 파서가 스탬프마다 라인을 펼치고 시간순 재정렬해야 한다.
8. **경쟁 조건.** 사용자가 곡명을 빠르게 고쳐 재검색하면 이전 요청이 늦게 도착해 화면을 덮어쓴다. `useEffect` cleanup 의 `aborted` 플래그로 막았다.
9. **404 는 에러가 아니라 "없음".** 백엔드도 프론트도 404 를 `notfound` 상태로(에러 아님) 구분해서, "서버 오류" 와 "이 곡 가사 없음" 을 다르게 안내한다.

---

## 4. 두 기능의 접점 — 제목 파싱 (`titleParser.js`)

곡 검색 결과(영상 제목)를 가사 쿼리로 변환하는 **유일한 연결 고리**.

```js
parseVideoTitle("아이유(IU) - 밤편지 (Through the Night) MR [가사/반주]")
// → { trackName: "밤편지", artistName: "아이유",
//     alternate: { trackName: "아이유", artistName: "밤편지" } }
```

동작:
1. HTML 엔티티 디코딩 →
2. 괄호류 `[...]()【】〈〉《》` 통째 제거 →
3. 노이즈 단어 제거(`MR, Inst, Karaoke, 반주, 가사, Official, MV, 4K …`) →
4. 구분자(`- – — −`)로 분리 →
5. `좌-우` 를 `artist-track` 으로 보되, **뒤바뀐 경우 대비해 `alternate` 도 같이 반환**.

**시행착오:** MR 업로드 제목은 포맷이 제각각(`[MR] 아이유 - 밤편지`, `밤편지 - 아이유 (MR)`, `IU 밤편지 MR 반주`)이라 한 규칙으로 못 잡는다. 그래서 "정답 1개" 가 아니라 **(주 추정 + alternate) 2개를 만들어 가사 검색에서 둘 다 시도**하게 했다. 이게 매칭 성공률을 크게 올렸다.

> 이식 시: 곡 검색만 떼어 쓸 거면 `parseVideoTitle` 불필요. 가사만 떼어 쓸 거면 사용자가 직접 (곡명, 아티스트) 를 입력받아 넘기면 된다(파서 없이도 동작).

---

## 5. 다른 앱에 이식하는 절차 (체크리스트)

### A. 곡 검색만 필요할 때
1. `VITE_YOUTUBE_API_KEY` 발급·설정.
2. `searchYouTube()` + `decodeEntities()` 두 함수만 복사(§2.2).
3. UI: 입력 → 결과 리스트(썸네일/제목/채널). 클릭 시 `videoId` 를 IFrame 으로 재생.
4. 에러 처리: 키 없음 / 403(쿼터·제한) / 결과 0건.
5. (선택) "MR Instrumental" 강제 삽입을 도메인에 맞게 조정/제거.

### B. 가사만 필요할 때
1. 백엔드 띄우기: `backend/` 의 `main.py`+`lyrics.py`+`requirements.txt` 복사 → uv/venv 로 설치 → `uvicorn main:app --port 8000`.
2. `VITE_LYRICS_API=http://127.0.0.1:8000` 설정.
3. 프론트: `useLyrics` 훅 + `lrcParser.js` 복사. zustand 안 쓰면 입력값을 직접 props 로 넘기게 시그니처만 조정.
4. (백엔드 없이 가려면) `VITE_LYRICS_API` 를 비우면 브라우저 직접 lrclib 경로로 동작 — 단 §3.7 의 환경 리스크를 감수.
5. UI: `status`(idle/loading/ok/notfound/error) 별 안내 + `lines` 를 시간 동기화해 하이라이트(`findLineIndex`).

### C. 둘 다 + 연동
- 위 A·B 에 더해 `titleParser.js` 를 끼워, 검색 선택 → `parseVideoTitle` → `useLyrics` 로 자동 연결(§4).

### 옮길 파일 맵
```
곡 검색:   src/pages/SearchPage.jsx (searchYouTube/decodeEntities 발췌)
가사 훅:   src/hooks/useLyrics.js
LRC 파서:  src/lib/lrcParser.js
제목 파서: src/lib/titleParser.js          (연동 시에만)
가사 백엔드: backend/main.py, backend/lyrics.py, backend/requirements.txt
```

---

## 6. 통합 검증 (이식 후 반드시 확인)

```bash
# 1) 백엔드 헬스
curl http://127.0.0.1:8000/api/health            # → {"ok": true}

# 2) 백엔드 가사 (싱크 가사가 synced 에 채워져 오면 성공)
curl "http://127.0.0.1:8000/api/lyrics?track=Dynamite&artist=BTS"

# 3) 프론트 곡 검색: 브라우저 DevTools Network 에서
#    googleapis.com/youtube/v3/search 가 200 이고 items 가 채워지는지

# 4) 프론트 가사: VITE_LYRICS_API 설정 시 요청이 127.0.0.1:8000 으로 가는지
#    (lrclib.net 으로 직접 가면 .env 가 안 먹은 것)
```
**성공 기준:** 검색 결과 클릭 → 가사 영역이 `loading` → `ok` 로 바뀌고 LRC 라인이 시간에 맞춰 하이라이트.

---

## 7. 실행 환경에서 실제로 부딪힌 함정 (이식 작업 중 재발 가능)

1. **rollup 네이티브 모듈 누락** —
   `Cannot find module @rollup/rollup-linux-x64-gnu`. `node_modules` 가 **다른 OS(예: Windows)에서 설치**된 채 Linux/WSL 로 넘어오면 발생(npm optional deps 버그).
   → **해결: `rm -rf node_modules package-lock.json && npm install`** 을 그 플랫폼에서 다시.
2. **`pip` 부재** — 시스템에 `pip`/`python3 -m pip` 가 없는 환경(여기 WSL)이 있다.
   → **해결: `uv`** 로 `uv venv --python 3.12` + `uv pip install`. (시스템 파이썬이 3.14처럼 너무 최신이라 `curl_cffi` 휠이 없을 수 있으니 **3.12 로 고정**.)
3. **포트 충돌** — Vite 5173 점유 시 자동으로 5174 로 뜬다. 프론트 주소를 코드/문서에 하드코딩하지 말 것.
4. **백엔드 첫 요청 지연** — `curl_cffi`/DoH 초기화로 첫 가사 요청이 몇 초 걸릴 수 있다(이후 `_ip_cache` 로 빨라짐). 헬스체크가 200이어도 가사 첫 콜은 여유를 둘 것.

---

## 8. 한 줄 핵심 (잊지 말 것)

- **검색**은 쉽다. 함정은 **HTML 엔티티 디코딩**과 **`videoEmbeddable=true`** 둘뿐.
- **가사**의 진짜 난이도는 lrclib 파싱이 아니라 **거기 도달하는 것**(DNS 필터·Cloudflare). 그 해법이 **백엔드 프록시 + DoH + `curl_cffi` Chrome 위장**이다. `requests` 로 바꾸면 깨진다.
- 문서(README)보다 **코드(`lyrics.py`)가 진실**이다.
