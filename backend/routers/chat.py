"""
Chat router — AI assistant powered by Vertex AI Gemini.
Fetches user's real activity data, builds context, calls Gemini, returns structured response.
"""
import json
import re
import traceback
from datetime import datetime, timedelta
from collections import Counter
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import verify_token, get_user_by_id
from backend.models import ActivityLog
from backend.services.aggregator import Aggregator

router = APIRouter()

# ── Google Generative AI Setup (Free Gemini API) ──

_gemini_model = None

def get_gemini_model():
    """Lazy-init Gemini model via free google-generativeai API."""
    global _gemini_model
    if _gemini_model is None:
        try:
            import google.generativeai as genai
            import os

            # Get API key from environment or fallback
            api_key = os.getenv("GOOGLE_GENERATIVEAI_KEY", "AIzaSyDR72GuItb0LpseJtC5RBvL2gZbaH5qZMw")
            if not api_key:
                raise ValueError("GOOGLE_GENERATIVEAI_KEY environment variable not set")

            genai.configure(api_key=api_key)

            _gemini_model = genai.GenerativeModel(
                "gemini-3-flash-preview",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_output_tokens": 2048,
                }
            )
            print("[Chat] Gemini model initialized successfully (gemini-3-flash-preview)")
        except Exception as e:
            print(f"[Chat] Failed to initialize Gemini: {e}")
            traceback.print_exc()
            raise
    return _gemini_model


# ── Request/Response Models ──

class ChatRequest(BaseModel):
    message: str
    date: str | None = None  # optional date context, defaults to today


class ChartData(BaseModel):
    label: str
    value: float
    color: str


class ChartBlock(BaseModel):
    title: str
    type: str  # "bar" | "pie" | "metric"
    data: list[ChartData]


class MetricItem(BaseModel):
    label: str
    value: str
    change: str | None = None
    icon: str


class ChatResponse(BaseModel):
    text: str
    charts: list[ChartBlock] | None = None
    metrics: list[MetricItem] | None = None
    error: str | None = None


# ── Data Context Builder ──

def build_user_context(db: Session, user_id: str, org_id: str, role: str, team_id: str | None, date_str: str) -> dict:
    """Fetch all relevant user data for the given date and build a context dict.

    Role-aware filtering:
    - employee: only their own data
    - team_lead: their own data + team's aggregated data
    - admin: organization's data + their own
    - super_admin: all organization data
    """

    # Determine which user(s) to include based on role
    filter_team_id = None
    if role == "employee":
        # Employees see only their own data
        filter_org_id = org_id
        filter_user_id = user_id
        data_scope = "personal"
    elif role == "team_lead":
        # Team leads see their team + themselves
        filter_org_id = org_id
        filter_user_id = None  # Will fetch team data
        filter_team_id = team_id
        data_scope = "team"
    elif role in ("admin", "super_admin"):
        # Admins see org-wide data (or all if super_admin)
        filter_org_id = org_id
        filter_user_id = None  # Will fetch org data
        data_scope = "organization"
    else:
        # Default to personal
        filter_org_id = org_id
        filter_user_id = user_id
        data_scope = "personal"

    # Get today's stats
    today_stats = Aggregator.compute_stats(db, date_str, org_id=filter_org_id, user_id=filter_user_id, team_id=filter_team_id)
    today_logs_data = Aggregator.get_logs_for_date(db, date_str, org_id=filter_org_id, user_id=filter_user_id, team_id=filter_team_id)
    today_logs = today_logs_data.get("logs", []) if isinstance(today_logs_data, dict) else today_logs_data

    # Get yesterday's stats for comparison
    yesterday = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_stats = Aggregator.compute_stats(db, yesterday, org_id=filter_org_id, user_id=filter_user_id, team_id=filter_team_id)

    # Get this week's data (last 7 days)
    weekly_data = []
    for i in range(7):
        d = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
        day_stats = Aggregator.compute_stats(db, d, org_id=filter_org_id, user_id=filter_user_id, team_id=filter_team_id)
        weekly_data.append({"date": d, **day_stats})

    # Extract window/app timeline from today's logs (only for personal view)
    window_events = []
    if role == "employee":
        window_events = [
            {
                "time": log["timestamp"],
                "app": log["data"].get("window_title", "Unknown"),
                "duration": log["data"].get("duration_seconds", 0),
            }
            for log in today_logs
            if log["event_type"] == "window_change"
        ]

    # Hourly keystroke/click breakdown from today (only for personal view)
    hourly_input = {}
    if role == "employee":
        for log in today_logs:
            if log["event_type"] == "input_summary":
                hour = log["timestamp"][:13]  # "2026-04-12T14"
                if hour not in hourly_input:
                    hourly_input[hour] = {"keystrokes": 0, "clicks": 0}
                hourly_input[hour]["keystrokes"] += log["data"].get("keystrokes", 0)
                hourly_input[hour]["clicks"] += log["data"].get("mouse_clicks", 0)

    # Telemetry summary (only for personal view)
    telemetry_latest = None
    if role == "employee":
        for log in reversed(today_logs):
            if log["event_type"] == "telemetry":
                telemetry_latest = log["data"]
                break

    return {
        "date": date_str,
        "data_scope": data_scope,  # "personal", "team", or "organization"
        "today": today_stats,
        "yesterday": yesterday_stats,
        "weekly": weekly_data,
        "window_timeline": window_events[-20:],  # last 20 window events
        "hourly_input": hourly_input,
        "telemetry": telemetry_latest,
        "total_events_today": len(today_logs),
    }


