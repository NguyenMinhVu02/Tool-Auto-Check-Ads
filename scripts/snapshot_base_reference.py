"""Refresh the portable reference from the reviewed base commit; never copy IDs/tokens.

Usage: .venv/bin/python scripts/snapshot_base_reference.py /path/to/base
Line ranges are reviewed against PINNED_COMMIT. Re-review them before changing it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


PINNED_COMMIT = 'e8f4337afbc987c7c9df45a69317fb538ed6e1c6'
JAVA = 'app/src/main/java/com/itg/template/'
FILES = {
    'global': 'app/GlobalApp.kt', 'config': 'ads/AdRemoteConfig.kt',
    'remote': 'ads/RemoteConfigUtils.kt', 'manager': 'ads/AdsManager.kt',
    'splash': 'ui/component/splash/SplashActivity.kt',
    'language': 'ui/component/language/LanguageActivity.kt',
    'onboarding': 'ui/component/onboarding/OnBoardingActivity.kt',
    'page': 'ui/component/onboarding/adapter/OnboardingPageFragment.kt',
    'resume': 'app/ResumeAdsEntryRule.kt', 'lifecycle': 'app/AppLifecycleObserver.kt',
    'welcome': 'ui/component/welcome/WelcomeActivity.kt',
    'banner': 'ui/bases/BaseActivityWithBanner.kt', 'events': 'data/event/EventTracking.kt',
    'tracking': 'utils/ITGTrackingHelper.kt', 'home': 'ui/component/main/MainActivity.kt',
}

# Goals describe static code contracts. SDK delivery/remote production data are separate limits.
PROFILES = {
    'ADS_INIT_ORDER': (
        'Chứng minh thứ tự Application init và đăng ký lifecycle từ manifest tới lời gọi.',
        ['manifest → onCreate', 'config local → SDK init', 'lifecycle callbacks và policy resume'],
        [('global', 48, 97)],
        ['Không bắt buộc App Open hoạt động nếu integration_policy không yêu cầu. SDK init thành công thực tế không thuộc chứng minh tĩnh.']),
    'ADS_REMOTE_FALLBACK': (
        'Chứng minh chọn local/release/debug, remote blank/parse lỗi, timer và chọn config trước load.',
        ['defaults/fetch → completed', 'resolver → parser → fallback assets', 'Splash timeout → config → load'],
        [('remote', 65, 106), ('remote', 130, 138), ('remote', 178, 191), ('config', 33, 47), ('config', 94, 106), ('splash', 93, 114)],
        ['completed trong base chỉ có nghĩa callback kết thúc, không chứng minh fetch thành công.',
         'Base fallback cho chuỗi blank hoặc parse exception; không tự thêm yêu cầu JSON object rỗng phải fallback nếu rule/hợp đồng không quy định.',
         'Không đòi giá trị Firebase live để chấm logic nhánh local/remote đã hiện rõ. Nếu giá trị SDK quyết định một nhánh chưa biết thật sự, ghi đúng nhánh đó.']),
    'ADS_ID_SOURCE_AND_COVERAGE': (
        'Nối key/alias trong getter tới config.id đưa vào SDK, đối chiếu ID của app theo tài liệu đang dùng.',
        ['ADS SCRIPTS active → assets/remote key', 'getter alias → config.id → SDK load'],
        [('config', 125, 162), ('manager', 54, 104)],
        ['Tên key có hậu tố/ngày hoặc alias không phải lỗi nếu getter nối đúng slot; inventory lexical chỉ là đầu mối.',
         'Không so ID với base. Slot disabled/unknown không yêu cầu coverage; inter_onboarding tùy chọn.',
         'Dừng đường chứng minh tại config.id → SDK load. Callback/render/navigation thuộc rule khác, trừ khi cần để xác định ID thật.',
         'Schema/key remote trong source có thể kiểm tĩnh; JSON Firebase đang triển khai chỉ là limitation nếu chưa được cung cấp, không phải blocker của nguồn ID tĩnh.',
         'Nếu local ID lệch tài liệu và đường fallback local đã chứng minh, remote live chưa biết không tự xóa sự lệch local đã quan sát.']),
    'ADS_SPLASH_PLACEMENT': (
        'Kiểm chọn cặp banner/inter theo route, preload đúng Language, timeout và đường tiếp tục.',
        ['normal/uninstall → config pair', 'config chọn xong → preload Language', 'inter next/skip và timeout → navigation'],
        [('splash', 93, 173), ('splash', 182, 199)],
        ['Mã base hiện preload Language ngay sau config, không đợi onAdLoaded như tài liệu cũ.',
         'Open Resume tuân integration_policy mới, không mặc định buộc bật từ đoạn code mẫu.']),
    'ADS_LANGUAGE_PLACEMENT': (
        'Nối load language/click, observer swap, render/hide, preload page1 và delay Done.',
        ['click callback → remove observer → stream click', 'stream → lifecycle observer → render/null/offline',
         'không từ Settings → preload page1', 'remote delay/fallback → Done'],
        [('language', 53, 84), ('language', 121, 174), ('manager', 84, 116)],
        ['Tên Activity, stream, lambda có thể khác base; mở helper/lambda được gọi thay vì chỉ tìm tên mẫu.',
         'Có đường đăng ký observer/load callback/render trong source là chứng minh tĩnh; không đòi ad fill runtime cho nhận định này.']),
    'ADS_ONBOARDING_PLACEMENT': (
        'Nối page thật sự được render với native page1/page4/full, view lifecycle và điều hướng tiếp.',
        ['Language → page1 preload', 'Onboarding → preload page4/full → page flags', 'page flags → observer → render/hide'],
        [('onboarding', 40, 59), ('onboarding', 112, 171), ('page', 64, 118), ('manager', 117, 139)],
        ['inter_onboarding trong code mẫu là thông tin lịch sử: không yêu cầu ở cuối Onboarding theo policy mới.',
         'Không bắt page full2 hoặc slot không có trong hành trình thực. Giải Kotlin mask theo đúng item, không áp mask page2 cho page1.']),
    'ADS_WELCOME_RESUME': (
        'Theo slot active trong tài liệu, kiểm route resume, loại trừ, gate và Welcome có nhánh thoát.',
        ['policy/applicability → lifecycle route', 'load → observer → button', 'CTA → inter callback hoặc skip → finish'],
        [('resume', 14, 28), ('lifecycle', 18, 45), ('welcome', 20, 76), ('manager', 270, 323)],
        ['Chấp nhận WelcomeBack chỉ inter nếu tài liệu app yêu cầu biến thể đó.',
         'Không bắt native_welcome/open_resume thiếu hoặc disabled; code base không thay thế tài liệu app.']),
    'ADS_LOAD_OBSERVE_GATES': (
        'Lần helper load dùng chung tới các màn active: gate → update stream → observer → render/hide.',
        ['config enable/purchase/network/UA → SDK load', 'success/failure/skip → stream', 'mỗi slot active → observer và view lifecycle → render/hide'],
        [('manager', 54, 82), ('manager', 117, 139), ('language', 132, 158), ('page', 64, 118)],
        ['Không cần đọc lại cùng helper cho mỗi slot; lập bảng slot→helper→stream→observer và mở những call site khác helper hoặc còn thiếu.',
         'Không đòi observer phát liên tục thực tế để chấm cấu trúc tĩnh; callback SDK không giải mã được chỉ chặn claim cần nội bộ đó.']),
    'ADS_FIREBASE_EVENTS': (
        'Nối tên event qua wrapper/alias tới hành động UI/callback tương ứng.',
        ['constant hoặc dynamic name → wrapper → Firebase.logEvent', 'screen/click/load callback → wrapper', 'page type → event'],
        [('events', 1, 18), ('tracking', 52, 55), ('language', 53, 68), ('splash', 111, 138), ('onboarding', 98, 109), ('home', 76, 82)],
        ['Tên class wrapper không phải API bắt buộc; lần caller của wrapper/alias trong app và callback/lambda đích.',
         'Không có lexical hit chưa chứng minh thiếu event. Muốn FAIL thiếu event phải đọc call site UI/callback hoàn chỉnh và wrapper liên quan.',
         'Base dùng position cố định nhưng page full thêm có điều kiện; kiểm theo loại page thật, không coi mapping cứng là chuẩn.',
         'Không cần chứng minh Firebase server nhận event để chấm lời gọi tĩnh đúng thời điểm; runtime delivery chỉ là limitation.']),
    'ADS_BANNER_RELOAD': (
        'Kiểm đúng slot/container/gate; reload trên màn có vòng reload được yêu cầu và cleanup lifecycle.',
        ['screen → banner config → container/load', 'interval → timer → reload', 'pause/destroy → cleanup'],
        [('splash', 150, 159), ('manager', 380, 414), ('banner', 36, 74), ('banner', 73, 129)],
        ['Base có vòng reload ở BaseActivityWithBanner; Splash chỉ gọi loadBanner một lần. Không suy reload Splash bắt buộc chỉ vì config có interval.',
         'Nếu báo thiếu reload phải xác định màn đó có yêu cầu reload từ hợp đồng/rule và lần cơ chế scheduler; không kết luận từ thiếu một tham số trong call load.']),
    'ADS_CROSS_FLOW_BUGS': (
        'Rà đường callback/lifecycle thực sự của hành trình chính, tìm lỗi mới có đường tái tạo tĩnh.',
        ['manager callback/skip → navigation', 'resume/pause/destroy → cleanup hoặc retry', 'config → preload → screen còn sống'],
        [('manager', 305, 323), ('banner', 36, 74), ('splash', 182, 211), ('lifecycle', 27, 45)],
        ['Không lặp finding chuyên biệt; không lặp lỗi inter optional hoặc open_resume không được yêu cầu.',
         'PASS chỉ giới hạn các đường trọng yếu đã lần đủ; không khẳng định toàn APK không bug. UNKNOWN phải chỉ ra call site/nhánh cụ thể còn thiếu.']),
}


def snapshot(base):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=base, text=True).strip()
    if commit != PINNED_COMMIT:
        raise ValueError('Base commit đã đổi; cần review lại ranges/caveats trước khi cập nhật snapshot')
    paths = [JAVA + name for name in FILES.values()]
    if subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', *paths], cwd=base).returncode:
        raise ValueError('Các source base liên quan có thay đổi chưa commit; cần review lại trước khi snapshot')
    texts = {key: (base / JAVA / relative).read_text() for key, relative in FILES.items()}
    result = {'schema_version': 1, 'source': {'repository': 'Example-AdLogic-Partner', 'commit': commit,
              'file_sha256': {JAVA + FILES[key]: hashlib.sha256(text.encode()).hexdigest() for key, text in texts.items()}},
              'rules': {}}
    for rule, (goal, paths, ranges, caveats) in PROFILES.items():
        snippets = []
        for key, start, end in ranges:
            lines = texts[key].splitlines()
            if end > len(lines):
                raise ValueError(f'Range ngoài file: {FILES[key]}:{end}')
            snippets.append({'file': JAVA + FILES[key], 'start': start, 'end': end,
                             'excerpt': '\n'.join(lines[start-1:end])})
        result['rules'][rule] = {'static_goal': goal, 'required_paths': paths, 'base_caveats': caveats, 'snippets': snippets}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('--output', type=Path, default=Path('rulepacks/default/base-reference.json'))
    args = parser.parse_args()
    data = snapshot(args.base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f"Saved {len(data['rules'])} rule profiles from {data['source']['commit']}")
