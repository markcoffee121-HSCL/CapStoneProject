import json, time, requests

BASE = "http://127.0.0.1:9009"

def test_healthz():
    r = requests.get(f"{BASE}/healthz", timeout=5)
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    print("✓ healthz check passed")

def test_research_quick():
    body = {"topic": "boomerang physics", "depth": "quick", "max_sources": 3}
    r = requests.post(f"{BASE}/research", json=body, timeout=10)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"✓ Created run: {run_id}")
    
    done = False
    for i in range(60):
        time.sleep(1)
        runs = requests.get(f"{BASE}/runs", timeout=5).json()
        row = next((x for x in runs if x["run_id"] == run_id), None)
        if row and row["status"] == "completed":
            done = True
            print(f"✓ Run completed successfully after {i+1} seconds")
            break
        elif row and row["status"] == "error":
            print(f"✗ Run failed with error: {row.get('error', 'unknown')}")
            assert False, f"Run failed: {row.get('error', 'unknown')}"
    
    assert done, "Run did not complete in 60 seconds"

if __name__ == "__main__":
    print("Running smoke tests...")
    test_healthz()
    test_research_quick()
    print("\n✓ All tests passed!")