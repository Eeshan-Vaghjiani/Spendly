import java.io.FileInputStream
import java.util.Properties
import java.util.Base64

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Opt-in acceptance APKs have their own package/storage and use debug signing.
val dartDefines = providers.gradleProperty("dart-defines").orNull.orEmpty()
    .split(',').filter { it.isNotBlank() }
    .map { String(Base64.getDecoder().decode(it), Charsets.UTF_8) }
val acceptanceBuild = dartDefines.contains("SPENDLY_ACCEPTANCE_BUILD=true")
val smsCapability = dartDefines.contains("SPENDLY_SMS_CAPABILITY=true")
val smsTestSource = dartDefines.contains("SPENDLY_SMS_TEST_SOURCE=true")
val smsEmulatorLab = dartDefines.contains("SPENDLY_SMS_EMULATOR_LAB=true")
check(!smsTestSource || (acceptanceBuild && smsCapability)) { "Synthetic SMS sources require the separate acceptance build." }
check(!smsEmulatorLab || (acceptanceBuild && smsCapability && !smsTestSource)) { "Emulator SMS labs must use the separate debug acceptance package." }
check(!acceptanceBuild || !smsCapability || smsTestSource || smsEmulatorLab) { "Acceptance APKs must never access a personal SMS inbox." }
val acceptanceTarget = providers.gradleProperty("target").orNull.orEmpty()
    .replace('\\', '/').let { it.contains("integration_test/native_acceptance_test.dart") || it.contains("integration_test/mpesa_sms_acceptance_test.dart") || it.contains("tool/mpesa_sms_lifecycle_main.dart") }
check(!acceptanceTarget || acceptanceBuild) {
    "Native acceptance tests require --dart-define=SPENDLY_ACCEPTANCE_BUILD=true."
}
check(!acceptanceBuild || gradle.startParameter.taskNames.none { it.contains("release", ignoreCase = true) }) {
    "Spendly acceptance builds must use debug tasks."
}
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
val hasReleaseSigning = !acceptanceBuild && keystorePropertiesFile.exists()
if (hasReleaseSigning) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    namespace = "com.evagh.capstone.spending_support"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion
    buildFeatures { buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "com.evagh.capstone.spending_support" + if (acceptanceBuild) ".acceptance" else ""
        manifestPlaceholders["appLabel"] = if (acceptanceBuild) "Spendly Acceptance" else "Spendly"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        buildConfigField("boolean", "MPESA_SMS_CAPABILITY", smsCapability.toString())
        buildConfigField("boolean", "MPESA_SMS_TEST_SOURCE", smsTestSource.toString())
        buildConfigField("boolean", "MPESA_SMS_EMULATOR_LAB", smsEmulatorLab.toString())
        manifestPlaceholders["usesCleartextTraffic"] = "true"
    }

    // The default distribution manifest has no SMS permission, receiver or job.
    // Generate an opt-in overlay from the tracked base instead of maintaining
    // divergent copies of the Flutter activity/security configuration.
    if (smsCapability) {
        val generated = layout.buildDirectory.file("generated/mpesa/AndroidManifest.xml").get().asFile
        generated.parentFile.mkdirs()
        val base = file("src/main/AndroidManifest.xml").readText()
        generated.writeText(base.replace("    <application", """
    <uses-permission android:name="android.permission.READ_SMS"/>
    <uses-permission android:name="android.permission.RECEIVE_SMS"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <application"""
        ).replace("    </application>", """
        <receiver android:name=".mpesa.MpesaSmsReceiver" android:exported="true" android:enabled="false"
            android:permission="android.permission.BROADCAST_SMS">
            <intent-filter><action android:name="android.provider.Telephony.SMS_RECEIVED"/></intent-filter>
        </receiver>
        <service android:name=".mpesa.MpesaJobService" android:exported="true"
            android:permission="android.permission.BIND_JOB_SERVICE"/>
    </application>"""))
        sourceSets.getByName("main").manifest.srcFile(generated)
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            signingConfig = if (hasReleaseSigning) {
                signingConfigs.getByName("release")
            } else {
                // Local release testing only. Play uploads must use key.properties.
                signingConfigs.getByName("debug")
            }
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