def build_prompt(user_name: str, question: str, context: dict, role: str) -> str:
    """Build the full prompt for Gemini with user data context."""

    today = context["today"]
    yesterday = context["yesterday"]
    data_scope = context["data_scope"]

    # Scope indicator for context
    scope_label = {
        "personal": "Your personal productivity data",
        "team": "Your team's aggregated productivity data",
        "organization": "Your organization's aggregated productivity data"
    }.get(data_scope, "Productivity data")

    # Calculate changes
    ks_change = ""
    if yesterday["activity_summary"]["keystrokes"] > 0:
        pct = ((today["activity_summary"]["keystrokes"] - yesterday["activity_summary"]["keystrokes"])
               / yesterday["activity_summary"]["keystrokes"] * 100)
        ks_change = f" ({pct:+.0f}% vs yesterday)"

    cl_change = ""
    if yesterday["activity_summary"]["clicks"] > 0:
        pct = ((today["activity_summary"]["clicks"] - yesterday["activity_summary"]["clicks"])
               / yesterday["activity_summary"]["clicks"] * 100)
        cl_change = f" ({pct:+.0f}% vs yesterday)"

    # Format top apps
    top_apps_str = "\n".join([
        f"  - {app['name']}: {app['duration'] // 60}m {app['duration'] % 60}s"
        for app in today.get("top_apps", [])
    ]) or "  No app data available"

    # Hourly summary - find peak hour only
    hourly_data = context.get("hourly_input", {})
    if hourly_data:
        peak_hour = max(hourly_data.items(), key=lambda x: x[1]['keystrokes'])[0]
        hourly_str = f"  Peak hour: {peak_hour}"
    else:
        hourly_str = "  No hourly data available"

    # Weekly trend - just show direction (up/down/stable)
    weekly = context.get("weekly", [])
    if len(weekly) >= 2:
        today_score = weekly[0]['productivity_score']
        week_avg = sum(d['productivity_score'] for d in weekly) / len(weekly)
        trend = "↑ Up" if today_score > week_avg else "↓ Down" if today_score < week_avg else "→ Stable"
        weekly_str = f"  Weekly trend: {trend} (today {today_score} vs week avg {week_avg:.0f})"
    else:
        weekly_str = "  No weekly data available"

    # Top 3 apps only - summarized
    top_3_apps = today.get("top_apps", [])[:3]
    if top_3_apps:
        recent_windows = "\n".join([
            f"  {i+1}. {app['name']}: {app['duration'] // 60}m"
            for i, app in enumerate(top_3_apps)
        ])
    else:
        recent_windows = "  No app data available"

    # Telemetry
    telem_str = "No telemetry data"
    if context.get("telemetry"):
        t = context["telemetry"]
        telem_str = f"CPU: {t.get('cpu_percent', 'N/A')}%, RAM: {t.get('ram_percent', 'N/A')}%, Battery: {t.get('battery_percent', 'N/A')}%"

    prompt = f"""You are ProMe AI Assistant — a productivity analytics AI. You analyze real tracked data and provide specific, differentiated insights based on the user's exact question.

USER: {user_name} ({role})
DATA SCOPE: {scope_label}
DATE: {context['date']}
TOTAL EVENTS LOGGED TODAY: {context['total_events_today']}

═══ TODAY'S SUMMARY ═══
Productivity Score: {today['productivity_score']}/100
Total Keystrokes: {today['activity_summary']['keystrokes']:,}{ks_change}
Total Clicks: {today['activity_summary']['clicks']:,}{cl_change}
Total Active Time: {today['total_time_seconds'] // 3600}h {(today['total_time_seconds'] % 3600) // 60}m

═══ TOP APPLICATIONS ═══
{recent_windows}

═══ ACTIVITY PATTERNS ═══
{hourly_str}
{weekly_str}

═══ SYSTEM HEALTH ═══
{telem_str}

═══════════════════════

USER'S QUESTION: {question}

CRITICAL INSTRUCTIONS:
1. **Focus on the specific question** — tailor your response to EXACTLY what they asked, not generic summaries.
2. **Use real numbers only** — cite specific metrics from the data above. Never invent data.
3. **Be specific and unique** — each question should produce a meaningfully different response. Do NOT provide generic answers.
4. **For "productivity" questions** → discuss score, trends, focus patterns, and suggestions
5. **For "keystroke/typing" questions** → focus on typing activity, patterns by time, peak hours
6. **For "app/application" questions** → analyze which apps consumed time, switching patterns, focus
7. **For "click/mouse" questions** → discuss click volume, distribution by app, intensity
8. **For "summary/overview" questions** → provide a concise day-at-a-glance with key highlights
9. If data is missing → acknowledge honestly ("No keystrokes logged" / "Limited activity data")
10. Keep response concise (2-4 paragraphs max) but answer the EXACT question asked.

IMPORTANT — STRUCTURED RESPONSE FORMAT:
You MUST respond with a valid JSON object in this exact format:
{{
  "text": "Your main response text here. Use **bold** for emphasis. Use \\n for line breaks.",
  "metrics": [
    {{"label": "Metric Name", "value": "123", "change": "+5%", "icon": "keyboard|clock|sparkles|monitor|mousepointer"}}
  ],
  "charts": [
    {{
      "title": "Chart Title",
      "type": "bar",
      "data": [
        {{"label": "Label", "value": 100, "color": "#4f46e5"}}
      ]
    }}
  ]
}}

RULES FOR JSON RESPONSE:
- "text" is REQUIRED. Use real numbers from the data above.
- "metrics" is OPTIONAL — include 3-4 key metrics when relevant. Icons must be one of: keyboard, clock, sparkles, monitor, mousepointer
- "charts" is OPTIONAL — include when the user asks about breakdowns, comparisons, or trends.
  - type can be "bar" or "pie"
  - Use colors: "#4f46e5" (indigo), "#10b981" (green), "#f59e0b" (amber), "#06b6d4" (cyan), "#a855f7" (purple), "#ec4899" (pink), "#ef4444" (red), "#64748b" (slate)
  - For pie charts, values should be percentages that sum to ~100
  - For bar charts, use actual values
- Respond ONLY with the JSON object. No markdown code fences. No extra text before or after.
"""
    return prompt


