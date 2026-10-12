# Kermit2Go

Flutter source prototype for iOS/Android. No native runner, signed build or
USB driver is included yet. Flutter is not installed in the development
workspace, so mobile compilation and device behavior remain unverified.

With Flutter installed, generate native runners without replacing the app:

```sh
cd kermit2go
flutter create --platforms=android,ios --project-name=kermit2go .
flutter pub get
```

Keep the existing `lib/main.dart` and dependency entries in `pubspec.yaml`.
Use a current Flutter SDK compatible with the plugins. Then configure:

- Android: `INTERNET`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION` in
  `android/app/src/main/AndroidManifest.xml`. For the HTTP development bridge,
  enable `android:usesCleartextTraffic="true"` on the application. Do not expose
  the bridge on public networks. Use compile SDK 35 or newer for geolocator.
- iOS: add `NSLocationWhenInUseUsageDescription` and
  `NSLocalNetworkUsageDescription` explanations in `ios/Runner/Info.plist`.
  Configure ATS for your local HTTP development endpoint (a scoped exception
  for a local hostname, or development-only `NSAllowsArbitraryLoads`). Use
  HTTPS and remove broad exceptions for distribution. Set the geolocator Apple
  `BYPASS_PERMISSION_LOCATION_ALWAYS=1` preprocessor definition for this
  foreground-only app, as described in the plugin documentation.
- Run `flutter analyze`, then `flutter run` on physical Android and iPhone.
  Verify permissions, local-network access, disconnect/reconnect, background
  pause, stale fixes, CSV export, and known calibrated test signals.

Surveys are flushed to application documents after each point. Export is
available after stopping. GPS accuracy and fix timestamp are retained with RF
readings. Failed or stale readings are not logged. Saved files remain in app
storage; a saved-survey browser and recovery/export UI are future work.

To map exported data on the desktop:

```sh
kermit generate-map -o /path/to/exported-survey --metric auto
```

The path excludes `.csv`. Map tiles need internet. The app's current relative
track is a preview, not a geographic basemap.

Next hardware milestone: implement Android USB permission/enumeration and an
RTL-SDR native driver adapter, verify USB-C host mode and power on the target
phone. The iPhone path uses an external Wi-Fi bridge unless a compatible
accessory with an iOS-supported protocol is selected. Wider RF coverage needs
frequency-sweep acquisition and per-frequency calibration before combining
non-overlapping bands in quadrature.
