"""
CodeLens — Quick Demo (no Docker, no database needed)
Run: python demo.py
"""

import os, json, textwrap

# ── Load API key from .env ──────────────────────────────────────────────────
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("❌  GEMINI_API_KEY not found in .env")
    raise SystemExit(1)

# ── Sample buggy code snippets ──────────────────────────────────────────────
SAMPLES = {
    "1": {
        "label": "Buggy Python (SQL injection + bare except)",
        "language": "python",
        "code": textwrap.dedent("""\
            import sqlite3

            def get_user(username):
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                query = "SELECT * FROM users WHERE username = '" + username + "'"
                cursor.execute(query)
                return cursor.fetchone()

            def divide(a, b):
                try:
                    return a / b
                except:
                    pass

            password = "hunter2"
            print(password)
        """),
    },
    "2": {
        "label": "SQL injection in PHP",
        "language": "php",
        "code": textwrap.dedent("""\
            <?php
            $id = $_GET['id'];
            $result = mysqli_query($conn, "SELECT * FROM products WHERE id = $id");
            $password = md5($_POST['password']);
            echo $result;
            ?>
        """),
    },
    "3": {
        "label": "Memory issues in C++",
        "language": "cpp",
        "code": textwrap.dedent("""\
            #include <iostream>
            void leak() {
                int* p = new int[100];
                // forgot delete[] p;
            }
            int main() {
                int arr[5];
                arr[10] = 42;   // buffer overflow
                leak();
                return 0;
            }
        """),
    },
}

# ── Gemini review function ───────────────────────────────────────────────────
def review_code(code: str, language: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are a senior security engineer. Review the following {language} code and return a JSON object with this exact structure:
{{
  "score": <integer 0-100, higher = safer>,
  "summary": "<one sentence overview>",
  "findings": [
    {{
      "severity": "<critical|high|medium|low|info>",
      "category": "<security|quality|performance|style>",
      "title": "<short title>",
      "line": <line number or null>,
      "description": "<what is wrong>",
      "fix": "<how to fix it>"
    }}
  ]
}}

CODE TO REVIEW:
```{language}
{code}
```

Return ONLY valid JSON, no markdown fences."""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )
    raw = response.text.strip()
    # strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Pretty printer ───────────────────────────────────────────────────────────
SEV_ICONS = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH    ",
    "medium":   "🟡 MEDIUM  ",
    "low":      "🔵 LOW     ",
    "info":     "⚪ INFO    ",
}

def print_results(result: dict):
    score = result.get("score", "?")
    bar = "█" * (score // 5) + "░" * (20 - score // 5)
    print(f"\n{'─'*60}")
    print(f"  Security Score: {score}/100  [{bar}]")
    print(f"  {result.get('summary', '')}")
    print(f"{'─'*60}")

    findings = result.get("findings", [])
    if not findings:
        print("  ✅  No issues found!")
    else:
        print(f"  Found {len(findings)} issue(s):\n")
        for i, f in enumerate(findings, 1):
            icon = SEV_ICONS.get(f.get("severity", "info"), "⚪")
            line = f"line {f['line']}" if f.get("line") else "general"
            print(f"  [{i}] {icon}  {f.get('title','')}  ({line})")
            print(f"       Category : {f.get('category','')}")
            print(f"       Problem  : {f.get('description','')}")
            print(f"       Fix      : {f.get('fix','')}")
            print()


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════╗")
    print("║        CodeLens  — Demo Runner         ║")
    print("╚══════════════════════════════════════════╝")
    print("\nPick a sample to review:")
    for k, v in SAMPLES.items():
        print(f"  [{k}] {v['label']}")
    print("  [4] Paste your own code")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice in SAMPLES:
        sample = SAMPLES[choice]
        code, language = sample["code"], sample["language"]
        print(f"\n📄 Reviewing: {sample['label']}\n")
    elif choice == "4":
        language = input("Language (python/javascript/php/etc): ").strip()
        print("Paste your code (type END on a new line when done):")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        code = "\n".join(lines)
    else:
        print("Invalid choice.")
        return

    print("⏳ Sending to Gemini for analysis...\n")
    try:
        result = review_code(code, language)
        print_results(result)
    except json.JSONDecodeError as e:
        print(f"❌  Could not parse Gemini response: {e}")
    except Exception as e:
        print(f"❌  Error: {e}")

if __name__ == "__main__":
    main()
