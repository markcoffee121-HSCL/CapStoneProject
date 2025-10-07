import pytest
from app.graph.state import make_initial_state
from app.agents.planner import planner_node
from app.agents.searcher import searcher_node
from app.agents.synthesizer import synthesizer_node


class TestPlannerAgent:
    """Test planner agent functionality"""
    
    @pytest.mark.asyncio
    async def test_planner_creates_plan(self):
        """Test that planner generates a plan"""
        state = make_initial_state(
            run_id="test-planner",
            topic="artificial intelligence",
            depth="quick"
        )
        result = await planner_node(state)
        assert "plan" in result
        assert isinstance(result["plan"], list)
        assert len(result["plan"]) >= 3
        assert len(result["plan"]) <= 6


class TestSearcherAgent:
    """Test searcher agent functionality"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_searcher_finds_results(self):
        """Test that searcher finds search results"""
        state = make_initial_state(
            run_id="test-search",
            topic="python programming",
            depth="quick",
            max_sources=5
        )
        result = await searcher_node(state)
        assert "results" in result
        assert isinstance(result["results"], list)
        assert len(result["results"]) > 0
        # Check result structure
        if result["results"]:
            first = result["results"][0]
            assert "url" in first
            assert "title" in first


class TestSynthesizerAgent:
    """Test synthesizer agent functionality"""
    
    @pytest.mark.asyncio
    async def test_synthesizer_creates_report(self):
        """Test that synthesizer creates a markdown report"""
        state = make_initial_state(
            run_id="test-synth",
            topic="machine learning",
            depth="quick"
        )
        # Add some mock notes
        state["notes"] = [
            {"url": "http://example.com", "bullets": ["Test content"]},
            {"url": "http://test.org", "bullets": ["More content"]},
        ]
        
        result = await synthesizer_node(state)
        assert "report_md" in result
        assert len(result["report_md"]) > 0
        assert "# Research Brief:" in result["report_md"]
        assert "## Key Takeaways" in result["report_md"]
        assert "## Citations" in result["report_md"]