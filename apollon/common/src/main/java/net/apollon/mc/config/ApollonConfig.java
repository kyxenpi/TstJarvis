package net.apollon.mc.config;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL20;
import org.lwjgl.opengl.GL30;
import org.lwjgl.opengl.GL43;

import java.io.*;
import java.nio.file.*;
import java.util.Properties;

public class ApollonConfig {
    private final Path configPath;
    private final Properties props;

    private GpuInfo gpuInfo;
    private int renderDistance;
    private int chunkBuildThreads;
    private boolean useComputeShaders;
    private boolean useGenerationalArenas;
    private boolean useEntityInstancing;
    private boolean useBindlessTextures;
    private boolean useHardwareOcclusion;
    private boolean enableShaderPacks;
    private boolean enableConnectedTextures;
    private boolean enableDynamicLighting;
    private boolean enableZoom;
    private int maxFps;
    private boolean vsync;
    private boolean fogOcclusion;

    public record GpuInfo(String name, String renderer, String version, int maxSamples, int maxTextureSize, boolean supportsCompute, boolean supportsBindless, boolean supportsIndirect) {}

    public ApollonConfig() {
        this.configPath = Path.of("config", "apollon.properties");
        this.props = new Properties();
        setDefaults();
        detectGpuInfo();
    }

    private void setDefaults() {
        renderDistance = 16;
        chunkBuildThreads = Math.max(2, Runtime.getRuntime().availableProcessors() - 1);
        useComputeShaders = false; // will be auto-detected
        useGenerationalArenas = true;
        useEntityInstancing = true;
        useBindlessTextures = false;
        useHardwareOcclusion = true;
        enableShaderPacks = true;
        enableConnectedTextures = true;
        enableDynamicLighting = true;
        enableZoom = true;
        maxFps = 260;
        vsync = false;
        fogOcclusion = true;
    }

    private void detectGpuInfo() {
        try {
            String name = GL11.glGetString(GL11.GL_RENDERER);
            String renderer = GL11.glGetString(GL11.GL_VENDOR);
            String version = GL11.glGetString(GL11.GL_VERSION);
            int maxSamples = GL11.glGetInteger(GL30.GL_MAX_SAMPLES);
            int maxTexSize = GL11.glGetInteger(GL11.GL_MAX_TEXTURE_SIZE);

            boolean supportsCompute = false;
            boolean supportsBindless = false;
            boolean supportsIndirect = false;

            if (version != null) {
                float v = parseGlVersion(version);
                supportsCompute = v >= 4.3f;
                supportsBindless = v >= 4.5f || (renderer != null && renderer.toLowerCase().contains("nvidia"));
                supportsIndirect = v >= 4.0f;
            }

            // Check extensions directly
            if (supportsCompute) {
                int numExt = GL11.glGetInteger(GL43.GL_NUM_EXTENSIONS);
                for (int i = 0; i < numExt; i++) {
                    String ext = GL20.glGetStringi(GL43.GL_EXTENSIONS, i);
                    if ("GL_ARB_bindless_texture".equals(ext)) supportsBindless = true;
                    if ("GL_ARB_multi_draw_indirect".equals(ext)) supportsIndirect = true;
                }
            }

            gpuInfo = new GpuInfo(
                name != null ? name : "Unknown",
                renderer != null ? renderer : "Unknown",
                version != null ? version : "Unknown",
                maxSamples, maxTexSize,
                supportsCompute, supportsBindless, supportsIndirect
            );
        } catch (Exception e) {
            gpuInfo = new GpuInfo("Fallback", "Unknown", "0.0", 0, 0, false, false, false);
        }
    }

    private float parseGlVersion(String version) {
        try {
            String[] parts = version.split("\\s+")[0].split("\\.");
            return Float.parseFloat(parts[0] + "." + (parts.length > 1 ? parts[1] : "0"));
        } catch (Exception e) {
            return 0f;
        }
    }

    public void autoDetectOptimalSettings() {
        if (gpuInfo == null) return;

        useComputeShaders = gpuInfo.supportsCompute();
        useBindlessTextures = gpuInfo.supportsBindless();

        boolean isIntel = gpuInfo.name() != null && gpuInfo.name().toLowerCase().contains("intel");
        boolean isApple = gpuInfo.name() != null && gpuInfo.name().toLowerCase().contains("apple");
        boolean isNvidia = gpuInfo.renderer() != null && gpuInfo.renderer().toLowerCase().contains("nvidia");

        if (isIntel || isApple) {
            useGenerationalArenas = true; // critical for Intel GPUs
            chunkBuildThreads = Math.max(2, Runtime.getRuntime().availableProcessors() / 2);
            useComputeShaders = false; // Intel compute shaders can be slow
        }

        if (isNvidia) {
            useBindlessTextures = true;
            useComputeShaders = true;
        }

        if (isApple) {
            vsync = true; // macOS benefits from vsync
            fogOcclusion = true;
        }

        ApollonMod.LOGGER.info("Apollon auto-detected optimal settings for GPU: {} ({}). Compute: {}, Bindless: {}, Arenas: {}",
            gpuInfo.name(), gpuInfo.renderer(), useComputeShaders, useBindlessTextures, useGenerationalArenas);
    }

    public void save() {
        try {
            Files.createDirectories(configPath.getParent());
            try (OutputStream os = Files.newOutputStream(configPath)) {
                props.store(os, "Apollon Configuration");
            }
        } catch (IOException e) {
            ApollonMod.LOGGER.error("Failed to save config", e);
        }
    }

    public void load() {
        if (Files.exists(configPath)) {
            try (InputStream is = Files.newInputStream(configPath)) {
                props.load(is);
                // Apply loaded properties...
            } catch (IOException e) {
                ApollonMod.LOGGER.warn("Failed to load config, using defaults", e);
            }
        }
    }

    public GpuInfo getGpuInfo() { return gpuInfo; }
    public int getRenderDistance() { return renderDistance; }
    public int getChunkBuildThreads() { return chunkBuildThreads; }
    public boolean useComputeShaders() { return useComputeShaders; }
    public boolean useGenerationalArenas() { return useGenerationalArenas; }
    public boolean useEntityInstancing() { return useEntityInstancing; }
    public boolean useBindlessTextures() { return useBindlessTextures; }
    public boolean useHardwareOcclusion() { return useHardwareOcclusion; }
    public boolean enableShaderPacks() { return enableShaderPacks; }
    public boolean enableConnectedTextures() { return enableConnectedTextures; }
    public boolean enableDynamicLighting() { return enableDynamicLighting; }
    public boolean enableZoom() { return enableZoom; }
    public int getMaxFps() { return maxFps; }
    public boolean isVsync() { return vsync; }
    public boolean useFogOcclusion() { return fogOcclusion; }
}
