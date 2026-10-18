"""Optional provider diagnostic. Never runs during import or automated tests."""
import os

def main():
    from groq import Groq
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("Set GROQ_API_KEY before running this diagnostic.")
        return 1
    try:
        with Groq(api_key=key, timeout=15, max_retries=0) as client:
            for model in client.models.list().data:
                print(model.id)
        return 0
    except Exception:
        print("Provider check failed. Check configuration and connectivity.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
