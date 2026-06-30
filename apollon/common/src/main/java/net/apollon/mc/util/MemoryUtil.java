package net.apollon.mc.util;

import sun.misc.Unsafe;
import java.lang.reflect.Field;

public final class MemoryUtil {
    private static volatile Unsafe UNSAFE;
    private static boolean AVAILABLE = false;

    static {
        try {
            Field f = Unsafe.class.getDeclaredField("theUnsafe");
            f.setAccessible(true);
            UNSAFE = (Unsafe) f.get(null);
            AVAILABLE = true;
        } catch (Exception e) {
            // Fallback: unsafe not available (should never happen on standard JVM)
        }
    }

    public static void ensureDirectMemoryAccess() {
        if (!AVAILABLE) {
            throw new RuntimeException("Apollon requires sun.misc.Unsafe - are you on a standard JVM?");
        }
    }

    public static Unsafe getUnsafe() {
        return UNSAFE;
    }

    public static long allocate(long bytes) {
        return UNSAFE.allocateMemory(bytes);
    }

    public static void free(long address) {
        UNSAFE.freeMemory(address);
    }

    public static void copyMemory(long src, long dst, long bytes) {
        UNSAFE.copyMemory(src, dst, bytes);
    }

    public static void setMemory(long address, long bytes, byte value) {
        UNSAFE.setMemory(address, bytes, value);
    }

    public static int getInt(long address) {
        return UNSAFE.getInt(address);
    }

    public static void putInt(long address, int value) {
        UNSAFE.putInt(address, value);
    }

    public static float getFloat(long address) {
        return UNSAFE.getFloat(address);
    }

    public static void putFloat(long address, float value) {
        UNSAFE.putFloat(address, value);
    }

    public static long getLong(long address) {
        return UNSAFE.getLong(address);
    }

    public static void putLong(long address, long value) {
        UNSAFE.putLong(address, value);
    }

    private MemoryUtil() {}
}
