import re, sys
from atproto_client.models import get_or_create
from atproto import CAR, models
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message

# Define the target
target_length = 15
strings = {}

def on_message_handler(message):
    commit = parse_subscribe_repos_message(message)
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
      return
    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
      if op.action in ["create"] and op.cid:
        raw = car.blocks.get(op.cid)
        cooked = get_or_create(raw, strict=False)
        if cooked is not None and cooked.py_type == "app.bsky.feed.post":
          # We want only full phrases so splitting on periods makes sure that
          # we don't span areas. Could be missing things,
          # ^^ actually, maybe we just wait?
          
          # Simple tokenization
          words = re.sub(r'[^A-Za-z\s]', '', raw['text']).split()
          # Get sequential words that are the right number of characters
          n = len(words)
          start = 0
          current_length = 0

          for end in range(n):
            current_length += len(words[end])
            
            while current_length > target_length and start <= end:
              current_length -= len(words[start])
              start += 1
              
            if current_length == target_length:
              found_section = words[start:end+1]
              combined = ''.join(found_section).lower()
              if combined in strings:
                strings[combined]['num'] += 1
                print(found_section)
              else:
                strings[combined] = {
                  'num': 1,
                  'separated': found_section,
                }

client = FirehoseSubscribeReposClient()
client.start(on_message_handler)