def parse_gemini_response(raw_text: str) -> ChatResponse:
    """Parse Gemini's response into structured ChatResponse."""
    try:
        # Clean up the response — strip markdown code fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        print(f"[Chat] Cleaned response length: {len(cleaned)} chars")
        print(f"[Chat] Cleaned response starts with: {cleaned[:100]}")

        parsed = json.loads(cleaned)

        print(f"[Chat] Successfully parsed JSON with keys: {list(parsed.keys())}")

        return ChatResponse(
            text=parsed.get("text", "I analyzed your data but couldn't format the response properly."),
            metrics=[MetricItem(**m) for m in parsed.get("metrics", [])] if parsed.get("metrics") else None,
            charts=[ChartBlock(
                title=c["title"],
                type=c["type"],
                data=[ChartData(**d) for d in c["data"]]
            ) for c in parsed.get("charts", [])] if parsed.get("charts") else None,
        )
    except json.JSONDecodeError as e:
        print(f"[Chat] JSON decode error: {e}")
        print(f"[Chat] Error at line {e.lineno}, col {e.colno}: {e.msg}")
        print(f"[Chat] Raw response (first 1000 chars): {raw_text[:1000]}")

        # Try to extract text field manually if JSON parsing failed
        try:
            # Look for "text": "..." pattern with improved regex
            match = re.search(r'"text"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', raw_text, re.DOTALL)
            if match:
                extracted_text = match.group(1).replace('\\"', '"').replace('\\n', '\n')
                print(f"[Chat] Extracted text from malformed JSON: {extracted_text[:100]}")
                return ChatResponse(text=extracted_text)

            # If no text field found, try to find any meaningful content
            # Look for the first JSON structure
            json_match = re.search(r'\{.*?"text"\s*:\s*"([^"]*)"', raw_text)
            if json_match:
                extracted_text = json_match.group(1)
                print(f"[Chat] Extracted text from partial JSON: {extracted_text[:100]}")
                return ChatResponse(text=extracted_text)
        except Exception as extract_err:
            print(f"[Chat] Failed to extract text manually: {extract_err}")

        # Fallback to a clear error message (never raw JSON)
        return ChatResponse(
            text="I encountered an issue formatting my response properly. This might be a temporary issue with the AI service. Please try asking your question again.",
            error=f"JSON parse error: {e.msg}"
        )
    except (KeyError, TypeError) as e:
        print(f"[Chat] Response structure error: {e}")
        print(f"[Chat] Raw response: {raw_text[:500]}")
        # Fall back to extracting text if available
        try:
            parsed = json.loads(cleaned) if 'cleaned' in locals() else {}
            text = parsed.get("text", None)
            if text:
                return ChatResponse(text=text)
        except:
            pass

        return ChatResponse(
            text="I encountered an error while processing the response. Please try asking again.",
            error=str(e)
        )
    except Exception as e:
        print(f"[Chat] Unexpected error parsing response: {e}")
        print(f"[Chat] Error type: {type(e).__name__}")
        print(f"[Chat] Raw response: {raw_text[:500]}")
        return ChatResponse(
            text="I encountered an unexpected error while processing your request. Please try again.",
            error=str(e)
        )


