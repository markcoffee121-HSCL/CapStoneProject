import pytest
import asyncio
import time
from httpx import AsyncClient
from app.main import app
from app.storage.runs import store
from app.graph.state import make_initial_state

BASE_URL = "http://127.0.0.1:9009"

@pytest.fixture
def client():
    """Create an async HTTP client for testing"""
    return AsyncClient(app=app, base_url=BASE_URL)


class TestHealthEndpoints:
    """Test basic health and info endpoints"""
    
    @pytest.mark.asyncio
    async def test_healthz(self, client):
        """Test health check endpoint"""
        response = await client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data
        assert "groq_model" in data
        assert "search_provider" in data
    
    @pytest.mark.asyncio
    async def test_root(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestResearchEndpoints:
    """Test research run creation and management"""
    
    @pytest.mark.asyncio
    async def test_create_research_run(self, client):
        """Test creating a new research run"""
        payload = {
            "topic": "test topic for pytest",
            "depth": "quick",
            "max_sources": 3
        }
        response = await client.post("/research", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert len(data["run_id"]) > 0
    
    @pytest.mark.asyncio
    async def test_create_research_with_domains(self, client):
        """Test creating research with domain restrictions"""
        payload = {
            "topic": "quantum computing",
            "depth": "standard",
            "max_sources": 5,
            "domains": ["arxiv.org", "nature.com"]
        }
        response = await client.post("/research", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
    
    @pytest.mark.asyncio
    async def test_list_runs(self, client):
        """Test listing all runs"""
        response = await client.get("/runs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_specific_run(self, client):
        """Test getting a specific run by ID"""
        # First create a run
        payload = {"topic": "test", "depth": "quick", "max_sources": 2}
        create_response = await client.post("/research", json=payload)
        run_id = create_response.json()["run_id"]
        
        # Wait a moment for it to be stored
        await asyncio.sleep(0.5)
        
        # Get the run
        response = await client.get(f"/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] in ["pending", "running", "completed", "error"]


class TestMetrics:
    """Test metrics endpoint"""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        text = response.text
        assert "http_requests_total" in text or len(text) > 0


class TestStateManagement:
    """Test graph state creation and manipulation"""
    
    def test_make_initial_state_defaults(self):
        """Test creating initial state with defaults"""
        state = make_initial_state(
            run_id="test-123",
            topic="test topic"
        )
        assert state["run_id"] == "test-123"
        assert state["topic"] == "test topic"
        assert state["depth"] == "standard"
        assert state["max_sources"] == 6  # standard preset
        assert "limits" in state
        assert state["results"] == []
        assert state["docs"] == []
        assert state["notes"] == []
        assert state["report_md"] == ""
    
    def test_make_initial_state_quick_depth(self):
        """Test quick depth preset"""
        state = make_initial_state(
            run_id="test-123",
            topic="test",
            depth="quick"
        )
        assert state["max_sources"] == 3
        assert state["limits"]["max_sources"] == 3
        assert state["limits"]["summary_words"] == 120
    
    def test_make_initial_state_deep_depth(self):
        """Test deep depth preset"""
        state = make_initial_state(
            run_id="test-123",
            topic="test",
            depth="deep"
        )
        assert state["max_sources"] == 10
        assert state["limits"]["max_sources"] == 10
        assert state["limits"]["summary_words"] == 350
    
    def test_make_initial_state_custom_max_sources(self):
        """Test overriding max_sources"""
        state = make_initial_state(
            run_id="test-123",
            topic="test",
            depth="standard",
            max_sources=15
        )
        assert state["max_sources"] == 15  # Override should work
    
    def test_make_initial_state_with_domains(self):
        """Test state with domain restrictions"""
        state = make_initial_state(
            run_id="test-123",
            topic="test",
            domains=["example.com", "test.org"]
        )
        assert state["domains"] == ["example.com", "test.org"]


class TestRunStorage:
    """Test run storage operations"""
    
    def test_create_run(self):
        """Test creating a run in storage"""
        rs = store.create(topic="storage test", depth="quick")
        assert rs.run_id is not None
        assert rs.topic == "storage test"
        assert rs.depth == "quick"
        assert rs.status == "pending"
        assert rs.created_at is not None
    
    def test_get_run(self):
        """Test retrieving a run from storage"""
        rs = store.create(topic="get test", depth="standard")
        retrieved = store.get(rs.run_id)
        assert retrieved is not None
        assert retrieved.run_id == rs.run_id
        assert retrieved.topic == "get test"
    
    def test_start_run(self):
        """Test starting a run"""
        rs = store.create(topic="start test")
        store.start(rs.run_id)
        retrieved = store.get(rs.run_id)
        assert retrieved.status == "running"
        assert retrieved.started_at is not None
    
    def test_finish_run(self):
        """Test finishing a run"""
        rs = store.create(topic="finish test")
        store.start(rs.run_id)
        store.finish(rs.run_id)
        retrieved = store.get(rs.run_id)
        assert retrieved.status == "completed"
        assert retrieved.finished_at is not None
    
    def test_error_run(self):
        """Test marking a run as errored"""
        rs = store.create(topic="error test")
        store.start(rs.run_id)
        store.error(rs.run_id, "Test error message")
        retrieved = store.get(rs.run_id)
        assert retrieved.status == "error"
        assert retrieved.error == "Test error message"
    
    def test_list_all_runs(self):
        """Test listing all runs"""
        # Create a few runs
        store.create(topic="list test 1")
        store.create(topic="list test 2")
        all_runs = store.list_all()
        assert len(all_runs) >= 2
        assert all(hasattr(r, "run_id") for r in all_runs)


class TestEndToEnd:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_research_pipeline(self, client):
        """Test a complete research run from start to finish"""
        # Create a run
        payload = {
            "topic": "photosynthesis basics",
            "depth": "quick",
            "max_sources": 2
        }
        response = await client.post("/research", json=payload)
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        
        # Poll for completion (max 60 seconds)
        max_attempts = 60
        for i in range(max_attempts):
            await asyncio.sleep(1)
            response = await client.get(f"/runs/{run_id}")
            data = response.json()
            
            if data["status"] == "completed":
                assert data["finished_at"] is not None
                # Try to get the report
                report_response = await client.get(f"/runs/{run_id}/report")
                assert report_response.status_code == 200
                return
            elif data["status"] == "error":
                pytest.fail(f"Run failed with error: {data.get('error')}")
        
        pytest.fail("Run did not complete within 60 seconds")


class TestNotifyEndpoint:
    """Test n8n notification endpoint"""
    
    @pytest.mark.asyncio
    async def test_notify_nonexistent_run(self, client):
        """Test notifying with non-existent run ID"""
        response = await client.post("/runs/fake-id-123/notify")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["error"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_notify_existing_run(self, client):
        """Test notifying with valid run ID"""
        # Create a run first
        payload = {"topic": "notify test", "depth": "quick", "max_sources": 2}
        create_response = await client.post("/research", json=payload)
        run_id = create_response.json()["run_id"]
        
        # Wait a moment
        await asyncio.sleep(0.5)
        
        # Try to notify (might fail if n8n not running, but endpoint should work)
        response = await client.post(f"/runs/{run_id}/notify")
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()