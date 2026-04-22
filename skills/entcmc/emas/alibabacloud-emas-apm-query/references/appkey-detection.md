# Detecting `app_key` and `os` from the user's workspace

At runtime this Skill **does NOT assume** the user's workspace is one of the 6 demo projects. Instead it uses the generic rules below to scan the user's own app project. After a hit, the Skill MUST echo it back to the user for confirmation.

## Detection order

1. First determine which project type the user currently has open (or has provided): existence of `build.gradle` / `AndroidManifest.xml` -> Android; `*.xcodeproj` / `Info.plist` -> iOS; `module.json5` + `ets/` -> HarmonyOS; `pubspec.yaml` -> Flutter; `Assets/` + `ProjectSettings/` + `*.cs` -> Unity; `package.json` plus an H5 SDK -> H5.
2. Run the grep / AST rules from the matching platform section.
3. Exactly one hit -> echo and ask the user to confirm; multiple hits -> list all candidates; zero hits -> ask the user proactively.
4. Flutter / Unity cross-platform apps usually ship **AppKeys for both Android and iOS**; the user must additionally pick which side this query targets.

---

## Android (Java / Kotlin)

SDK package: `com.aliyun.emas.apm`; typical facade class: `com.aliyun.emas.apm.Apm`.

### Common initialization patterns

```java
Apm.preStart(new ApmOptions.Builder()
        .setAppKey("123456789")
        .setAppSecret("...")
        .setAppRsaSecret("...")
        .addComponent(ApmCrashAnalysisComponent.class)
        .addComponent(ApmPerformanceComponent.class)
        .addComponent(ApmRemoteLogComponent.class)
        .addComponent(ApmMemMonitorComponent.class)
        .build());
Apm.start();
```

### grep rules

```bash
# Direct assignment in Java / Kotlin source
rg -n --type-add 'kts:*.kts' -t java -t kotlin -t kts \
   -e 'setAppKey\s*\(\s*"(\d+)"' \
   -e 'APP_KEY\s*=\s*"(\d+)"' \
   -e 'appKey\s*=\s*"(\d+)"' <workspace>

# AndroidManifest meta-data
rg -n --glob '**/AndroidManifest.xml' \
   -e 'android:name="com\.(alibaba|aliyun)\.[a-zA-Z_.]*[aA]pp[kK]ey"\s+android:value="(\d+)"' <workspace>

# gradle / properties
rg -n --glob '*.gradle*' --glob '*.properties' \
   -e 'APM_APP_KEY\s*=\s*"?(\d+)"?' <workspace>
```

### Additional sources

- `BuildConfig.APM_APP_KEY`: injected by `buildConfigField "String", "APM_APP_KEY", "\"123456789\""`; read the raw definition from `build.gradle(.kts)`.
- Demo code that reads the App Key dynamically from SharedPreferences: the value usually comes from a constant (`APP_KEY = "..."`) or a gradle default; just use the constant.

### os value

Android project hit -> `--os android`.

---

## iOS (Objective-C / Swift)

SDK entry classes: `EAPMApm`, `EAPMOptions`.

### Common initialization patterns

```objc
EAPMOptions *options = [[EAPMOptions alloc] initWithAppKey:@"123456789"
                                                appSecret:@"..."];
options.appRsaSecret = @"...";
options.sdkComponents = @[ ... ];
[EAPMApm startWithOptions:options];
```

Swift equivalent:

```swift
let options = EAPMOptions(appKey: "123456789", appSecret: "...")
options.appRsaSecret = "..."
EAPMApm.start(with: options)
```

### grep rules

```bash
# OC
rg -n -g '*.{m,mm,h}' \
   -e 'initWithAppKey:\s*@"(\d+)"' \
   -e 'setAppKey:\s*@"(\d+)"' \
   -e '\.appKey\s*=\s*@"(\d+)"' <workspace>

# Swift
rg -n -g '*.swift' \
   -e 'EAPMOptions\s*\(\s*appKey:\s*"(\d+)"' \
   -e '\.appKey\s*=\s*"(\d+)"' <workspace>

# Common custom keys in Info.plist / xcconfig
rg -n -g '*.plist' -g '*.xcconfig' \
   -e 'APMAppKey|AliyunAPMAppKey|EAPMAppKey' <workspace>
```

### os value

iOS project hit -> `--os iphoneos` (**not** `ios`).

---

## HarmonyOS (ArkTS)

SDK package: `@aliyun/apm`.

### Common initialization patterns

```typescript
import { APM, APMConfig, EMAS_APM_Config } from '@aliyun/apm';

APM.init(new EMAS_APM_Config({
  appKey: '233584108',
  context: await getUIAbilityContext(),
  appSecret: '...',
  ...
}));
APM.start();

// Or a plain APMConfig literal
const config: APMConfig = {
  context: await getUIAbilityContext(),
  appKey: '233584108',
  appSecret: '...',
};
APM.init(config, [crashAnalysisApi]);
APM.start();
```

