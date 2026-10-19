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
val acceptanceTarget = providers.gradleProperty("target").orNull.orEmpty()
    .replace('\\', '/').contains("integration_test/native_acceptance_test.dart")
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
        manifestPlaceholders["usesCleartextTraffic"] = "true"
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
