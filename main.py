import re, sys
from atproto_client.models import get_or_create
from atproto import CAR, models
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message

# Define the target
target_length = 13
strings = {}
# Filter out things that are likely to be partials
# Or just known bad Bsky formats
banned_ends = {'the', 'of', 'and', 'on', 'in', 'or', 'to', 'a', 'are', 'who'}

def on_message_handler(message):
    commit = parse_subscribe_repos_message(message)
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
      return
    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
      if op.action in ["create"] and op.cid:
        raw = car.blocks.get(op.cid)
        cooked = get_or_create(raw, strict=False)
        # Exclude IEMbot which is weather spam
        if (
          cooked is not None
          and cooked.py_type == "app.bsky.feed.post"
          and 'IEMbot' not in raw['text']
          and '🕒 Current times' not in raw['text']
        ):
          # We want only full phrases so splitting on periods makes sure that
          # we don't span areas. Could be missing things,
          # ^^ actually, maybe we just wait?
          
          # Simple tokenization (remove hashtags, remove non-alpha numeric, split into words)
          words = re.sub(r'[^A-Za-z\s]', '', re.sub(r'#[A-Za-z]+', '', raw['text'])).split()
          # Get sequential words that are the right number of characters
          n = len(words)
          start = 0
          current_length = 0

          for end in range(n):
            current_length += len(words[end])
            
            while current_length > target_length and start <= end:
              current_length -= len(words[start])
              start += 1
            # It's the right length AND it's more than one word
            # (any standard dictionary should already have one word answers
            # I guess, unless it's slang...hmm. Can revisit)
            if current_length == target_length and end != start:
              found_section = words[start:end+1]
              if (found_section[0].lower() in banned_ends or found_section[-1].lower() in banned_ends):
                continue
              combined = ''.join(found_section).lower()
              if combined in strings:
                strings[combined]['num'] += 1
                if (strings[combined]['num'] == 3):
                  print(' '.join(found_section))
              else:
                strings[combined] = {
                  'num': 1,
                  'separated': found_section,
                }

try:
  client = FirehoseSubscribeReposClient()
  print('Initialized.')
  client.start(on_message_handler)
except KeyboardInterrupt:
  print("\nCtrl+C detected. Performing cleanup before exit.")
  strings = {x: strings[x] for x in strings if strings[x]['num'] > 1}
  print(strings)
  # Perform any cleanup here
  sys.exit(0)