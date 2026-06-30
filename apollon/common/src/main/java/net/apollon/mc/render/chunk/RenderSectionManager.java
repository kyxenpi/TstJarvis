package net.apollon.mc.render.chunk;

import net.apollon.mc.ApollonMod;
import net.apollon.mc.render.ApollonWorldRenderer;
import net.apollon.mc.render.culling.FrustumCuller;
import net.apollon.mc.render.culling.OcclusionCuller;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Coordinates chunk rendering lifecycle.
 * Improvement over Sodium's RenderSectionManager:
 * - Lock-free section tracking via ConcurrentHashMap
 * - Generational region management to avoid buffer thrashing
 * - Predictable rebuild scheduling with priority queue
 */
public class RenderSectionManager {
    private final ApollonWorldRenderer renderer;
    private final Map<Long, RenderSection> sections;
    private final Map<Long, RenderRegion> regions;
    private final PriorityQueue<RenderSection> rebuildQueue;
    private final AtomicInteger pendingBuilds;

    // Region dimensions: 8x4x8 sections per region (same as Sodium for compat)
    private static final int REGION_SIZE_X = 8;
    private static final int REGION_SIZE_Y = 4;
    private static final int REGION_SIZE_Z = 8;

    public RenderSectionManager(ApollonWorldRenderer renderer) {
        this.renderer = renderer;
        this.sections = new ConcurrentHashMap<>();
        this.regions = new ConcurrentHashMap<>();
        this.rebuildQueue = new PriorityQueue<>(
            Comparator.comparingInt(RenderSection::getBuildPriority).reversed()
        );
        this.pendingBuilds = new AtomicInteger(0);
    }

    public void updateChunks() {
        // Drain rebuild queue and submit to chunk builder
        var builder = renderer.getChunkBuilder();
        int maxSubmits = 16; // Limit per frame to avoid lag spikes

        for (int i = 0; i < maxSubmits; i++) {
            var section = rebuildQueue.poll();
            if (section == null) break;

            if (section.needsRebuild()) {
                builder.submitBuild(section);
                pendingBuilds.incrementAndGet();
                section.setBuildState(RenderSection.BuildState.BUILDING);
            }
        }
    }

    public void uploadChunks() {
        var builder = renderer.getChunkBuilder();
        var completed = builder.drainCompleted();

        for (var result : completed) {
            var section = result.section();
            var mesh = result.mesh();

            section.setMesh(mesh);
            section.setBuildState(RenderSection.BuildState.COMPLETED);

            // Assign mesh to parent region
            var region = getOrCreateRegion(section.getRegionKey());
            region.addSection(section);

            pendingBuilds.decrementAndGet();
        }
    }

    public List<RenderRegion> buildVisibleList(FrustumCuller frustum, OcclusionCuller occlusion, boolean fogOcclusion) {
        var visible = new ArrayList<RenderRegion>();
        var cameraRegion = getRegionKey(
            (int) frustum.getCameraX() >> 4,
            (int) frustum.getCameraY() >> 4,
            (int) frustum.getCameraZ() >> 4
        );

        for (var entry : regions.entrySet()) {
            var region = entry.getValue();

            // Skip invisible regions (frustum test)
            if (!frustum.isRegionVisible(region)) continue;

            // Hardware occlusion query test (if supported)
            if (frustum.supportsOcclusion() && region.hasOcclusionQuery()) {
                if (!occlusion.isVisible(region)) continue;
            }

            // Fog culling: skip if entirely fogged
            if (fogOcclusion && region.isFullyFogged(frustum.getRenderDistance())) continue;

            visible.add(region);

            // Update region for next frame
            region.prepareForRender();
        }

        return visible;
    }

    public void scheduleRebuild(int chunkX, int chunkY, int chunkZ, boolean important) {
        long key = getSectionKey(chunkX, chunkY, chunkZ);
        var section = sections.computeIfAbsent(key, k -> new RenderSection(chunkX, chunkY, chunkZ));

        if (important) {
            section.setBuildPriority(Integer.MAX_VALUE);
        } else {
            section.setBuildPriority(section.getBuildPriority() + 1);
        }

        section.setNeedsRebuild(true);
        rebuildQueue.offer(section);
    }

    public RenderRegion getOrCreateRegion(long regionKey) {
        return regions.computeIfAbsent(regionKey, RenderRegion::new);
    }

    public static long getSectionKey(int x, int y, int z) {
        return ((long) x & 0x3FFFFFF) << 38
             | ((long) y & 0x3FFFFFF) << 12
             | ((long) z & 0x3FFFFFF);
    }

    public static long getRegionKey(int sectionX, int sectionY, int sectionZ) {
        int rx = Math.floorDiv(sectionX, REGION_SIZE_X);
        int ry = Math.floorDiv(sectionY, REGION_SIZE_Y);
        int rz = Math.floorDiv(sectionZ, REGION_SIZE_Z);
        return getSectionKey(rx, ry, rz);
    }

    public int getPendingBuilds() { return pendingBuilds.get(); }
}
