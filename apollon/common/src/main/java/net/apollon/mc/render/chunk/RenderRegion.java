package net.apollon.mc.render.chunk;

import net.apollon.mc.render.vertex.CompactVertex;
import org.lwjgl.opengl.GL30;
import org.lwjgl.opengl.GL42;
import org.lwjgl.opengl.GL15;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Groups multiple RenderSections for batched rendering.
 * Improvements over Sodium's RenderRegion:
 * - Generational buffer allocation (no resize thrashing)
 * - Shared quad index buffer for memory savings
 * - Hardware occlusion query support
 */
public class RenderRegion {
    private final long key;
    private final List<RenderSection> sections;
    private ChunkMesh mergedMesh;
    private int occlusionQueryId;
    private boolean occlusionQueryPending;
    private boolean occlusionQueryResult;
    private long lastRenderTime;

    // Buffer arena tracking
    private long bufferGeneration;
    private int bufferCapacity;

    private static final AtomicInteger QUERY_COUNTER = new AtomicInteger(0);

    public RenderRegion(long key) {
        this.key = key;
        this.sections = Collections.synchronizedList(new ArrayList<>());
        this.occlusionQueryId = -1;
    }

    public void addSection(RenderSection section) {
        sections.add(section);
        mergedMesh = null; // invalidate merged mesh
    }

    public void removeSection(RenderSection section) {
        sections.remove(section);
        mergedMesh = null;
    }

    public ChunkMesh getMesh() {
        if (mergedMesh == null && !sections.isEmpty()) {
            mergeMeshes();
        }
        return mergedMesh;
    }

    private void mergeMeshes() {
        // Merge all section meshes into one region mesh for batched rendering
        // This is what allows multi-draw indirect to be efficient
        if (sections.isEmpty()) {
            mergedMesh = null;
            return;
        }

        int totalVerts = 0;
        int totalIndices = 0;
        int totalSections = 0;

        var validMeshes = new ArrayList<ChunkMesh>();
        for (var section : sections) {
            var m = section.getMesh();
            if (m != null && m.vertexCount() > 0) {
                validMeshes.add(m);
                totalVerts += m.vertexCount();
                totalIndices += m.indexCount();
                totalSections++;
            }
        }

        if (validMeshes.isEmpty()) {
            mergedMesh = null;
            return;
        }

        if (validMeshes.size() == 1) {
            mergedMesh = validMeshes.get(0);
            return;
        }

        // Allocate merged buffer
        var merged = new ChunkMesh(totalVerts, totalIndices, totalSections);
        int vertOffset = 0;
        int indexOffset = 0;

        for (var m : validMeshes) {
            // Copy vertex data
            CompactVertex.VertexBlock.copyVertices(m.getVertexBuffer(), merged.getVertexBuffer(), vertOffset, 0, m.vertexCount());
            // Copy index data with offset
            int[] srcIndices = m.getIndexBuffer();
            int[] dstIndices = merged.getIndexBuffer();
            for (int i = 0; i < m.indexCount(); i++) {
                dstIndices[indexOffset + i] = srcIndices[i] + vertOffset;
            }
            vertOffset += m.vertexCount();
            indexOffset += m.indexCount();
        }

        mergedMesh = merged;
    }

    public void prepareForRender() {
        // Allocate occlusion query if needed
        if (occlusionQueryId == -1) {
            occlusionQueryId = GL15.glGenQueries();
        }

        // Issue occlusion query for next frame
        GL15.glBeginQuery(GL15.GL_SAMPLES_PASSED, occlusionQueryId);
    }

    public boolean hasOcclusionQuery() {
        return occlusionQueryId != -1;
    }

    public boolean isOcclusionQueryResult() {
        if (occlusionQueryId == -1) return true;
        int available = GL15.glGetQueryObjecti(occlusionQueryId, GL15.GL_QUERY_RESULT_AVAILABLE);
        if (available == GL15.GL_TRUE) {
            occlusionQueryResult = GL15.glGetQueryObjecti(occlusionQueryId, GL15.GL_QUERY_RESULT) > 0;
        }
        return occlusionQueryResult;
    }

    public boolean isFullyFogged(int renderDistance) {
        // Quick distance-based check
        return false; // Placeholder for fog culling
    }

    public long getKey() { return key; }
    public long getBufferGeneration() { return bufferGeneration; }
    public void setBufferGeneration(long gen) { this.bufferGeneration = gen; }
    public int getBufferCapacity() { return bufferCapacity; }
    public void setBufferCapacity(int cap) { this.bufferCapacity = cap; }
    public long getLastRenderTime() { return lastRenderTime; }
}
