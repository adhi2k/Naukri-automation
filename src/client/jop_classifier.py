import json
import os
import re
import requests


class JobFilterPipeline2:

    # =========================================================
    # CANDIDATE PROFILE — BASED ON RESUME
    # =========================================================

    CANDIDATE = {
        "education": "B.Tech Artificial Intelligence and Data Science",
        "current_status": "Student / Entry-level Software Developer",
        "experience": [
            "Software Development Intern",
            "Software Documentation Intern",
            "Freelance Web Developer / Designer",
            "Technical Content Creator",
        ],

        "primary_skills": [
            "python",
            "java",
            "javascript",
            "sql",
            "postgresql",
            "fastapi",
            "rest api",
            "rest apis",
            "web development",
            "git",
            "github",
            "workflow automation",
        ],

        "secondary_skills": [
            "gcp",
            "google cloud",
            "flutter",
            "html",
            "css",
            "ui/ux",
            "machine learning",
            "deep learning",
            "artificial intelligence",
            "rag",
            "retrieval augmented generation",
            "vector database",
            "postgis",
            "database management",
            "problem solving",
            "data structures",
            "object oriented programming",
            "blockchain",
            "qr codes",
        ],

        "project_skills": [
            "fastapi",
            "postgresql",
            "postgis",
            "vector database",
            "rag",
            "rest api",
            "flutter",
            "ai",
            "machine learning",
            "automation",
            "web development",
            "javascript",
        ],
    }

    # =========================================================
    # PREFERRED LOCATIONS
    # =========================================================

    PREFERRED_LOCATIONS = {
        "chennai",
        "tamil nadu",
        "tamilnadu",
        "bengaluru",
        "bangalore",
        "bengaluru urban",
    }

    # Remote can be enabled if you want remote jobs too.
    ALLOW_REMOTE = True

    # =========================================================
    # TARGET JOB TITLES
    # =========================================================

    TARGET_TITLE_KEYWORDS = {
        "software developer",
        "software engineer",
        "software development engineer",
        "sde",
        "sde 1",
        "sde-1",
        "associate software engineer",
        "graduate software engineer",
        "trainee software engineer",

        "python developer",
        "python engineer",

        "java developer",
        "java engineer",
        "java software engineer",

        "backend developer",
        "backend engineer",
        "back end developer",
        "back-end developer",

        "full stack developer",
        "fullstack developer",
        "full stack engineer",
        "fullstack engineer",

        "web developer",
        "web engineer",

        "application developer",
        "application engineer",

        "automation developer",
        "automation engineer",

        "ai developer",
        "ai engineer",
        "ai software engineer",

        "ml engineer",
        "machine learning engineer",

        "data analyst",
        "junior data analyst",
        "data engineer",
        "junior data engineer",
    }

    # =========================================================
    # HARD VETO TITLES
    # =========================================================

    VETO_TITLES = {
        "walk-in",
        "walkin",
        "walk in",

        "principal engineer",
        "staff engineer",
        "architect",
        "solution architect",
        "technical architect",

        "vp of",
        "vice president",
        "head of engineering",
        "head of technology",
        "director of engineering",

        "founder",
        "co-founder",

        "engineering manager",
        "engineering management",
        "project manager",
        "product manager",
        "program manager",

        "tutor",
        "trainer",
        "faculty",
        "teacher",

        "internship - unpaid",
        "unpaid internship",

        "senior software engineer",
        "senior software developer",
        "lead software engineer",
        "technical lead",
        "tech lead",
    }

    # =========================================================
    # ROLE VETOES
    # =========================================================

    ROLE_VETO_KEYWORDS = {
        "android developer",
        "android engineer",

        "ios developer",
        "ios engineer",

        "flutter developer",
        "flutter engineer",

        "mobile developer",
        "mobile application developer",

        "embedded engineer",
        "embedded developer",
        "firmware engineer",

        "front end only",
        "frontend only",
        "ui developer",
        "ui engineer",

        "react native developer",
        "react native engineer",

        "devops engineer",
        "site reliability engineer",
        "sre engineer",
        "cloud operations engineer",

        "network engineer",
        "network administrator",

        "security analyst",
        "cyber security analyst",

        "manual tester",
        "manual testing",

        "qa tester",
        "test engineer",
    }

    # =========================================================
    # COMPANY VETO
    # =========================================================

    VETO_COMPANIES = {
        "accenture",
        "wipro",
        "infosys",
        "tcs",
        "cognizant",
        "capgemini",
        "hcl",
        "tech mahindra",
        "mphasis",
        "hexaware",
        "ltimindtree",
        "persistent",
        "birlasoft",
    }

    # =========================================================
    # RED FLAGS
    # =========================================================

    DESC_RED_FLAGS = {
        "walk-in": r"\bwalk.?in\b|\bwalkin\b",
        "interview venue": r"interview\s+venue",
        "bring resume": r"bring\s+(your\s+)?resume",
        "carry resume": r"carry\s+(your\s+)?resume",
    }

    # =========================================================
    # SOFTWARE / TECHNICAL TITLES
    # =========================================================

    SOFTWARE_KEYWORDS = {
        "software",
        "developer",
        "engineer",
        "engineering",
        "backend",
        "back-end",
        "full stack",
        "fullstack",
        "python",
        "java",
        "javascript",
        "typescript",
        "web",
        "application",
        "api",
        "ai",
        "machine learning",
        "data analyst",
        "data engineer",
        "automation",
        "programmer",
        "sde",
    }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        openai_api_key=None,
        cache_file="score_cache.json",
        daily_apply_limit=50,
        min_apply_score=60,
        ai_score_limit=100,
        batch_size=3,
        ollama_url=None,
        ollama_model=None,
    ):

        self.ollama_url = (
            ollama_url
            or os.getenv("OLLAMA_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")

        self.ollama_model = (
            ollama_model
            or os.getenv("OLLAMA_MODEL")
            or "qwen2.5:14b"
        )

        self.url = f"{self.ollama_url}/api/chat"
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

        self.cache_file = cache_file
        self.daily_apply_limit = daily_apply_limit
        self.min_apply_score = min_apply_score
        self.ai_score_limit = ai_score_limit if ai_score_limit is not None else int(os.getenv("AI_SCORE_LIMIT", "15"))
        self.batch_size = batch_size

        self.cache = self._load_cache()

    # =========================================================
    # MAIN PIPELINE
    # =========================================================

    def run(self, jobs):

        print("\nRAW JOBS:", len(jobs))

        jobs = self.normalize_jobs(jobs)
        print("AFTER NORMALIZE:", len(jobs))

        jobs = self.dedup(jobs)
        print("AFTER DEDUP:", len(jobs))

        jobs = self.location_filter(jobs)
        print("AFTER LOCATION FILTER:", len(jobs))

        jobs = self.hard_veto(jobs)
        print("AFTER HARD VETO:", len(jobs))

        jobs = self.experience_filter(jobs)
        print("AFTER EXPERIENCE FILTER:", len(jobs))

        jobs = self.desc_red_flag_check(jobs)
        print("AFTER RED FLAG CHECK:", len(jobs))

        jobs = self.title_filter(jobs)
        print("AFTER TITLE FILTER:", len(jobs))

        jobs = self.company_veto(jobs)
        print("AFTER COMPANY VETO:", len(jobs))

        jobs = self.tag_presort(jobs)

        jobs = jobs[:self.ai_score_limit]

        print("AFTER AI LIMIT:", len(jobs))

        jobs = self.ai_score_batch(jobs)

        jobs = self.rank(jobs)

        print("AFTER RANK:", len(jobs))

        jobs = self.select(jobs)

        print("FINAL SELECTED:", len(jobs))

        for job in jobs:
            print(
                f"  {job.get('ai_score'):>3} "
                f"{job.get('title')} @ {job.get('company')} "
                f"| {job.get('location')} "
                f"| {job.get('ai_reason', '')}"
            )

        return jobs

    # =========================================================
    # NORMALIZE
    # =========================================================

    def normalize_jobs(self, jobs):

        normalized = []

        for j in jobs:

            job = j if isinstance(j, dict) else j.__dict__

            posted = (job.get("posted_date") or "").lower()

            days_old = 7

            if (
                "today" in posted
                or "hour" in posted
                or "just now" in posted
            ):
                days_old = 0

            elif "yesterday" in posted:
                days_old = 1

            else:

                m = re.search(r"(\d+)\s*day", posted)

                if m:
                    days_old = int(m.group(1))

                else:

                    m = re.search(r"(\d+)\s*week", posted)

                    if m:
                        days_old = int(m.group(1)) * 7

            # Experience

            exp = job.get("experience") or ""

            exp_min = 0
            exp_max = 5

            nums = re.findall(r"\d+", str(exp))

            if len(nums) >= 2:

                exp_min = int(nums[0])
                exp_max = int(nums[1])

            elif len(nums) == 1:

                exp_min = int(nums[0])
                exp_max = int(nums[0])

            # Tags

            raw_tags = (
                job.get("tags")
                or job.get("skills")
                or []
            )

            if isinstance(raw_tags, str):

                raw_tags = re.split(
                    r"[,;|]",
                    raw_tags
                )

            tags = [
                t.strip().lower()
                for t in raw_tags
                if t.strip()
            ]

            normalized.append({

                "job_id":
                    job.get("job_id"),

                "title":
                    (job.get("title") or "").strip(),

                "company":
                    (job.get("company") or "").strip(),

                "location":
                    (job.get("location") or "").strip(),

                "description":
                    (job.get("description") or "").strip(),

                "tags":
                    tags,

                "mandatory_tags":
                    tags[:2],

                "optional_tags":
                    tags[2:],

                "days_old":
                    days_old,

                "experience_min":
                    exp_min,

                "experience_max":
                    exp_max,
            })

        return normalized

    # =========================================================
    # DEDUP
    # =========================================================

    def dedup(self, jobs):

        seen = set()
        result = []

        for job in jobs:

            job_id = job.get("job_id")

            if job_id is None:
                result.append(job)
                continue

            if job_id in seen:
                continue

            seen.add(job_id)
            result.append(job)

        return result

    # =========================================================
    # LOCATION FILTER
    # =========================================================

    def location_filter(self, jobs):

        result = []

        for job in jobs:

            location = (
                job.get("location") or ""
            ).lower()

            title = (
                job.get("title") or ""
            ).lower()

            description = (
                job.get("description") or ""
            ).lower()

            location_text = (
                location
                + " "
                + title
                + " "
                + description
            )

            location_match = any(
                loc in location_text
                for loc in self.PREFERRED_LOCATIONS
            )

            remote_match = (
                self.ALLOW_REMOTE
                and any(term in location_text for term in ["remote", "work from home", "wfh", "anywhere in india", "pan india", "hybrid"])
            )

            if location_match or remote_match:

                result.append(job)

            else:

                print(
                    f"  [LOCATION SKIP] "
                    f"{job.get('title')} "
                    f"@ {job.get('location')}"
                )

        return result

    # =========================================================
    # HARD VETO
    # =========================================================

    def hard_veto(self, jobs):

        clean = []

        for job in jobs:

            title = (
                job.get("title") or ""
            ).lower()

            if any(
                keyword in title
                for keyword in self.VETO_TITLES
            ):

                print(
                    f"  [VETO] "
                    f"{job.get('title')}"
                )

                continue

            clean.append(job)

        return clean

    # =========================================================
    # EXPERIENCE
    # =========================================================

    def experience_filter(self, jobs):

        result = []

        for job in jobs:

            min_exp = job.get(
                "experience_min",
                0
            )

            max_exp = job.get(
                "experience_max",
                10
            )

            # Entry-level / fresher / 0-3 years

            if min_exp <= 2 and max_exp <= 4:

                result.append(job)

            elif min_exp == 0:

                result.append(job)

            else:

                print(
                    f"  [EXP SKIP] "
                    f"{job.get('title')} "
                    f"{min_exp}-{max_exp} yrs"
                )

        return result

    # =========================================================
    # DESCRIPTION RED FLAGS
    # =========================================================

    def desc_red_flag_check(self, jobs):

        clean = []

        for job in jobs:

            description = (
                job.get("description") or ""
            ).lower()

            flagged = [
                label
                for label, pattern
                in self.DESC_RED_FLAGS.items()
                if re.search(
                    pattern,
                    description
                )
            ]

            if flagged:

                print(
                    f"  [RED FLAG {flagged}] "
                    f"{job.get('title')}"
                )

                continue

            clean.append(job)

        return clean

    # =========================================================
    # TITLE FILTER
    # =========================================================

    def title_filter(self, jobs):

        result = []

        for job in jobs:

            title = (
                job.get("title") or ""
            ).lower()

            # Reject clearly unwanted roles

            if any(
                keyword in title
                for keyword in self.ROLE_VETO_KEYWORDS
            ):

                print(
                    f"  [ROLE VETO] "
                    f"{job.get('title')}"
                )

                continue

            # Must look like a technical/software role

            if not any(
                keyword in title
                for keyword in self.SOFTWARE_KEYWORDS
            ):

                print(
                    f"  [NOT SOFTWARE] "
                    f"{job.get('title')}"
                )

                continue

            result.append(job)

        return result

    # =========================================================
    # COMPANY FILTER
    # =========================================================

    def company_veto(self, jobs):

        clean = []

        for job in jobs:

            company = (
                job.get("company") or ""
            ).lower()

            if any(
                company_name in company
                for company_name
                in self.VETO_COMPANIES
            ):

                print(
                    f"  [COMPANY VETO] "
                    f"{job.get('title')} "
                    f"@ {job.get('company')}"
                )

                continue

            clean.append(job)

        return clean

    # =========================================================
    # TAG PRESORT
    # =========================================================

    def tag_presort(self, jobs):

        primary = set(
            self.CANDIDATE["primary_skills"]
        )

        secondary = set(
            self.CANDIDATE["secondary_skills"]
        )

        project = set(
            self.CANDIDATE["project_skills"]
        )

        def score(job):

            tags = set(
                job.get("tags", [])
            )

            primary_hits = len(
                tags & primary
            )

            secondary_hits = len(
                tags & secondary
            )

            project_hits = len(
                tags & project
            )

            recency_bonus = max(
                0,
                7 - job.get("days_old", 7)
            )

            return (
                primary_hits * 5
                + secondary_hits * 2
                + project_hits * 2
                + recency_bonus
            )

        return sorted(
            jobs,
            key=score,
            reverse=True
        )

    # =========================================================
    # AI SCORING
    # =========================================================

    def ai_score_batch(self, jobs):

        result = []

        total_batches = (
            (len(jobs) + self.batch_size - 1)
            // self.batch_size
            if jobs
            else 0
        )

        for batch_index, start in enumerate(
            range(
                0,
                len(jobs),
                self.batch_size
            ),
            1
        ):

            batch = jobs[
                start:start + self.batch_size
            ]

            uncached = [
                job
                for job in batch
                if str(
                    job.get("job_id") or ""
                ) not in self.cache
            ]

            if uncached:

                provider_name = f"Groq ({self.groq_model})" if self.groq_api_key else f"Ollama ({self.ollama_model})"
                print(
                    f"  [AI] "
                    f"Batch {batch_index}/"
                    f"{total_batches}: "
                    f"{len(uncached)} jobs -> "
                    f"{provider_name}"
                )

                scores = self._call_ai(
                    uncached
                )

                for index, job in enumerate(
                    uncached
                ):

                    job_id = str(
                        job.get("job_id") or ""
                    )

                    data = scores.get(
                        str(index),
                        {
                            "score": 0,
                            "reason": "No AI response"
                        }
                    )

                    try:

                        data["score"] = int(
                            data.get("score", 0)
                        )

                    except (ValueError, TypeError, Exception):

                        data["score"] = 0

                    data["score"] = max(
                        0,
                        min(
                            100,
                            data["score"]
                        )
                    )

                    if job_id:

                        self.cache[
                            job_id
                        ] = data

                # Save cache immediately after each batch so progress is never lost
                self._save_cache()

            else:

                print(
                    f"  [AI] Batch "
                    f"{batch_index}/"
                    f"{total_batches}: "
                    f"loaded from cache"
                )

            for job in batch:

                job_id = str(
                    job.get("job_id") or ""
                )

                data = self.cache.get(
                    job_id,
                    {
                        "score": 0,
                        "reason": "Not scored"
                    }
                )

                score_val = data.get("score", 0)
                reason_val = data.get("reason", "")

                job["ai_score"] = score_val
                job["score"] = score_val
                job["ai_reason"] = reason_val
                job["ai_detail"] = reason_val

                result.append(job)

        self._save_cache()

        return result

    # =========================================================
    # OLLAMA
    # =========================================================

    def _call_ai(self, jobs):

        job_block = ""

        for index, job in enumerate(jobs):

            tags = ", ".join(
                job.get("tags", [])
            ) or "none"

            # Use first 750 characters of description for fast evaluation
            desc = (job.get('description') or '').strip()[:750]

            job_block += (
                f"\nJOB {index}\n"
                f"Title: {job.get('title')}\n"
                f"Company: {job.get('company')}\n"
                f"Location: {job.get('location')}\n"
                f"Experience: "
                f"{job.get('experience_min', 0)}-"
                f"{job.get('experience_max', 4)} years\n"
                f"Skills: {tags}\n"
                f"Description: "
                f"{desc}\n"
            )

        prompt = f"""
You are a strict recruitment matching system.

Evaluate the jobs against the candidate profile.

CANDIDATE:

Education:
B.Tech Artificial Intelligence and Data Science.

Career stage:
Student / entry-level software developer.

Experience:
- Software Development Intern
- Software Documentation Intern
- Freelance Web Developer / Designer
- Technical Content Creator

Primary skills:
Python, Java, JavaScript, SQL, PostgreSQL,
FastAPI, REST APIs, Git, GitHub,
web development, workflow automation.

Additional skills/projects:
GCP, Flutter, HTML, CSS, UI/UX,
Artificial Intelligence, Machine Learning,
Deep Learning, RAG, vector databases,
PostGIS, automation, database management.

Target locations:
Chennai, Tamil Nadu, Bengaluru/Bangalore,
or remote.

TARGET ROLES:
Software Developer
Software Engineer
SDE / SDE-1
Associate Software Engineer
Graduate Software Engineer
Trainee Software Engineer
Python Developer
Java Developer
Backend Developer
Full Stack Developer
Web Developer
Application Developer
Automation Developer
AI Developer
AI Engineer
ML Engineer
Junior Data Engineer
Data Analyst

SCORING:

90-100:
Excellent match.
Entry-level/junior role with strong overlap
with Python/Java/JavaScript/SQL/PostgreSQL/FastAPI/
REST/web/AI/automation.

75-89:
Strong match.
Good software-development role with several
candidate skills and reasonable experience requirements.

60-74:
Good potential.
Some relevant skills but noticeable gaps.

40-59:
Weak match.
Some relevant technology but substantial mismatch.

20-39:
Poor match.
Mostly unrelated requirements.

0-19:
Do not apply.
Clearly incompatible role, senior role, unrelated
technology stack, or prohibited role.

IMPORTANT:

- Do NOT assume the candidate has 2+ years professional experience.
- Internship + freelance experience is entry-level experience.
- Do NOT require Node.js.
- Do NOT require MongoDB.
- Do NOT require AWS.
- Java is a valid candidate skill.
- Python is a strong candidate skill.
- PostgreSQL and SQL are strong candidate skills.
- FastAPI is a strong candidate skill.
- AI/RAG/vector DB roles can be relevant.
- Web development roles can be relevant.
- Full-stack roles can be relevant if backend/API work exists.
- Pure frontend roles should score lower.
- Mobile-only roles should score low.
- Senior/lead/architect/manager roles should score very low.
- DevOps-only roles should score low.
- Location matters.
- Chennai and Bengaluru/Bangalore are preferred.
- Remote is acceptable.
- Tamil Nadu locations should receive a positive location signal.

Return ONLY JSON.

Format:

{{
  "0": {{
    "score": 87,
    "reason": "Python + FastAPI + REST backend role; entry-level experience fits"
  }},
  "1": {{
    "score": 42,
    "reason": "Some Java overlap but role requires senior experience"
  }}
}}

JOBS:
{job_block}
"""

        # Method 1: High-Speed Free Cloud AI (Groq LPU)
        if self.groq_api_key:
            try:
                groq_resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.groq_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1
                    },
                    timeout=30
                )
                if groq_resp.status_code == 200:
                    payload = groq_resp.json()
                    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        clean_content = re.sub(r"```json|```", "", content).strip()
                        return json.loads(clean_content)
                else:
                    print(f"  [GROQ WARNING] HTTP {groq_resp.status_code}: {groq_resp.text[:120]}. Falling back to Ollama...")
            except Exception as e:
                print(f"  [GROQ WARNING] {e}. Falling back to Ollama...")

        # Method 2: Local Ollama Fallback
        try:

            response = requests.post(
                self.url,
                headers={
                    "Content-Type":
                    "application/json"
                },
                json={
                    "model":
                    self.ollama_model,

                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    "stream": False,

                    "format": "json",

                    "options": {
                        "temperature": 0.1
                    }
                },

                # 14B can be slow on your laptop.
                timeout=600
            )

            if response.status_code != 200:

                print(
                    "OLLAMA HTTP ERROR:",
                    response.status_code,
                    response.text[:500]
                )

                return {}

            payload = response.json()

            content = (
                payload
                .get("message", {})
                .get("content", "")
            )

            if not content:

                print(
                    "OLLAMA ERROR: "
                    "empty response"
                )

                return {}

            content = re.sub(
                r"```json|```",
                "",
                content
            ).strip()

            try:

                data = json.loads(content)

            except json.JSONDecodeError:

                match = re.search(
                    r"\{.*\}",
                    content,
                    re.S
                )

                if not match:

                    print(
                        "OLLAMA JSON PARSE ERROR:",
                        content[:500]
                    )

                    return {}

                data = json.loads(
                    match.group(0)
                )

            return (
                data
                if isinstance(data, dict)
                else {}
            )

        except requests.exceptions.ConnectionError:

            print(
                "OLLAMA CONNECTION ERROR."
            )

            return {}

        except requests.exceptions.Timeout:

            print(
                f"OLLAMA TIMEOUT: "
                f"{self.ollama_model}"
            )

            return {}

        except Exception as error:

            print(
                "OLLAMA ERROR:",
                error
            )

            return {}

    # =========================================================
    # RANK
    # =========================================================

    def rank(self, jobs):

        return sorted(
            jobs,
            key=lambda job:
                job.get("ai_score", 0)
                + max(
                    0,
                    3 - job.get(
                        "days_old",
                        7
                    )
                ),
            reverse=True
        )

    # =========================================================
    # SELECT
    # =========================================================

    def select(self, jobs):

        apply_list = [
            job
            for job in jobs
            if job.get(
                "ai_score",
                0
            ) >= self.min_apply_score
        ]

        review_list = [
            job
            for job in jobs
            if 40 <= job.get(
                "ai_score",
                0
            ) < self.min_apply_score
        ]

        if review_list:

            print(
                f"\n--- REVIEW "
                f"MANUALLY "
                f"({len(review_list)}) ---"
            )

            for job in review_list:

                print(
                    f"score={job.get('ai_score')} "
                    f"{job.get('title')} "
                    f"@ {job.get('company')} "
                    f"| {job.get('location')} "
                    f"| {job.get('ai_reason', '')}"
                )

        return apply_list[
            :self.daily_apply_limit
        ]

    # =========================================================
    # CACHE
    # =========================================================

    def _load_cache(self):

        if os.path.exists(
            self.cache_file
        ):

            try:

                with open(
                    self.cache_file,
                    "r",
                    encoding="utf-8"
                ) as file:

                    return json.load(file)

            except Exception:

                return {}

        return {}

    def _save_cache(self):

        with open(
            self.cache_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.cache,
                file,
                indent=2,
                ensure_ascii=False
            )