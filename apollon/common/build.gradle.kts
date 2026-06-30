plugins {
    id("java-library")
}

archivesBaseName = "apollon-common"

repositories {
    mavenCentral()
}

dependencies {
    compileOnly("org.jetbrains:annotations:24.0.0")

    // LWJGL + OpenGL
    implementation("org.lwjgl:lwjgl:${property("org.lwjgl.version")}")
    implementation("org.lwjgl:lwjgl-opengl:${property("org.lwjgl.version")}")

    // Minecraft mappings (compile only)
    compileOnly("net.fabricmc:yarn:${property("minecraft_version")}+build.1")
    compileOnly("net.fabricmc:fabric-loader:${property("fabric_loader_version")}")
}

java {
    withSourcesJar()
}
