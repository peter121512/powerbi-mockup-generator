plugins { id("com.android.application") }
android {
    namespace = "com.peterdev.dashboardmockup"
    compileSdk = 34
    defaultConfig { applicationId = "com.peterdev.dashboardmockup"; minSdk = 24; targetSdk = 34; versionCode = 1; versionName = "1.0" }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
dependencies { implementation("androidx.appcompat:appcompat:1.6.1") }
