"""Press Run on this file to collect news every 15 minutes (stop with Ctrl+C)."""
from newstracker.cli import main

if __name__ == "__main__":
    print("Collecting news every 15 minutes. Press Ctrl+C to stop.", flush=True)
    main(["run"])
