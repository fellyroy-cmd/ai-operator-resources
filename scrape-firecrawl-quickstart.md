# Turn any website into AI-ready text (Firecrawl quick-start)

*From my "Stop copy-pasting websites into ChatGPT" short. — Dara*

[Firecrawl](https://github.com/firecrawl/firecrawl) is free and open source. Give it a URL and it returns clean markdown with the menus, ads and junk stripped out, ready to paste into any AI.

## Step 1: get a free API key

Sign up at [firecrawl.dev](https://firecrawl.dev) (Google or GitHub login). The free plan comes with credits, and one page costs one credit.

## Step 2: run one command

Mac / Linux / Git Bash:

```bash
curl -s -X POST https://api.firecrawl.dev/v2/scrape \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["markdown"], "onlyMainContent": true}'
```

Windows PowerShell:

```powershell
$body = '{"url": "https://example.com", "formats": ["markdown"], "onlyMainContent": true}'
(Invoke-RestMethod -Method Post -Uri https://api.firecrawl.dev/v2/scrape `
  -Headers @{ Authorization = "Bearer YOUR_API_KEY" } `
  -ContentType "application/json" -Body $body).data.markdown
```

Prefer Python?

```bash
pip install firecrawl-py
```

```python
from firecrawl import Firecrawl
fc = Firecrawl(api_key="YOUR_API_KEY")
doc = fc.scrape("https://example.com", formats=["markdown"])
print(doc.markdown)
```

## Step 3: point it at any page

Docs pages, competitor landing pages, articles, pricing pages, changelogs. Swap the URL and run it again.

## Step 4: paste it into your AI with this prompt

```
Below is the full text of a web page, as markdown.
Answer my questions using ONLY this page. If the answer isn't on the page, say so.

First, give me:
1. A 3-line summary of what this page is about.
2. The 5 most important facts or numbers on it.
3. Anything that's unclear or missing.

Then wait for my questions.

---
[PASTE THE MARKDOWN HERE]
```

## Ideas to try

- Scrape a competitor's pricing page and ask "what are they charging, and what's the catch?"
- Scrape a long docs page and ask "what's the fastest way to do X?"
- Scrape 3 articles on the same story and ask "where do these disagree?"

---

**Share what you scraped in The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
