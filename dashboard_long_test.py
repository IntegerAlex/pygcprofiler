import gc
import time


def churn_memory(duration_seconds: float = 60.0) -> None:
    """Generate sustained GC activity for dashboard visualization.

    This is intentionally CPU/memory heavy – use only in non‑prod or
    on an isolated instance.
    """
    print(f"Starting long GC churn for {duration_seconds:.0f}s...")
    start = time.time()
    iteration = 0

    while time.time() - start < duration_seconds:
        iteration += 1

        # Allocate and drop lots of short‑lived objects
        data = []
        for _ in range(5_000):
            data.append([0] * 500)
        del data

        # Force a GC cycle every few iterations to make events obvious
        if iteration % 5 == 0:
            gc.collect()

        if iteration % 10 == 0:
            elapsed = time.time() - start
            print(f"[dashboard_long_test] iteration={iteration}, elapsed={elapsed:5.1f}s")

        # Small sleep so we don’t completely starve the CPU
        time.sleep(0.05)

    print("GC churn complete.")


if __name__ == "__main__":
    churn_memory()


