import time
import random

def slow_random():
    start = time.time()
    x = random.randint(2, 9)

    # Keep working for at least 5 seconds
    while time.time() - start < 5:
        # Perform many multiplications per loop
        for _ in range(500_000):      # adjust this number for more/less load
            x = (x * x + 3) % 1_000_000_007

    return x

if __name__ == "__main__":
    print("Generating slow random number...")
    num = slow_random()
    print("Result:", num)
