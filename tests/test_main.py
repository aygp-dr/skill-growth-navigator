"""Tests for SkillGrowthNavigator learning path recommendation engine."""
import json

import pytest

from main import (
    CAREER_GOALS,
    DOMAINS,
    LEVEL_ORDER,
    SKILLS,
    app,
    get_recommendations,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    app.config["TESTING"] = True
    app.config["DB_PATH"] = db_path
    with app.test_client() as c:
        yield c


# ─── Skills Data Integrity ──────────────────────────────────────────────────


def test_exactly_30_skills():
    assert len(SKILLS) == 30


def test_six_skills_per_domain():
    for domain in DOMAINS:
        count = sum(1 for s in SKILLS.values() if s["domain"] == domain)
        assert count == 6, f"{domain} has {count} skills, expected 6"


def test_five_domains():
    assert len(DOMAINS) == 5
    assert set(DOMAINS) == {"backend", "frontend", "devops", "data", "security"}


def test_skills_have_required_fields():
    required = {"name", "domain", "level", "prerequisites", "estimated_hours", "resources"}
    for skill_id, skill in SKILLS.items():
        assert required.issubset(skill.keys()), f"{skill_id} missing fields"


def test_skill_levels_valid():
    for skill_id, skill in SKILLS.items():
        assert skill["level"] in LEVEL_ORDER, f"{skill_id} has invalid level: {skill['level']}"


def test_skill_domains_valid():
    for skill_id, skill in SKILLS.items():
        assert skill["domain"] in DOMAINS, f"{skill_id} has invalid domain: {skill['domain']}"


def test_each_skill_has_three_resources():
    for skill_id, skill in SKILLS.items():
        assert len(skill["resources"]) == 3, f"{skill_id} has {len(skill['resources'])} resources"
        for res in skill["resources"]:
            assert "title" in res and "url" in res, f"{skill_id} has malformed resource"
            assert res["url"].startswith("https://"), f"{skill_id} resource URL not HTTPS"


def test_estimated_hours_positive():
    for skill_id, skill in SKILLS.items():
        assert skill["estimated_hours"] > 0, f"{skill_id} has non-positive hours"


def test_prerequisites_exist():
    for skill_id, skill in SKILLS.items():
        for prereq in skill["prerequisites"]:
            assert prereq in SKILLS, f"{skill_id} has unknown prereq: {prereq}"


def test_no_self_prerequisites():
    for skill_id, skill in SKILLS.items():
        assert skill_id not in skill["prerequisites"], f"{skill_id} lists itself as prereq"


def test_no_circular_prerequisites():
    """DFS cycle detection across the prerequisite graph."""
    visited = set()
    in_stack = set()

    def has_cycle(node):
        visited.add(node)
        in_stack.add(node)
        for prereq in SKILLS[node]["prerequisites"]:
            if prereq not in visited:
                if has_cycle(prereq):
                    return True
            elif prereq in in_stack:
                return True
        in_stack.discard(node)
        return False

    for skill_id in SKILLS:
        if skill_id not in visited:
            assert not has_cycle(skill_id), f"Cycle detected involving {skill_id}"


def test_beginner_skills_have_no_prerequisites():
    for skill_id, skill in SKILLS.items():
        if skill["level"] == "beginner":
            assert skill["prerequisites"] == [], (
                f"Beginner skill {skill_id} has prerequisites: {skill['prerequisites']}"
            )


# ─── Career Goals ───────────────────────────────────────────────────────────


def test_career_goals_exist():
    assert len(CAREER_GOALS) >= 5


def test_career_goals_have_required_fields():
    for goal_id, goal in CAREER_GOALS.items():
        assert "name" in goal, f"{goal_id} missing name"
        assert "description" in goal, f"{goal_id} missing description"
        assert "domain_weights" in goal, f"{goal_id} missing domain_weights"
        for domain in DOMAINS:
            assert domain in goal["domain_weights"], f"{goal_id} missing weight for {domain}"


def test_career_goal_weights_between_0_and_1():
    for goal_id, goal in CAREER_GOALS.items():
        for domain, weight in goal["domain_weights"].items():
            assert 0 <= weight <= 1, f"{goal_id}.{domain} weight {weight} out of range"


# ─── Recommendation Engine ──────────────────────────────────────────────────


def test_recommendations_no_skills_returns_beginners():
    recs = get_recommendations([], "backend-engineer")
    assert len(recs) > 0
    # All returned skills should have no prerequisites (beginners)
    for rec in recs:
        assert rec["prerequisites"] == [], (
            f"Recommended {rec['id']} but its prereqs {rec['prerequisites']} are not met"
        )


def test_recommendations_excludes_acquired_skills():
    recs = get_recommendations(["python-fundamentals"], "backend-engineer")
    rec_ids = [r["id"] for r in recs]
    assert "python-fundamentals" not in rec_ids


def test_recommendations_unlocks_dependents():
    recs = get_recommendations(["python-fundamentals"], "backend-engineer")
    rec_ids = [r["id"] for r in recs]
    # Having python-fundamentals should unlock rest-api-design and database-management
    assert "rest-api-design" in rec_ids
    assert "database-management" in rec_ids


def test_recommendations_respects_prerequisites():
    # Without python-fundamentals, can't recommend rest-api-design
    recs = get_recommendations([], "backend-engineer")
    rec_ids = [r["id"] for r in recs]
    assert "rest-api-design" not in rec_ids


def test_recommendations_career_goal_weighting():
    # Backend engineer should rank backend skills higher
    backend_recs = get_recommendations([], "backend-engineer")
    frontend_recs = get_recommendations([], "frontend-engineer")

    backend_ids = [r["id"] for r in backend_recs[:3]]
    frontend_ids = [r["id"] for r in frontend_recs[:3]]

    # python-fundamentals should rank higher for backend
    assert "python-fundamentals" in backend_ids
    # html-css or javascript-fundamentals should rank higher for frontend
    assert any(s in frontend_ids for s in ["html-css", "javascript-fundamentals"])


def test_recommendations_no_career_goal():
    recs = get_recommendations([], "")
    # Should still return recommendations with default weights
    assert len(recs) > 0


def test_recommendations_limit():
    recs = get_recommendations([], "backend-engineer", limit=3)
    assert len(recs) <= 3


def test_recommendations_all_skills_acquired():
    all_ids = list(SKILLS.keys())
    recs = get_recommendations(all_ids, "backend-engineer")
    assert recs == []


def test_recommendations_scores_are_positive():
    recs = get_recommendations([], "backend-engineer")
    for rec in recs:
        assert rec["score"] > 0


def test_recommendations_sorted_by_score():
    recs = get_recommendations(["python-fundamentals"], "backend-engineer")
    for i in range(len(recs) - 1):
        assert recs[i]["score"] >= recs[i + 1]["score"]


def test_advanced_not_recommended_without_intermediate():
    # microservices requires rest-api-design + database-management
    recs = get_recommendations(["python-fundamentals"], "backend-engineer")
    rec_ids = [r["id"] for r in recs]
    assert "microservices" not in rec_ids


def test_advanced_recommended_with_all_prereqs():
    prereqs = ["python-fundamentals", "rest-api-design", "database-management"]
    recs = get_recommendations(prereqs, "backend-engineer")
    rec_ids = [r["id"] for r in recs]
    assert "microservices" in rec_ids


# ─── API Endpoints ──────────────────────────────────────────────────────────


def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"SkillGrowthNavigator" in resp.data


def test_api_skills(client):
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 30


def test_api_goals(client):
    resp = client.get("/api/goals")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "backend-engineer" in data


def test_api_graph(client):
    resp = client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 30
    assert len(data["edges"]) > 0


def test_api_recommend_empty(client):
    resp = client.post(
        "/api/recommend",
        data=json.dumps({"skills": [], "career_goal": "backend-engineer"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_api_recommend_with_skills(client):
    resp = client.post(
        "/api/recommend",
        data=json.dumps({"skills": ["python-fundamentals"], "career_goal": "backend-engineer"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    rec_ids = [r["id"] for r in data]
    assert "python-fundamentals" not in rec_ids
    assert "rest-api-design" in rec_ids


# ─── Profile API ────────────────────────────────────────────────────────────


def test_api_profile_save_and_load(client):
    # Save
    resp = client.post(
        "/api/profile",
        data=json.dumps({
            "username": "testuser",
            "career_goal": "backend-engineer",
            "skills": ["python-fundamentals", "rest-api-design"],
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "saved"

    # Load
    resp = client.get("/api/profile?username=testuser")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["username"] == "testuser"
    assert data["career_goal"] == "backend-engineer"
    assert set(data["skills"]) == {"python-fundamentals", "rest-api-design"}


def test_api_profile_update(client):
    # Save initial
    client.post(
        "/api/profile",
        data=json.dumps({
            "username": "updater",
            "career_goal": "frontend-engineer",
            "skills": ["html-css"],
        }),
        content_type="application/json",
    )
    # Update
    client.post(
        "/api/profile",
        data=json.dumps({
            "username": "updater",
            "career_goal": "fullstack-developer",
            "skills": ["html-css", "javascript-fundamentals"],
        }),
        content_type="application/json",
    )
    # Verify update
    resp = client.get("/api/profile?username=updater")
    data = resp.get_json()
    assert data["career_goal"] == "fullstack-developer"
    assert set(data["skills"]) == {"html-css", "javascript-fundamentals"}


def test_api_profile_nonexistent_user(client):
    resp = client.get("/api/profile?username=nobody")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["skills"] == []


def test_api_profile_no_username(client):
    resp = client.get("/api/profile")
    assert resp.status_code == 400


def test_api_profile_ignores_invalid_skills(client):
    client.post(
        "/api/profile",
        data=json.dumps({
            "username": "validator",
            "career_goal": "",
            "skills": ["python-fundamentals", "fake-skill-xyz"],
        }),
        content_type="application/json",
    )
    resp = client.get("/api/profile?username=validator")
    data = resp.get_json()
    assert "fake-skill-xyz" not in data["skills"]
    assert "python-fundamentals" in data["skills"]
