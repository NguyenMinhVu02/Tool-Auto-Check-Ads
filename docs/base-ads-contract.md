# Chuẩn tham chiếu ads để kiểm tra APK

Nguồn đọc trực tiếp: `Example-AdLogic-Partner/main` tại `e8f4337afbc987c7c9df45a69317fb538ed6e1c6` (đã fetch/đối chiếu remote ngày 2026-09-25). Commit tracking là `56eb8b1` ngày 2026-09-18; HEAD mới hơn vẫn giữ các call site đó. Các đường dẫn dưới đây tính từ root của base project. Bản này là **hợp đồng logic**, không phải danh sách tên hàm bắt buộc. `rulepacks/default/context.md` và `rules/ads-flow.yaml` là bản mà `apk-audit` nạp.

## Nguồn ID và schema

`app/src/main/assets/ad_config.json` chứa ID fallback release. Debug dùng `ad_config_debug.json`. Các ID trong base là ID mẫu của base, không dùng để chấm app đối tác. `app/src/main/res/values/id_ads.xml` hiện chứa token Adjust/Facebook/TikTok, không chứa ad-unit ID. `AdRemoteConfig.kt:33-47,94-117` chọn file debug/release, parse remote JSON cho release và fallback local nếu parse lỗi. `RemoteConfigUtils.kt:66-105,130-137` đưa từng placement local vào defaults Firebase, fetch/activate và đọc key `ad_remote_config` cho JSON tổng. `SplashActivity.kt:111-127` áp dụng config rồi mới lấy `config.id` để load; `GlobalApp.kt:86` ban đầu để `idAdResume` rỗng, Splash gán từ `open_resume` sau khi config sẵn (`SplashActivity.kt:142-147`). Nếu remote và local khác ID, cả hai phải vẫn tham chiếu **cùng key placement**, không lấy ID slot khác.

Mỗi placement có `id`, `isEnable`, `enable_ua_check`. Native còn có `colorCTA`, `heightCTA`, `positionCTA`, `components`; banner có `reloadIntervalSeconds`. `AdRemoteConfigJsonAdapterFactory.kt:43-76` ánh xạ `enable_ua_check` sang `enableUaCheck`. Những giá trị cấu hình thật ở server Firebase không nằm trong APK, nên phần này chỉ kiểm tra logic fallback/phân phối và dữ liệu local. Muốn kết luận ID đúng với app cụ thể cần ADS SCRIPTS; muốn kết luận package, Firebase project và token đúng cần working checklist. Không dùng dữ liệu base để thay hai tài liệu này.

## Inventory ID theo hành trình

| Màn/điểm | Slot được load hoặc dùng | Điều kiện/thời điểm | Bằng chứng |
|---|---|---|---|
| Splash thường | `banner_splash`, `inter_splash`; preload `native_language_1` **hoặc** `_2`; cấu hình `open_resume` | Sau khi đã chọn config; native Language chỉ khi không là uninstall shortcut | `SplashActivity.kt:111-159`; `AdsManager.kt:84-93` |
| Splash từ uninstall shortcut | `banner_splash_uninstall`, `inter_splash_uninstall`; `open_resume` vẫn được cấu hình | Chọn cặp slot uninstall; **không** preload Language | `SplashActivity.kt:115-159` |
| Language | `native_language_1_click` **hoặc** `_2_click`; preload `native_onboarding_1_1` **hoặc** `_2_1` | Sau `postDelayed(100 ms)`; Onboarding preload chỉ khi không mở Language từ Settings | `LanguageActivity.kt:53-81,120-143`; `AdsManager.kt:95-115` |
| Onboarding | `native_onboarding_1_4` **hoặc** `_2_4`; `native_onboarding_fullscreen_1_3` **hoặc** `_2_3`; `inter_onboarding` | Sau `postDelayed(100 ms)`; page 1 dùng native được Language preload; inter được show khi rời Onboarding nếu hợp lệ | `OnBoardingActivity.kt:40-59,165-171`; `AdsManager.kt:117-139,240-268` |
| Welcome | `native_welcome`, `inter_welcome` | Chỉ trên đường resume Welcome được phép; native render tại Welcome; inter show khi click Start | `WelcomeActivity.kt:21-75`; `ResumeAdsEntryRule.kt:14-28` |
| App Open resume | `open_resume` | Ưu tiên so với Welcome; không stack | `ResumeAdsEntryRule.kt:18-28`; `SplashActivity.kt:142-147` |
| Home và nơi khác | `banner_home`, `native_home`, `native_permission`, `native_survey`, `native_confirm_uninstall` | Tùy màn/cấu hình; không tính vào bốn màn trên | `AdsManager.kt:153-191`; `BaseActivityWithBanner.kt:73-126` |
| Chỉ có helper/config ở HEAD | `native_onboarding_fullscreen_1_4`, `_2_4`; `reward_example` | Full2 chưa thấy được load/render trong hành trình Onboarding chính; reward là demo | `AdsManager.kt:141-151,325-378`; `OnBoardingActivity.kt:40-59,112-163` |

