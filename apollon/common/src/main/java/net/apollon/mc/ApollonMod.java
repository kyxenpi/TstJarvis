package net.apollon.mc;

import net.apollon.mc.config.ApollonConfig;
import net.apollon.mc.render.ApollonWorldRenderer;
import net.apollon.mc.render.shader.ShaderManager;
import net.apollon.mc.util.MemoryUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ApollonMod {
    public static final String MOD_ID = "apollon";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static ApollonMod instance;
    private ApollonConfig config;
    private ApollonWorldRenderer worldRenderer;
    private ShaderManager shaderManager;

    public ApollonMod() {
        instance = this;
    }

    public static ApollonMod getInstance() {
        return instance;
    }

    public void onInitialize() {
        LOGGER.info("Apollon v{} initializing...", getClass().getPackage().getImplementationVersion());

        MemoryUtil.ensureDirectMemoryAccess();
        this.config = new ApollonConfig();
        this.config.load();

        this.shaderManager = new ShaderManager();
        this.shaderManager.initialize();

        this.worldRenderer = new ApollonWorldRenderer();
        this.worldRenderer.initialize();

        LOGGER.info("Apollon initialized. GPU: {}, Renderer: {}",
            config.getGpuInfo().name(),
            config.getGpuInfo().renderer());

        config.autoDetectOptimalSettings();
    }

    public ApollonConfig getConfig() {
        return config;
    }

    public ApollonWorldRenderer getWorldRenderer() {
        return worldRenderer;
    }

    public ShaderManager getShaderManager() {
        return shaderManager;
    }
}
