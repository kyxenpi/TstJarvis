pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
        maven("https://maven.fabricmc.net")
        maven("https://maven.neoforged.net/releases")
        maven("https://maven.caffeinemc.net/releases")
    }
}

rootProject.name = "apollon"

include("common")
include("fabric")
include("neoforge")
