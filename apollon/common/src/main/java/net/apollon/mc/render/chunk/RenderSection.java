package net.apollon.mc.render.chunk;

public class RenderSection {
    private final int x, y, z;
    private final long regionKey;
    private ChunkMesh mesh;
    private BuildState state;
    private boolean needsRebuild;
    private int buildPriority;

    public enum BuildState {
        IDLE,
        BUILDING,
        COMPLETED,
        UPLOADED
    }

    public RenderSection(int x, int y, int z) {
        this.x = x;
        this.y = y;
        this.z = z;
        this.regionKey = RenderSectionManager.getRegionKey(x, y, z);
        this.state = BuildState.IDLE;
        this.needsRebuild = true;
        this.buildPriority = 0;
    }

    public int getX() { return x; }
    public int getY() { return y; }
    public int getZ() { return z; }
    public long getRegionKey() { return regionKey; }
    public ChunkMesh getMesh() { return mesh; }
    public void setMesh(ChunkMesh mesh) { this.mesh = mesh; }
    public BuildState getBuildState() { return state; }
    public void setBuildState(BuildState s) { this.state = s; }
    public boolean needsRebuild() { return needsRebuild; }
    public void setNeedsRebuild(boolean v) { this.needsRebuild = v; }
    public int getBuildPriority() { return buildPriority; }
    public void setBuildPriority(int p) { this.buildPriority = p; }
}
