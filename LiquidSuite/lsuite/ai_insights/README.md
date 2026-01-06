# AI Insights - Groq AI Integration

AI-powered financial analysis using Groq AI with rotating API keys.

## Features

- **Period Analysis**: Comprehensive analysis of transactions over selected periods
- **Transaction Intelligence**: AI insights on individual transactions
- **Supplier Analysis**: Deep dive into supplier spending patterns
- **Category Intelligence**: Smart analysis of spending by category
- **API Key Rotation**: Automatic rotation of Groq API keys for reliability

## Setup

### 1. Install Groq SDK

```bash
pip install groq
```

### 2. Configure API Keys

Add multiple Groq API keys to your `.env` file (comma-separated):

```bash
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
```

Get API keys from: https://console.groq.com/keys

### 3. Register Blueprint

In `lsuite/__init__.py`, add:

```python
from lsuite.ai_insights import ai_insights_bp

app.register_blueprint(ai_insights_bp, url_prefix='/ai-insights')
```

### 4. Create Directory Structure

```bash
mkdir -p lsuite/ai_insights
touch lsuite/ai_insights/__init__.py
touch lsuite/ai_insights/routes.py
touch lsuite/ai_insights/services.py
mkdir -p lsuite/templates/ai_insights
```

## Usage

### Period Analysis

```python
# Analyze last 90 days
POST /ai-insights/analyze-period
Form data: days=90

Response:
{
  "success": true,
  "analysis": {
    "overview": "...",
    "key_insights": [...],
    "spending_patterns": {...},
    "recommendations": [...],
    "risk_score": "LOW|MEDIUM|HIGH",
    "savings_potential": "R5000"
  }
}
```

### Single Transaction Analysis

```python
# Analyze specific transaction
POST /ai-insights/transaction/123/analyze

Response:
{
  "success": true,
  "analysis": {
    "summary": "...",
    "insights": [...],
    "flags": [...],
    "suggestions": [...]
  }
}
```

### Supplier Analysis

```python
# Analyze supplier spending
POST /ai-insights/supplier/UBER/analyze
Form data: days=180

Response:
{
  "success": true,
  "analysis": {
    "relationship_assessment": "...",
    "spending_trend": "increasing",
    "insights": [...],
    "concerns": [...],
    "recommendations": [...]
  }
}
```

## API Key Rotation

The service automatically rotates through available API keys:

- Keys are loaded from environment variable
- Failed keys are temporarily blacklisted
- Automatic retry with next available key
- Keys rotate after each successful request

## Navigation

Add to your navigation menu:

```html
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('ai_insights.dashboard') }}">
        <i class="fas fa-brain"></i> AI Insights
    </a>
</li>
```

## Requirements

- Python 3.9+
- Groq API keys (free tier available)
- Flask with existing LiquidSuite setup

## Notes

- Groq uses Llama 3.3 70B model
- Free tier: 30 requests/minute
- Multiple keys allow higher throughput
- Analysis cached per session for performance