### grep rules

```bash
rg -n -g '*.{ets,ts,json5,json}' \
   -e "appKey:\s*['\"](\d+)['\"]" \
   -e "from\s+['\"]@aliyun/apm['\"]" <workspace>
```

### os value

HarmonyOS project hit -> `--os harmony`.

---

## Flutter (Dart)

SDK package: `alibabacloud_apm` / `apm_flutter`. Core class: `ApmOptions`.

### Common initialization patterns

```dart
import 'package:alibabacloud_apm/alibabacloud_apm.dart';

const options = ApmOptions(
  appKey: '333854661',      // Android
  appSecret: '...',
  appRsaSecret: '...',
  channel: 'store',
);
await Apm.instance.start(options);
```

Cross-platform demos typically **keep a per-platform copy of AppKey**:

```dart
static const ApmOptionsFields defaultIosDeveloperFields = ApmOptionsFields(
  appKey: '335628209',
  ...
);
static const ApmOptionsFields defaultAndroidFields = ApmOptionsFields(
  appKey: '333854661',
  ...
);
```

### grep rules

```bash
rg -n -g '*.dart' \
   -e "ApmOptions\s*\(\s*appKey:\s*['\"](\d+)['\"]" \
   -e "appKey:\s*['\"](\d+)['\"]" <workspace>
```

### os value

Flutter is cross-platform; always ask the user whether this query targets `android` or `iphoneos`. If the grep matches per-platform constants like `defaultAndroidFields` and `defaultIosXxxFields`, have the user pick one.

Custom exceptions reported from Dart / Kotlin / Swift / ObjC end up under `biz-module=custom`, and `customErrorLanguage` (see [../assets/system-filters/custom-android.json](../assets/system-filters/custom-android.json)) is tagged `Dart`; when this Skill queries Flutter custom exceptions, `--os` is still `android` / `iphoneos`.

---

## Unity (C#)

SDK package: `alicloud-apm`. Core classes: `Aliyun.Apm.ApmOptions` / `Aliyun.Apm.Apm`.

### Common initialization patterns

```csharp
var options = new ApmOptions(appKey, appSecret, appRsaSecret)
{
    SdkComponents = SDKComponents.Crash | SDKComponents.Performance,
    Channel = "store",
};
Apm.Start(options);
```

The `DemoConfig { public string appKey = "..." }` + `ApmDemoUI.GetRolePreset` pattern is also common in demos.

### grep rules

```bash
rg -n -g '*.cs' \
   -e 'new\s+ApmOptions\s*\(\s*"(\d+)"' \
   -e 'AppKey\s*=\s*"(\d+)"' \
   -e 'appKey\s*=\s*"(\d+)"' <workspace>
```

If the demo stores AppKey in a ScriptableObject / JSON, do a second pass under `Assets/`.

### os value

Same as Flutter: have the user pick Android or iOS. Unity custom exceptions (C#) are reported to `custom` with `customErrorLanguage=C#` / `CSharp` (exact value per [../assets/system-filters/custom-android.json](../assets/system-filters/custom-android.json)).

---

## H5 (JavaScript / TypeScript)

SDK class: `EMAS_APM` (constructor-based init).

### Common initialization patterns

```html
<script src="emas-apm.min.js"></script>
<script>
  var sdk = new EMAS_APM({
    appKey: '335102493',
    appSecret: '...',
    appVersion: '1.0.0',
  });
  sdk.start();
</script>
```

Or as an ES module:

```typescript
import { EMAS_APM } from '@alicloud/apm-h5-sdk';

const sdk = new EMAS_APM({ appKey: '335102493', appSecret: '...' });
sdk.start();
```

### grep rules

```bash
rg -n -g '*.{js,ts,jsx,tsx,vue,html,htm}' \
   -e "new\s+EMAS_APM\s*\(\s*\{\s*appKey:\s*['\"]([^'\"]+)['\"]" \
   -e "appKey:\s*['\"]([A-Za-z0-9]+)['\"]" <workspace>
```

H5 AppKeys are not necessarily pure digits, but they are still issued by the console.

### os value

H5 project -> `--os h5`. Note: H5 bizModules are typically `h5JsError` / `h5WhiteScreen` / `h5Pv`; this Skill focuses on the 6 mobile types. For H5, consult the APM console H5 section; it is out of scope for this Skill.

---

## Generic fallback

When every grep misses, the Skill should ask the user:

> I could not find APM SDK initialization code in the current workspace. Please provide:
>
> 1. App Key (find it in the [EMAS console](https://emas.console.aliyun.com/) app detail page; usually 9 digits)
> 2. Platform: `android` / `iphoneos` / `harmony` / `h5` (for Flutter / Unity, pick android or iphoneos per the actual build target)

Only enter the main flow after confirmation.
