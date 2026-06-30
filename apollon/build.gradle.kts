plugins {
    id("java-library")
    id("maven-publish")
}

group = "net.apollon.mc"
version = "1.0.0"

subprojects {
    apply(plugin = "java-library")
    apply(plugin = "maven-publish")

    java {
        toolchain { languageVersion.set(JavaLanguageVersion.of(21)) }
        withSourcesJar()
    }

    repositories {
        mavenCentral()
        maven("https://maven.fabricmc.net")
        maven("https://maven.neoforged.net/releases")
        maven("https://maven.caffeinemc.net/releases")
    }
}
