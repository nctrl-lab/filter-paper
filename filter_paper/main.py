import os
import json
import numpy as np
import re
import click
import keyring
import requests
import feedparser
from pybtex.database.input import bibtex
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .constants import PAPERS

class FilterPaper:
    def __init__(self, bibtex_file='assets/My Library.bib'):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # Parse bibtex file once at initialization
        parser = bibtex.Parser()
        bib_data = parser.parse_file(bibtex_file)

        # Extract and clean titles in one pass
        queries = []
        for entry in bib_data.entries.values():
            title = entry.fields['title']
            title = title.replace('{','').replace('}','')

            abstract = entry.fields.get('abstract', '')
            queries.append(title + ' ' + abstract if abstract else title)

        self.query = self.model.encode(queries)
        
    def __call__(self, rss, threshold=0.35):
        # Parse feed and extract titles efficiently
        feed = feedparser.parse(rss)
        
        # Load cached entries if they exist
        # Create a safe filename by replacing invalid characters with underscores
        safe_name = re.sub(r'[:/\?=&]', '_', rss)

        # Ensure cache directory exists
        cache_dir = os.path.expanduser('~/.cache/filter-paper')
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{safe_name}.json")
        cached_entries = set()
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cached_entries = set(json.load(f))
                
        # Filter out entries we've seen before
        new_entries = [entry for entry in feed.entries 
                      if entry.title not in cached_entries]
        
        if not new_entries:
            print("No new entries found")
            return []
        
        # Update cache with new entries
        with open(cache_file, 'w') as f:
            json.dump(list({entry.title for entry in feed.entries}), f)

        # Process only new entries
        feed_entries = [entry.title + ' ' + entry.get('summary', '') 
                       for entry in new_entries]

        # Compute scores
        embeddings = self.model.encode(feed_entries)

        # Cosine similarity between query and feed
        scores = np.quantile(cosine_similarity(embeddings, self.query), 0.95, axis=1)

        if threshold is not None:
            in_threshold = scores >= threshold
            
            if in_threshold.any():
                new_entries = np.array(new_entries)[in_threshold]
                scores = scores[in_threshold]
            else:
                print(f"No papers found with similarity >= {100*threshold:.0f}%")
                return []

        entries = []
        for entry, score in zip(new_entries, scores):
            parts = []

            if entry.get('authors'):
                parts.append(', '.join(author.name for author in entry.authors))
                
            parts.append(entry.title)

            if entry.get('dc_source'):
                parts.append(entry.get('dc_source'))

            parts.append(entry.get('updated') or entry.get('date'))
            parts.append(f"Match score: {100*score:.0f}%")
            parts.append(entry.link)

            entries.append('\n'.join(parts))

        print(f"Found {len(feed_entries)} papers")
        if threshold is not None:
            print(f"Showing papers with similarity >= {100*threshold:.0f}%\n")

        return entries


def send_slack_message(message):
    # Cache webhook URL in function scope to avoid repeated keyring lookups
    if not hasattr(send_slack_message, '_webhook_url'):
        url = keyring.get_password('slack', 'journal_club')
        if url is None:
            url = input("Enter the Slack webhook URL: ")
            keyring.set_password('slack', 'journal_club', url)
        send_slack_message._webhook_url = url
    
    response = requests.post(send_slack_message._webhook_url, json={"text": message})
    if response.status_code != 200:
        raise ValueError(f"Request to slack returned an error {response.status_code}, the response is:\n{response.text}")


@click.command()
@click.option('--slack', is_flag=True, default=False, help='Send message to slack')
def filterpaper(slack=True):
    filter_paper = FilterPaper()
    for journal, (rss, threshold) in PAPERS.items():
        print(f"Filtering {journal}...")
        entries = filter_paper(rss, threshold)
        
        if entries:
            message = f"{journal}\n"
            message += '\n\n'.join(entries)

            print(message)
            print()
            if slack:
                send_slack_message(message)


if __name__ == "__main__":
    filterpaper()