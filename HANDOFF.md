# 핸드오프 가이드 — AI 보컬 코치 (Flutter)

> 다음 에이전트용. 무엇으로 만들었고(스택), 어디서 막혔는지(시행착오)만 짧고 굵게.
> 앱 = 노래방 챌린지 + 실시간 피치 채점 + Claude 한국어 코칭 + 호흡 분석. (Android/Web 타깃)

---

## 1. 확정된 스택 (이대로 가면 됨)

| 영역 | 선택 | 비고 |
|---|---|---|
| 상태관리 | **Riverpod 2.x** (StateNotifier + `autoDispose` family) | provider override로 의존성 주입 |
| 라우팅 | **go_router 14** | 경로 파라미터(songId, sessionId) |
| 데이터모델 | **freezed + json_serializable** | `build_runner`로 생성 |
| 오디오 입력 | **record 6.2** | 16kHz mono PCM16, 1024 frame |
| 피치 감지 | **pitch_detector_dart** (YIN) | 네이티브는 **Isolate**, 웹은 동기 fallback |
| MR 재생 | **just_audio** | LRC 동기화(`flutter_lyric`) |
| 차트 | **fl_chart** | 점수 추이, 피치 그래프(CustomPaint) |
| 백엔드 | **Firebase** (Auth/Firestore/Storage/Functions, 서울 `asia-northeast3`) | Blaze 플랜 필수 |
| AI 코치 | **Cloud Function → Anthropic SDK**, `claude-haiku-4-5` | TypeScript, Node 20 |
| 로컬저장 | **shared_preferences** | 프로필/음역대 오프라인 fallback |

**오디오 파이프라인:** `record` → 1024 PCM 프레임 → 단일 Isolate(YIN + 호흡 features) → StreamProvider → CustomPaint. **PCM은 폰을 떠나지 않음(on-device).**

---

## 2. 시행착오 / 함정 (← 여기가 핵심, 다시 밟지 말 것)

### 오디오
- **`record` 설정이 전부다.** `autoGain: true` (작은 소리도 잡음), `echoCancel: false`, `noiseSuppress: false` — **에코캔슬 켜면 본인 노래 목소리를 에코로 오인해 잘라먹음**. 켜지 마라. (`lib/audio/audio_capture.dart`)
- **웹은 `dart:isolate` 미지원** → `kIsWeb`으로 분기해 메인 isolate 동기 처리. 안 하면 웹 빌드 깨짐. (`lib/audio/pitch_isolate.dart`)
- 피치 감지는 16kHz / bufferSize 2048 기준으로 튜닝됨. 샘플레이트 바꾸면 MIDI 변환 다 틀어짐.
- **레이턴시:** 데모는 유선 이어폰 권장. 블루투스/스피커는 마이크가 MR을 되받아 점수 망가짐.

### Firebase
- **offline-safe가 설계 핵심.** `firebaseServiceProvider`를 main.dart에서 override 주입, 모든 repository가 `service.available` 체크 후 호출. Firebase 미설정/실패해도 **게스트 모드로 앱이 돈다**. 이 패턴 깨지 말 것.
- `firebase_options.dart`는 더미 → `flutterfire configure`가 덮어씀. iOS/macOS/Win/Linux는 `UnsupportedError` (Android/Web만 설정됨).
- **Google 로그인 안 되면 100% SHA-1 누락.** 디버그 키 SHA-1을 Firebase 콘솔에 등록해야 함.
- **Cloud Functions는 Blaze(종량제) 플랜 필수** (외부 API 호출 때문). Spark에선 배포 자체가 안 됨.

