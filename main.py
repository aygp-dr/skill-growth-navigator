"""SkillGrowthNavigator - Learning path recommendation engine.

An AI-powered platform that helps employees identify skill gaps and suggests
personalized learning paths for career development.
"""
import os
import sqlite3

from flask import Flask, g, jsonify, render_template, request

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAINS = ["backend", "frontend", "devops", "data", "security"]

LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}

# ─── 30 Skills across 5 domains ────────────────────────────────────────────

SKILLS = {
    # ── Backend (6) ──────────────────────────────────────────────────────
    "python-fundamentals": {
        "name": "Python Fundamentals",
        "domain": "backend",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 40,
        "resources": [
            {"title": "Official Python Tutorial", "url": "https://docs.python.org/3/tutorial/"},
            {"title": "Real Python - First Steps", "url": "https://realpython.com/python-first-steps/"},
            {"title": "Learn Python", "url": "https://www.learnpython.org/"},
        ],
    },
    "rest-api-design": {
        "name": "REST API Design",
        "domain": "backend",
        "level": "intermediate",
        "prerequisites": ["python-fundamentals"],
        "estimated_hours": 30,
        "resources": [
            {"title": "RESTful API Tutorial", "url": "https://restfulapi.net/"},
            {"title": "Flask Quickstart", "url": "https://flask.palletsprojects.com/en/stable/quickstart/"},
            {"title": "Red Hat - REST APIs", "url": "https://www.redhat.com/en/topics/api/what-is-a-rest-api"},
        ],
    },
    "database-management": {
        "name": "Database Management",
        "domain": "backend",
        "level": "intermediate",
        "prerequisites": ["python-fundamentals"],
        "estimated_hours": 35,
        "resources": [
            {"title": "SQLite Tutorial", "url": "https://www.sqlitetutorial.net/"},
            {"title": "Python sqlite3 Docs", "url": "https://docs.python.org/3/library/sqlite3.html"},
            {"title": "Use The Index, Luke", "url": "https://use-the-index-luke.com/"},
        ],
    },
    "auth-and-authorization": {
        "name": "Authentication & Authorization",
        "domain": "backend",
        "level": "intermediate",
        "prerequisites": ["rest-api-design"],
        "estimated_hours": 25,
        "resources": [
            {"title": "OWASP Auth Cheatsheet", "url": "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"},
            {"title": "JWT Introduction", "url": "https://jwt.io/introduction"},
            {"title": "Flask-Login Docs", "url": "https://flask-login.readthedocs.io/en/latest/"},
        ],
    },
    "microservices": {
        "name": "Microservices Architecture",
        "domain": "backend",
        "level": "advanced",
        "prerequisites": ["rest-api-design", "database-management"],
        "estimated_hours": 50,
        "resources": [
            {"title": "Microservices.io", "url": "https://microservices.io/"},
            {"title": "The Twelve-Factor App", "url": "https://12factor.net/"},
            {"title": "Martin Fowler - Microservices", "url": "https://martinfowler.com/articles/microservices.html"},
        ],
    },
    "performance-optimization": {
        "name": "Performance Optimization",
        "domain": "backend",
        "level": "advanced",
        "prerequisites": ["microservices"],
        "estimated_hours": 40,
        "resources": [
            {"title": "Python Profilers", "url": "https://docs.python.org/3/library/profile.html"},
            {"title": "High Performance Python", "url": "https://realpython.com/python-performance/"},
            {"title": "web.dev Performance", "url": "https://web.dev/performance/"},
        ],
    },
    # ── Frontend (6) ─────────────────────────────────────────────────────
    "html-css": {
        "name": "HTML & CSS",
        "domain": "frontend",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 30,
        "resources": [
            {"title": "MDN Learn HTML", "url": "https://developer.mozilla.org/en-US/docs/Learn/HTML"},
            {"title": "MDN Learn CSS", "url": "https://developer.mozilla.org/en-US/docs/Learn/CSS"},
            {"title": "web.dev Learn CSS", "url": "https://web.dev/learn/css/"},
        ],
    },
    "javascript-fundamentals": {
        "name": "JavaScript Fundamentals",
        "domain": "frontend",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 45,
        "resources": [
            {"title": "MDN JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Learn/JavaScript"},
            {"title": "JavaScript.info", "url": "https://javascript.info/"},
            {"title": "Eloquent JavaScript", "url": "https://eloquentjavascript.net/"},
        ],
    },
    "responsive-design": {
        "name": "Responsive Design",
        "domain": "frontend",
        "level": "intermediate",
        "prerequisites": ["html-css"],
        "estimated_hours": 20,
        "resources": [
            {"title": "MDN Responsive Design", "url": "https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design"},
            {"title": "web.dev Responsive Design", "url": "https://web.dev/responsive-web-design-basics/"},
            {"title": "CSS-Tricks Flexbox Guide", "url": "https://css-tricks.com/snippets/css/a-guide-to-flexbox/"},
        ],
    },
    "react-fundamentals": {
        "name": "React Fundamentals",
        "domain": "frontend",
        "level": "intermediate",
        "prerequisites": ["javascript-fundamentals", "html-css"],
        "estimated_hours": 40,
        "resources": [
            {"title": "React Quick Start", "url": "https://react.dev/learn"},
            {"title": "React Tutorial", "url": "https://react.dev/learn/tutorial-tic-tac-toe"},
            {"title": "React Thinking in React", "url": "https://react.dev/learn/thinking-in-react"},
        ],
    },
    "state-management": {
        "name": "State Management",
        "domain": "frontend",
        "level": "advanced",
        "prerequisites": ["react-fundamentals"],
        "estimated_hours": 30,
        "resources": [
            {"title": "React Managing State", "url": "https://react.dev/learn/managing-state"},
            {"title": "Redux Getting Started", "url": "https://redux.js.org/introduction/getting-started"},
            {"title": "Zustand GitHub", "url": "https://github.com/pmndrs/zustand"},
        ],
    },
    "web-accessibility": {
        "name": "Web Accessibility",
        "domain": "frontend",
        "level": "intermediate",
        "prerequisites": ["html-css", "javascript-fundamentals"],
        "estimated_hours": 25,
        "resources": [
            {"title": "MDN Accessibility", "url": "https://developer.mozilla.org/en-US/docs/Web/Accessibility"},
            {"title": "web.dev Accessibility", "url": "https://web.dev/accessibility/"},
            {"title": "W3C WAI Introduction", "url": "https://www.w3.org/WAI/fundamentals/accessibility-intro/"},
        ],
    },
    # ── DevOps (6) ───────────────────────────────────────────────────────
    "linux-fundamentals": {
        "name": "Linux Fundamentals",
        "domain": "devops",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 35,
        "resources": [
            {"title": "Linux Journey", "url": "https://linuxjourney.com/"},
            {"title": "Linux Command Line Basics", "url": "https://ubuntu.com/tutorials/command-line-for-beginners"},
            {"title": "The Linux Documentation Project", "url": "https://tldp.org/LDP/intro-linux/html/"},
        ],
    },
    "git-version-control": {
        "name": "Git & Version Control",
        "domain": "devops",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 15,
        "resources": [
            {"title": "Pro Git Book", "url": "https://git-scm.com/book/en/v2"},
            {"title": "Learn Git Branching", "url": "https://learngitbranching.js.org/"},
            {"title": "Atlassian Git Tutorials", "url": "https://www.atlassian.com/git/tutorials"},
        ],
    },
    "docker-containers": {
        "name": "Docker & Containers",
        "domain": "devops",
        "level": "intermediate",
        "prerequisites": ["linux-fundamentals"],
        "estimated_hours": 30,
        "resources": [
            {"title": "Docker Getting Started", "url": "https://docs.docker.com/get-started/"},
            {"title": "Docker Curriculum", "url": "https://docker-curriculum.com/"},
            {"title": "Dockerfile Best Practices", "url": "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/"},
        ],
    },
    "ci-cd-pipelines": {
        "name": "CI/CD Pipelines",
        "domain": "devops",
        "level": "intermediate",
        "prerequisites": ["git-version-control", "docker-containers"],
        "estimated_hours": 25,
        "resources": [
            {"title": "GitHub Actions Docs", "url": "https://docs.github.com/en/actions"},
            {"title": "CircleCI Documentation", "url": "https://circleci.com/docs/"},
            {"title": "GitLab CI/CD", "url": "https://docs.gitlab.com/ee/ci/"},
        ],
    },
    "kubernetes": {
        "name": "Kubernetes Orchestration",
        "domain": "devops",
        "level": "advanced",
        "prerequisites": ["docker-containers"],
        "estimated_hours": 50,
        "resources": [
            {"title": "Kubernetes Tutorials", "url": "https://kubernetes.io/docs/tutorials/"},
            {"title": "Kubernetes Concepts", "url": "https://kubernetes.io/docs/concepts/"},
            {"title": "Learnk8s", "url": "https://learnk8s.io/"},
        ],
    },
    "infrastructure-as-code": {
        "name": "Infrastructure as Code",
        "domain": "devops",
        "level": "advanced",
        "prerequisites": ["linux-fundamentals", "ci-cd-pipelines"],
        "estimated_hours": 40,
        "resources": [
            {"title": "Terraform Tutorials", "url": "https://developer.hashicorp.com/terraform/tutorials"},
            {"title": "Ansible Getting Started", "url": "https://docs.ansible.com/ansible/latest/getting_started/"},
            {"title": "Pulumi Getting Started", "url": "https://www.pulumi.com/docs/get-started/"},
        ],
    },
    # ── Data (6) ─────────────────────────────────────────────────────────
    "sql-fundamentals": {
        "name": "SQL Fundamentals",
        "domain": "data",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 25,
        "resources": [
            {"title": "SQLZoo", "url": "https://sqlzoo.net/"},
            {"title": "W3Schools SQL", "url": "https://www.w3schools.com/sql/"},
            {"title": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial/"},
        ],
    },
    "data-analysis-python": {
        "name": "Data Analysis with Python",
        "domain": "data",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 35,
        "resources": [
            {"title": "Pandas Getting Started", "url": "https://pandas.pydata.org/docs/getting_started/"},
            {"title": "Kaggle Learn Pandas", "url": "https://www.kaggle.com/learn/pandas"},
            {"title": "Real Python - Pandas", "url": "https://realpython.com/pandas-python-explore-dataset/"},
        ],
    },
    "data-visualization": {
        "name": "Data Visualization",
        "domain": "data",
        "level": "intermediate",
        "prerequisites": ["data-analysis-python"],
        "estimated_hours": 25,
        "resources": [
            {"title": "Matplotlib Tutorials", "url": "https://matplotlib.org/stable/tutorials/"},
            {"title": "Seaborn Tutorial", "url": "https://seaborn.pydata.org/tutorial.html"},
            {"title": "Plotly Python", "url": "https://plotly.com/python/"},
        ],
    },
    "machine-learning-basics": {
        "name": "Machine Learning Basics",
        "domain": "data",
        "level": "intermediate",
        "prerequisites": ["data-analysis-python", "sql-fundamentals"],
        "estimated_hours": 45,
        "resources": [
            {"title": "Scikit-learn Tutorial", "url": "https://scikit-learn.org/stable/tutorial/"},
            {"title": "Kaggle Intro to ML", "url": "https://www.kaggle.com/learn/intro-to-machine-learning"},
            {"title": "Google ML Crash Course", "url": "https://developers.google.com/machine-learning/crash-course"},
        ],
    },
    "deep-learning": {
        "name": "Deep Learning",
        "domain": "data",
        "level": "advanced",
        "prerequisites": ["machine-learning-basics"],
        "estimated_hours": 60,
        "resources": [
            {"title": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/"},
            {"title": "Keras Getting Started", "url": "https://keras.io/getting_started/"},
            {"title": "fast.ai", "url": "https://www.fast.ai/"},
        ],
    },
    "data-engineering": {
        "name": "Data Engineering",
        "domain": "data",
        "level": "advanced",
        "prerequisites": ["sql-fundamentals", "machine-learning-basics"],
        "estimated_hours": 50,
        "resources": [
            {"title": "Apache Airflow Docs", "url": "https://airflow.apache.org/docs/"},
            {"title": "Spark Quick Start", "url": "https://spark.apache.org/docs/latest/quick-start.html"},
            {"title": "Kafka Quickstart", "url": "https://kafka.apache.org/quickstart"},
        ],
    },
    # ── Security (6) ─────────────────────────────────────────────────────
    "security-fundamentals": {
        "name": "Security Fundamentals",
        "domain": "security",
        "level": "beginner",
        "prerequisites": [],
        "estimated_hours": 20,
        "resources": [
            {"title": "OWASP Top Ten", "url": "https://owasp.org/www-project-top-ten/"},
            {"title": "Cybersecurity Basics - NIST", "url": "https://www.nist.gov/cybersecurity"},
            {"title": "SANS Cyber Aces", "url": "https://www.sans.org/cyberaces/"},
        ],
    },
    "network-security": {
        "name": "Network Security",
        "domain": "security",
        "level": "intermediate",
        "prerequisites": ["security-fundamentals"],
        "estimated_hours": 35,
        "resources": [
            {"title": "Nmap Reference Guide", "url": "https://nmap.org/book/man.html"},
            {"title": "Wireshark User Guide", "url": "https://www.wireshark.org/docs/wsug_html_chunked/"},
            {"title": "CompTIA Security+", "url": "https://www.comptia.org/certifications/security"},
        ],
    },
    "owasp-top-10": {
        "name": "OWASP Top 10 Deep Dive",
        "domain": "security",
        "level": "intermediate",
        "prerequisites": ["security-fundamentals"],
        "estimated_hours": 25,
        "resources": [
            {"title": "OWASP Top Ten Project", "url": "https://owasp.org/www-project-top-ten/"},
            {"title": "OWASP Cheat Sheet Series", "url": "https://cheatsheetseries.owasp.org/"},
            {"title": "PortSwigger Web Security", "url": "https://portswigger.net/web-security"},
        ],
    },
    "penetration-testing": {
        "name": "Penetration Testing",
        "domain": "security",
        "level": "advanced",
        "prerequisites": ["network-security", "owasp-top-10"],
        "estimated_hours": 45,
        "resources": [
            {"title": "TryHackMe", "url": "https://tryhackme.com/"},
            {"title": "Hack The Box", "url": "https://www.hackthebox.com/"},
            {"title": "PortSwigger Web Security Academy", "url": "https://portswigger.net/web-security"},
        ],
    },
    "cryptography": {
        "name": "Cryptography",
        "domain": "security",
        "level": "intermediate",
        "prerequisites": ["security-fundamentals"],
        "estimated_hours": 30,
        "resources": [
            {"title": "Cryptopals Challenges", "url": "https://cryptopals.com/"},
            {"title": "Crypto 101", "url": "https://www.crypto101.io/"},
            {"title": "Khan Academy Cryptography", "url": "https://www.khanacademy.org/computing/computer-science/cryptography"},
        ],
    },
    "incident-response": {
        "name": "Incident Response",
        "domain": "security",
        "level": "advanced",
        "prerequisites": ["network-security", "cryptography"],
        "estimated_hours": 35,
        "resources": [
            {"title": "NIST SP 800-61r2", "url": "https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final"},
            {"title": "SANS Incident Handler's Handbook", "url": "https://www.sans.org/white-papers/33901/"},
            {"title": "DFIR Training", "url": "https://www.dfir.training/"},
        ],
    },
}

# ─── Career Goals ───────────────────────────────────────────────────────────

CAREER_GOALS = {
    "backend-engineer": {
        "name": "Backend Engineer",
        "description": "Build scalable server-side applications and APIs",
        "domain_weights": {
            "backend": 1.0, "data": 0.6, "devops": 0.5,
            "security": 0.4, "frontend": 0.2,
        },
    },
    "frontend-engineer": {
        "name": "Frontend Engineer",
        "description": "Create responsive and accessible web interfaces",
        "domain_weights": {
            "frontend": 1.0, "backend": 0.4, "devops": 0.3,
            "security": 0.3, "data": 0.2,
        },
    },
    "fullstack-developer": {
        "name": "Full Stack Developer",
        "description": "End-to-end web development across all layers",
        "domain_weights": {
            "backend": 0.9, "frontend": 0.9, "devops": 0.5,
            "data": 0.4, "security": 0.4,
        },
    },
    "devops-engineer": {
        "name": "DevOps Engineer",
        "description": "Automate infrastructure, deployments, and operations",
        "domain_weights": {
            "devops": 1.0, "backend": 0.5, "security": 0.5,
            "data": 0.3, "frontend": 0.1,
        },
    },
    "data-scientist": {
        "name": "Data Scientist",
        "description": "Extract insights from data using statistics and ML",
        "domain_weights": {
            "data": 1.0, "backend": 0.5, "devops": 0.3,
            "security": 0.2, "frontend": 0.2,
        },
    },
    "security-engineer": {
        "name": "Security Engineer",
        "description": "Protect systems, identify vulnerabilities, and ensure compliance",
        "domain_weights": {
            "security": 1.0, "backend": 0.5, "devops": 0.5,
            "data": 0.2, "frontend": 0.2,
        },
    },
}

# ─── Database ───────────────────────────────────────────────────────────────


def _db_path():
    return app.config.get("DB_PATH", os.path.join(BASE_DIR, "data", "app.db"))


def get_db():
    if "db" not in g:
        path = _db_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        _init_tables(g.db)
    return g.db


def _init_tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            career_goal TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_skills (
            user_id INTEGER NOT NULL,
            skill_id TEXT NOT NULL,
            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, skill_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)


def init_db():
    """Explicitly initialize the database. Used by tests."""
    db = get_db()
    return db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()


# ─── Recommendation Engine ──────────────────────────────────────────────────


def get_recommendations(user_skill_ids, career_goal, limit=10):
    """Recommend next skills based on satisfied prerequisites and career goal.

    Pure function - no database access required.

    Args:
        user_skill_ids: List of skill IDs the user already has.
        career_goal: Career goal ID (key in CAREER_GOALS).
        limit: Maximum number of recommendations to return.

    Returns:
        List of skill dicts with added 'id' and 'score' fields,
        sorted by score descending.
    """
    user_set = set(user_skill_ids)
    goal_config = CAREER_GOALS.get(career_goal)
    domain_weights = (
        goal_config["domain_weights"]
        if goal_config
        else {d: 0.5 for d in DOMAINS}
    )

    candidates = []
    for skill_id, skill in SKILLS.items():
        if skill_id in user_set:
            continue
        if not all(prereq in user_set for prereq in skill["prerequisites"]):
            continue

        domain_score = domain_weights.get(skill["domain"], 0.1)
        level_score = {"beginner": 1.0, "intermediate": 0.7, "advanced": 0.4}[
            skill["level"]
        ]
        prereq_bonus = len(skill["prerequisites"]) * 0.1
        score = domain_score * level_score + prereq_bonus

        candidates.append({"id": skill_id, "score": round(score, 3), **skill})

    candidates.sort(
        key=lambda x: (-x["score"], LEVEL_ORDER[x["level"]], x["estimated_hours"])
    )
    return candidates[:limit]


# ─── Routes ─────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    return render_template(
        "index.html",
        skills=SKILLS,
        career_goals=CAREER_GOALS,
        domains=DOMAINS,
    )


@app.route("/api/skills")
def api_skills():
    return jsonify(SKILLS)


@app.route("/api/goals")
def api_goals():
    return jsonify(CAREER_GOALS)


@app.route("/api/graph")
def api_graph():
    nodes = []
    edges = []
    for skill_id, skill in SKILLS.items():
        nodes.append({
            "id": skill_id,
            "name": skill["name"],
            "domain": skill["domain"],
            "level": skill["level"],
            "estimated_hours": skill["estimated_hours"],
        })
        for prereq in skill["prerequisites"]:
            edges.append({"source": prereq, "target": skill_id})
    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.get_json(force=True)
    skills = data.get("skills", [])
    goal = data.get("career_goal", "")
    recs = get_recommendations(skills, goal)
    return jsonify(recs)


@app.route("/api/profile", methods=["GET", "POST"])
def api_profile():
    db = get_db()

    if request.method == "POST":
        data = request.get_json(force=True)
        username = data.get("username", "").strip()
        if not username:
            return jsonify({"error": "Username required"}), 400

        career_goal = data.get("career_goal", "")
        skills = data.get("skills", [])

        db.execute(
            "INSERT INTO users (username, career_goal) VALUES (?, ?) "
            "ON CONFLICT(username) DO UPDATE SET career_goal = excluded.career_goal",
            (username, career_goal),
        )
        user = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        user_id = user["id"]

        db.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
        for skill_id in skills:
            if skill_id in SKILLS:
                db.execute(
                    "INSERT INTO user_skills (user_id, skill_id) VALUES (?, ?)",
                    (user_id, skill_id),
                )
        db.commit()
        return jsonify({"status": "saved", "user_id": user_id})

    # GET
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400

    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if not user:
        return jsonify({"username": username, "career_goal": "", "skills": []})

    skills = db.execute(
        "SELECT skill_id FROM user_skills WHERE user_id = ?", (user["id"],)
    ).fetchall()
    return jsonify({
        "username": user["username"],
        "career_goal": user["career_goal"],
        "skills": [s["skill_id"] for s in skills],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