Các nhánh `_1`/`_2` chọn theo cờ firstLanguage/firstOnBoarding, nghĩa là **một slot trong cặp tại một lần đi**; không cộng cả hai như quảng cáo cùng lúc. `native_language_1`/`_2` được **load từ Splash nhưng show ở Language**. `native_onboarding_1_1`/`_2_1` được **load từ Language nhưng show ở Onboarding page 1**. Đây là hai trường hợp quan trọng khi kiểm thiếu/thừa ID theo màn.

## Khởi tạo, Remote Config, timeout

- `GlobalApp.kt:48-95`: MobileAds -> DevConfig và ba version BuildConfig -> local AdRemoteConfig -> ERainAdConfig (môi trường debug/release, token từ resources, inter interval 35 giây, id resume ban đầu rỗng) -> ERainAd.init -> App Open exclusions -> lifecycle observer và activity callbacks.
- `RemoteConfigUtils.kt:83-103`: Firebase min fetch interval 0 giây debug, 3600 giây release; defaults gồm từng placement local cùng các flag UI. `fetchAndActivate` có completion listener, nhưng `completed=true` kể cả khi request thất bại; lấy remote rỗng thì fallback local (`:130-137`). `AdRemoteConfig.initialize` parse remote không hợp lệ cũng fallback assets (`AdRemoteConfig.kt:94-103`).
- `SplashActivity.kt:60-70,93-113`: Consent chạy trước timer Splash (nếu cần); timer tổng 6500 ms. Khi config callback xong và thời gian còn dưới 5000 ms, tiếp tục; suy ra ít nhất khoảng 1500 ms chờ. Hết 6500 ms vẫn đi tiếp bằng fallback. Inter Splash gọi SDK với 30000/5000 ms (`:125-140`). `AppConstants.kt:7-9` còn có GDPR timeout 20000 ms; `ConsentHandler.kt` xử lý consent riêng.
- `LanguageActivity.kt:73-81,160-171`: remote có flag delay Done, giá trị mặc định 2000 ms. `WelcomeActivity.kt:28-33`: tối đa khoảng 500 ms mở Start dù inter chưa sẵn sàng.

## Load, show, observer

