import re, sys
from atproto_client.models import get_or_create
from atproto import CAR, models
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from enum import Enum

# There are two modes that ClueSky works in. One is just a target length:
# can you find a phrase that's x characters.
# The other is substring: can you find a phrase (of ANY length) that contains the substring
class MODE(Enum):
  LENGTH = 1
  SUBSTRING = 2

# Define the target
target_mode = MODE.LENGTH
target_length = 13

target_mode = MODE.SUBSTRING
target_substring = 'se cond'
# 15 as max size, +4 because rebus, -1 to fit in rebus
max_length = 15 + 6 - 1

PRINT_LIMIT = 1

strings = {}
# Filter out things that are likely to be partials
# Or just known bad Bsky formats
banned_ends = {'the', 'of', 'and', 'on', 'in', 'or', 'to', 'a', 'are', 'who'}

def find_words(before, after, current, all_words, max_length):
  # Check left
  if len(before) > 0 and len(before[-1]) + sum([len(x) for x in current]) <= max_length:
    new_current = [before[-1], *current]
    all_words.append(new_current)
    all_words = find_words(before[:-1], after, new_current, all_words, max_length)
    
  # Check right
  if len(after) > 0 and len(after[0]) + sum([len(x) for x in current]) <= max_length:
    new_current = [*current, after[0]]
    all_words.append(new_current)
    all_words = find_words(before, after[1:], new_current, all_words, max_length)
  
  return all_words

def extract_chunks(target_substring, cleaned, max_length):
  if target_substring not in cleaned:
    return {}
    
  total_matches = {}
  matches = re.finditer(fr'(?:\S+\s+){{0,2}}\S*{re.escape(target_substring)}\S*(?:\s+\S+){{0,2}}', cleaned)
  for match in matches:
    # Get both sides of the string that we care about
    front, back = match.group().split(target_substring)
    front = front.split(' ')
    back = back.split(' ')
    combo_parts = target_substring.split(' ')
    # Reconstruct the core words that are part of the string that we care about
    assert len(combo_parts) > 1, 'TODO: fix this'
    core = []
    # Front piece
    if combo_parts[0] == '':
      before = front
    else:
      core.append(front[-1] + combo_parts[0])
      before = front[:-1]
    # The middle chunks
    for i in range(1, len(combo_parts) - 1):
      core.append(combo_parts[i])
    # Back piece
    if combo_parts[-1] == '':
      after = back
    else:
      core.append(combo_parts[-1] + back[0])
      after = back[1:]
    # Create set of matches
    words = find_words(before, after, core, [core], max_length)
    for word in words:
      combined = ''.join(word).lower()
      total_matches[combined] = ' '.join(word)
  return total_matches

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
          # Simple tokenization (remove hashtags, remove non-alpha numeric
          cleaned = re.sub(r'[^A-Za-z\s]', '', re.sub(r'#[A-Za-z]+', '', re.sub(r'\n+', ' ', raw['text'])))
          if target_mode == MODE.SUBSTRING:
            words = extract_chunks(target_substring, cleaned, max_length)
            for combined in words:
              if combined in strings:
                strings[combined]['num'] += 1
              else:
                strings[combined] = {
                  'num': 1,
                  'separated': words[combined],
                }
              if (strings[combined]['num'] == PRINT_LIMIT):
                print(strings[combined]['separated'])
            
          elif target_mode == MODE.LENGTH:
            # We want only full phrases so splitting on periods makes sure that
            # we don't span areas. Could be missing things,
            # ^^ actually, maybe we just wait?
            
            # Split into words
            words = cleaned.split()
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
                else:
                  strings[combined] = {
                    'num': 1,
                    'separated': found_section,
                  }
                if (strings[combined]['num'] == PRINT_LIMIT):
                  print(strings[combined]['separated'])

if __name__ == '__main__':
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