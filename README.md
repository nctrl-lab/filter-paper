# FilterPaper

FilterPaper is a Python tool that helps researchers stay up-to-date with academic literature by filtering RSS feeds from scientific journals based on similarity to their existing library of papers. This sends a message to Slack with the new papers.

## Features

- Filters papers from RSS feeds using semantic similarity
- Compares new papers against your existing BibTeX library
- Caches processed entries to avoid duplicates
- Sends notifications to Slack
- Supports multiple journal RSS feeds
- Configurable similarity threshold

## Installation

1. Installation
```bash
git clone https://github.com/nctrl-lab/filter-paper.git
cd filter-paper
pip install .
```

2. Run
```bash
filterpaper
```

- If you don't have a Slack webhook URL, you will be prompted to enter one.
- The webhook URL will be cached in your system keyring, so you don't need to enter it again.

3. Add more journals
You can add more journals to the `PAPERS` dictionary in `filter_paper/constants.py`.