- Native trong `AdsManager.kt:54-82` bị chặn bởi `isEnable`, purchase, mất mạng và gate UA truyền vào. Khi chặn hoặc thất bại, LiveData nhận `null`; khi tải được, giữ ad cùng config rồi cập nhật LiveData. Các slot nhạy cảm có `getShouldDisplay*(config.enableUaCheck)` trong helper tương ứng (`:117-201`). Những native Language/page 1 đi qua helper với `shouldDisplay=true` mặc định; không gán cho chúng gate UA mà base không có.
- Language `LanguageActivity.kt:132-158` hủy observer cũ trước khi đổi giữa native thường và native click, populate khi có ad và ẩn khi null/offline. Onboarding page Fragment `OnboardingPageFragment.kt:64-117` chọn đúng LiveData theo page và observe với `viewLifecycleOwner`, ẩn container khi null. Welcome `WelcomeActivity.kt:36-75` observe native/inter, render/hide và có fallback Start.
- Inter Onboarding `AdsManager.kt:240-268` có load qua config/gate và callback `onNextAction` để vào Home. **Mã HEAD có lỗi đáng nghi:** nhánh show yêu cầu `&& ignoreLimit`, trong khi caller `OnBoardingActivity.kt:167` không truyền cờ đó (mặc định false). Kiểm tra APK đối tác theo mục tiêu logic “ready + gate thì show, sau close/fail mới điều hướng; không ad thì đi tiếp”, không sao chép điều kiện sai này.
- Welcome `AdsManager.kt:270-323` có readiness callback, timeout nút Start, show/fallback. `ResumeAdsEntryRule.kt:18-28` chọn App Open trước; Welcome đòi cả native và inter bật. `AppLifecycleObserver.kt:19-42` loại Splash/Language/Onboarding/Welcome/Survey, kiểm inter đang hiển thị, purchase và UA trước khi route. App Open exclusion ở `GlobalApp.kt:92-95` là danh sách khác, có ConfirmUninstall.
- Banner reload `BaseActivityWithBanner.kt:73-128` cần enable, chưa purchase, có container, đọc `reloadIntervalSeconds`, dọn handler khi pause/destroy.

## Firebase Analytics events

Commit `56eb8b1` thêm `EventTracking.kt` và call sites. Tên event cần kiểm theo **hành động thực**:

| Event | Điểm gửi ở HEAD |
|---|---|
| `splash_scr_view` | Vào Splash, `SplashActivity.kt:59` |
| `splash_request_ad` | Sau chọn config, trước request ads, `SplashActivity.kt:112` |
| `splash_ad_load` | Callback inter load thành công, `SplashActivity.kt:134-137` |
| `splash_user_close_ad` | Callback inter chuyển tiếp, `SplashActivity.kt:128-132` |
| `language_scr_view` | Vào Language, `LanguageActivity.kt:67` |
| `language_scr_click` | Chọn ngôn ngữ, `LanguageActivity.kt:53-63` |
| `obd_1_scr_view`, `obd_2_scr_view`, `obd_3_scr_view`, `obd_4th_scr_view` | Khi page thường tương ứng hiện, `OnBoardingActivity.kt:97-109` |
| `obd_full_1_scr_view`, `obd_full_2_scr_view` | Chỉ khi full page tương ứng hiện, `OnBoardingActivity.kt:97-109` |
| `home_scr_view` | Vào Home, `MainActivity.kt:79` |

`ITGTrackingHelper.kt:52-54` thực sự gọi Firebase Analytics. Base **không có Welcome event**. `OnBoardingActivity.kt:97-109` gán event theo `position` cứng, nhưng `:143-149` chỉ thêm full1 có điều kiện và không thêm full2. Do đó event từ position 2 trở đi có thể sai; kiểm logic app đối tác theo loại page thực tế, không theo mapping cứng của base. APK tĩnh không chứng minh Firebase server đã nhận event; cần runtime để xác nhận delivery.

## Cách đọc kết quả của apk-audit hiện tại

Rule pack đã nạp 10 câu hỏi theo luồng và các regex trích xuất ID/event/key. Mặc định CLI dùng `--engine none`: các luật agent sẽ trả `UNKNOWN`, không tự xác nhận PASS/FAIL. Muốn chấm logic APK tự động cần adapter AI live hoặc bộ phân tích static chuyên sâu trong phase tiếp theo. `facts.json` vẫn trích được assets, strings, manifest và mã đã giải thông qua MCP để người kiểm tra đối chiếu. Bản web localhost kéo thả APK/XAPK là phase sau, có thể gọi cùng `apk_audit.run(...)` sau khi phần kiểm tra logic hoạt động đủ tin cậy.