# ── Auth Helper ──

def _get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)


# ── API Endpoint ──

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, db: Session = Depends(get_db)):
    """Send a message to ProMe AI and get an intelligent response based on real user data."""

    # Auth check
    token_data = _get_token_data(request)
    if not token_data:
        return ChatResponse(text="Please log in to use the AI assistant.", error="unauthorized")

    user_id = token_data["id"]
    org_id = token_data.get("org_id")

    # Get user info
    user_info = get_user_by_id(db, user_id)
    user_name = user_info["name"] if user_info else "User"
    user_role = user_info.get("role", "employee") if user_info else "employee"
    user_team_id = user_info.get("team_id") if user_info else None

    # Date context
    date_str = req.date or datetime.now().strftime("%Y-%m-%d")

    try:
        # Build context from real data (role-aware)
        context = build_user_context(db, user_id, org_id, user_role, user_team_id, date_str)

        # Debug logging
        print(f"[Chat] User {user_id} ({user_role}) asked: {req.message}")
        print(f"[Chat] Context data scope: {context.get('data_scope')}")
        print(f"[Chat] Today's keystrokes: {context.get('today', {}).get('activity_summary', {}).get('keystrokes', 0)}")
        print(f"[Chat] Today's clicks: {context.get('today', {}).get('activity_summary', {}).get('clicks', 0)}")
        print(f"[Chat] Total events today: {context.get('total_events_today', 0)}")

        # Build prompt
        prompt = build_prompt(user_name, req.message, context, user_role)

        # Call Gemini with timeout
        model = get_gemini_model()
        response = model.generate_content(
            prompt,
            request_options={"timeout": 30}
        )

        # Parse response
        result = parse_gemini_response(response.text)
        print(f"[Chat] Gemini response length: {len(result.text)} chars")
        print(f"[Chat] Gemini response preview: {result.text[:100]}...")
        return result

    except Exception as e:
        print(f"[Chat] Error: {e}")
        traceback.print_exc()

        # Fallback: try to give basic stats even if Gemini fails
        try:
            stats = Aggregator.compute_stats(db, date_str, org_id=org_id)
            fallback_text = (
                f"I'm having trouble connecting to the AI service right now, but here are your stats for {date_str}:\n\n"
                f"- **Productivity Score:** {stats['productivity_score']}/100\n"
                f"- **Keystrokes:** {stats['activity_summary']['keystrokes']:,}\n"
                f"- **Clicks:** {stats['activity_summary']['clicks']:,}\n"
                f"- **Active Time:** {stats['total_time_seconds'] // 3600}h {(stats['total_time_seconds'] % 3600) // 60}m\n\n"
                f"Error details: {str(e)}"
            )
            return ChatResponse(
                text=fallback_text,
                metrics=[
                    MetricItem(label="Productivity", value=f"{stats['productivity_score']}%", icon="sparkles"),
                    MetricItem(label="Keystrokes", value=f"{stats['activity_summary']['keystrokes']:,}", icon="keyboard"),
                    MetricItem(label="Clicks", value=f"{stats['activity_summary']['clicks']:,}", icon="mousepointer"),
                ],
                error=str(e),
            )
        except Exception:
            return ChatResponse(
                text=f"Sorry, I encountered an error: {str(e)}. Please set GOOGLE_GENERATIVEAI_KEY environment variable.\n\nGet a free API key from: https://aistudio.google.com/app/apikey",
                error=str(e),
            )