### Cloud Function / AI 코치
- `onCall`(callable) 사용 — 인증 컨텍스트(`req.auth.uid`) 자동. region은 클라/함수 **둘 다 `asia-northeast3`** 맞춰야 함.
- API 키는 코드에 박지 말고 **`firebase functions:secrets:set ANTHROPIC_API_KEY`** → 함수 `secrets`에 mount.
- **프롬프트 캐싱:** system 프롬프트에 `cache_control: {type: 'ephemeral'}` → 비용/지연 절감.
- **Rate limit은 Firestore 트랜잭션**으로 `users/{uid}/quota/{날짜}` 카운트, 20회/일 초과 시 `resource-exhausted`. 클라가 이 에러코드를 한국어로 매핑함.
- Claude 응답을 JSON으로 강제했지만 깨질 수 있어 **정규식 `/\{[\s\S]*\}/`로 추출 후 parse, 실패 시 raw text fallback**.
- 클라 쪽 **에러코드별 한국어 매핑 필수**: `invalid x-api-key` / `unauthenticated` / `resource-exhausted` 등 케이스별 안내. (`coach_controller.dart`)

### UX / 콘텐츠
- **MR 음원 없어도 동작.** `song_player.hasAsset` false면 `Stopwatch` fallback으로 진행. 음원 조달 막혀도 데모 가능.
- **저작권:** K-pop 금지. 아리랑(PD) + 자작 워밍업 4곡만. `assets/songs/<id>.json`에 노트 매핑(startMs/endMs/midiNote/lyric) + license 필드.
- **뒤로가기:** `PopScope`로 즉시 navigate, 마이크 dispose는 백그라운드 (안 그러면 화면 전환이 버벅임).
- 시작 시 3-2-1 카운트다운 + amplitude bar(RMS) — 입력 없을 때 즉각 피드백 줘서 "마이크 죽었나" 오해 방지.

### 채점 (튜닝값 — 마음대로 바꾸면 점수 체감 달라짐)
- `score = max(0, 100 - |centsDeviation| * 0.5)` → **50 cent = 50점, 100 cent = 0점**.
- confidence(RMS/voicing) 가중. 등급 S(90+)/A(80+)/B(70+)/C(<70). 약점 구간 Top 3.
- 호흡: HNR(autocorrelation) + spectral centroid + ZCR로 stability / breathyRatio / longestPhrase 산출. (FFT 아니라 근사치 — 프로덕션은 FFT 패키지 권장)

---

## 3. 빌드 / 검증

```bash
$env:Path = "C:\flutter\bin;$env:Path"
flutter pub get
dart run build_runner build --delete-conflicting-outputs   # freezed/riverpod 생성
flutter analyze        # No issues
flutter test           # 23/23 (audio/ 순수 Dart 단위테스트 위주)
flutter run -d <기기>
flutter build apk --debug   # ~171MB
```

CI: `.github/workflows` (analyze + test + web build).

---

## 4. 미완성 / TODO (재작업 시 우선순위)

**P0**
- [ ] 세션 삭제 UI (history_screen — 버튼/스와이프 없음)
- [ ] 세션 상세 보기 (history → result 라우팅 미연결)

**P1**
- [ ] 곡 검색/필터 (song_picker는 리스트만)
- [ ] 프로필 편집
- [ ] AI 코치 자동 재시도(지수 백오프) — 현재 수동만
- [ ] 음역대 저장 위치 명확화 (SharedPrefs vs Firestore 혼재)

**P2**
- [ ] iOS 등 나머지 플랫폼 `flutterfire configure`
- [ ] FFT 기반 정밀 호흡 분석, 위젯/통합 테스트 보강

---

## 5. 디렉토리 빠른 지도

```
lib/
  core/        theme · router(go_router) · telemetry(p50/p95)
  data/firebase/      firebase_service · auth · session · coach_repository
  data/repositories/  song · song_catalog · user_profile
  audio/       audio_capture · pitch_isolate · pitch_detector · scorer · breath_analyzer · song_player
  features/    auth · range_test · home · song_picker · sing · result · history · profile
  shared/widgets/  pitch_graph · lyric_view · amplitude_bar · animated_score
functions/src/  claudeCoach.ts (Anthropic 프록시)
assets/songs/   *.json 노트 매핑 (아리랑 + 워밍업 4)
```

> 상세 외부 셋업은 `SETUP.md`, 데모 시나리오는 `DEMO.md`, 전수 감사는 `FEATURE_AUDIT_REPORT.md` 참조.
